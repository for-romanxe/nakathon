import json
from contextlib import asynccontextmanager, closing
from threading import Lock
from typing import Literal

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from backend.checkin import Checkin, save_checkin
from backend.db import connect, initialize
from backend import event_flow
from backend.events import EventOverride, SymptomAnswer, SymptomInput, event_payload, save_event
from backend.link_simulation import LinkSimulation, compare_packet
from backend.mission import ClockUpdate, DEMO_TIME, active_window, mission_sol, mission_status
from backend.seed import DEMO_DB, seed
from backend.today import today
from backend.transmission import (
    DeliveryResult, QueueRequest, dispatch, enqueue_daily, enqueue_event, packets, record_delivery,
)


def crew_not_found() -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"error": {"code": "crew_not_found", "message": "Crew member not found."}},
    )


def event_error(code="event_not_found", message="Event not found.", status=404) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def create_app(db_path=DEMO_DB) -> FastAPI:
    clock = DEMO_TIME
    clock_lock = Lock()
    event_locks = [Lock() for _ in range(32)]
    evidence = []

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        nonlocal evidence
        evidence = event_flow.load_evidence()
        initialize(db_path)
        with closing(connect(db_path)) as connection:
            seed(connection)
        yield

    app = FastAPI(title="Crew Health Demo API", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, error: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "invalid_request", "message": str(error.errors()[0]["msg"])}},
        )

    @app.get("/crew")
    def list_crew():
        with closing(connect(db_path)) as connection:
            rows = connection.execute("SELECT id, name, role, cmo FROM crew ORDER BY id")
            return [dict(row, cmo=bool(row["cmo"])) for row in rows]

    @app.get("/mission")
    def read_mission():
        return mission_status(clock)

    @app.post("/demo/clock")
    def update_clock(update: ClockUpdate):
        nonlocal clock
        with clock_lock:
            clock = update.apply(clock)
            return mission_status(clock)

    @app.get("/crew/{crew_id}/today")
    def read_today(crew_id: str, lang: Literal["en", "ko"] = "en"):
        crew_id = crew_id.lower()
        with closing(connect(db_path)) as connection:
            crew = connection.execute("SELECT id FROM crew WHERE id = ?", (crew_id,)).fetchone()
            if crew is None:
                return crew_not_found()
            return today(connection, crew_id, mission_sol(clock), lang)

    @app.post("/crew/{crew_id}/checkin")
    def submit_checkin(crew_id: str, checkin: Checkin, lang: Literal["en", "ko"] = "en"):
        crew_id = crew_id.lower()
        with closing(connect(db_path)) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            crew = connection.execute("SELECT id FROM crew WHERE id = ?", (crew_id,)).fetchone()
            if crew is None:
                return crew_not_found()
            timestamp = clock
            sol = mission_sol(timestamp)
            current = today(connection, crew_id, sol, lang)
            save_checkin(connection, crew_id, sol, checkin, current["status"]["level"], timestamp)
            return today(connection, crew_id, sol, lang)

    @app.post("/crew/{crew_id}/symptom")
    def report_symptom(crew_id: str, report: SymptomInput):
        crew_id = crew_id.lower()
        with closing(connect(db_path)) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            crew = connection.execute("SELECT id FROM crew WHERE id = ?", (crew_id,)).fetchone()
            if crew is None:
                return crew_not_found()
            timestamp = clock
            sol = mission_sol(timestamp)
            current = today(connection, crew_id, sol, report.lang)
            event_id = save_event(connection, crew_id, sol, report, current, timestamp)
            event = connection.execute("SELECT * FROM event WHERE id = ?", (event_id,)).fetchone()
            if event["level"] == "warning":
                enqueue_event(connection, event)
                return {"event_id": event_id, "needs_question": False, "urgent": bool(event["urgent"])}
        # Do not hold a SQLite write lock during inference.
        codes, state = event_flow.extract(event_payload(event), report.lang)
        with closing(connect(db_path)) as connection, connection:
            connection.execute("UPDATE event SET codes = ?, pipeline = ? WHERE id = ?",
                               (json.dumps(codes), json.dumps(state), event_id))
        response = {"event_id": event_id, "needs_question": "question" in state, "urgent": False}
        if response["needs_question"]:
            response["question"] = state["question"]
        return response

    def get_event(event_id):
        with closing(connect(db_path)) as connection:
            return connection.execute("SELECT * FROM event WHERE id = ?", (event_id,)).fetchone()

    @app.post("/events/{event_id}/answer", status_code=202)
    def answer_symptom(event_id: int, answer: SymptomAnswer):
        with closing(connect(db_path)) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            event = connection.execute("SELECT * FROM event WHERE id = ?", (event_id,)).fetchone()
            if event is None:
                return event_error()
            state = json.loads(event["pipeline"] or "{}")
            if "question" not in state or (state.get("answer") and state["answer"] != answer.answer):
                return event_error("answer_not_expected", "No matching question is awaiting this answer.", 409)
            if "answer" not in state:
                state["answer"] = answer.answer
                connection.execute("UPDATE event SET pipeline = ? WHERE id = ?", (json.dumps(state), event_id))
        return {"event_id": event_id}

    def finish_explanation(event_id: int, paragraphs: list[dict]):
        with event_locks[event_id % len(event_locks)]:
            row = get_event(event_id)
            event = event_payload(row)
            state = json.loads(row["pipeline"])
            if state["stages"][-1] in ("done", "hold"):
                return state["stages"]
            state["stages"].append("retrieve")
            if not paragraphs:
                state["hold_reason"] = "no_matching_evidence"
                state["stages"].append("hold")
            else:
                event_flow.explain(event, state, paragraphs, row["lang"])
            with closing(connect(db_path)) as connection, connection:
                connection.execute("UPDATE event SET pipeline = ? WHERE id = ?", (json.dumps(state), event_id))
            return state["stages"]

    @app.get("/events/{event_id}/stream")
    def stream_event(event_id: int):
        row = get_event(event_id)
        if row is None:
            return event_error()
        state = json.loads(row["pipeline"] or "{}")
        old_stages = ["collect", "rules", "done" if row["level"] == "warning" else "hold"]
        stages = state.get("stages", old_stages)
        if stages[-1] == "rules" or (stages[-1] == "question" and "answer" not in state):
            return event_error("event_not_ready", "The report is still processing or awaiting an answer.", 409)

        def stream():
            def emit(stage):
                return f"data: {json.dumps({'stage': stage})}\n\n"

            for stage in stages:
                yield emit(stage)
            if stages[-1] not in ("done", "hold"):
                yield emit("retrieve")
                paragraphs = event_flow.relevant_evidence(evidence, json.loads(row["codes"]), state)
                emitted = len(stages) + 1
                if paragraphs:
                    yield emit("generate")
                    emitted += 1
                for stage in finish_explanation(event_id, paragraphs)[emitted:]:
                    yield emit(stage)

        return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})

    @app.get("/tx")
    def read_queue():
        with closing(connect(db_path)) as connection:
            return packets(connection)

    def queue_summary(connection, request: QueueRequest, timestamp):
        if request.event_id is not None:
            event = connection.execute("SELECT * FROM event WHERE id = ?", (request.event_id,)).fetchone()
            if event is None:
                return JSONResponse(
                    status_code=404,
                    content={"error": {"code": "event_not_found", "message": "Event not found."}},
                )
            enqueue_event(connection, event)
        else:
            sol = mission_sol(timestamp)
            for crew in connection.execute("SELECT id FROM crew"):
                crew_id = crew["id"]
                enqueue_daily(connection, crew_id, sol, today(connection, crew_id, sol))
        return None

    @app.post("/tx")
    def queue_transmission(request: QueueRequest):
        with closing(connect(db_path)) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            error = queue_summary(connection, request, clock)
            return error if error is not None else packets(connection)

    @app.post("/tx/send")
    def send_transmissions(request: QueueRequest | None = None):
        with closing(connect(db_path)) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            timestamp = clock
            if request is not None:
                error = queue_summary(connection, request, timestamp)
                if error is not None:
                    return error
            window_id = active_window(timestamp)
            if window_id is not None:
                dispatch(connection, window_id)
            return packets(connection)

    @app.post("/tx/{seq}/receipt")
    def receive_transmission(seq: int, result: DeliveryResult):
        with closing(connect(db_path)) as connection, connection:
            if not record_delivery(connection, seq, result):
                exists = connection.execute("SELECT 1 FROM tx_packet WHERE seq = ?", (seq,)).fetchone()
                return JSONResponse(
                    status_code=409 if exists else 404,
                    content={"error": {
                        "code": "invalid_receipt" if exists else "packet_not_found",
                        "message": "Receipt does not match the packet's current attempt."
                        if exists else "Packet not found.",
                    }},
                )
            return packets(connection)

    @app.post("/tx/{seq}/simulate")
    def simulate_link(seq: int, simulation: LinkSimulation):
        with closing(connect(db_path)) as connection:
            packet = connection.execute("SELECT payload FROM tx_packet WHERE seq = ?", (seq,)).fetchone()
        if packet is None:
            return JSONResponse(
                status_code=404,
                content={"error": {"code": "packet_not_found", "message": "Packet not found."}},
            )
        return {"seq": seq, **compare_packet(packet["payload"], simulation)}

    @app.get("/events/{event_id}")
    def read_event(event_id: int):
        event = get_event(event_id)
        return event_error() if event is None else event_payload(event)

    @app.post("/events/{event_id}/share")
    def share_event(event_id: int):
        with closing(connect(db_path)) as connection, connection:
            event = connection.execute(
                "UPDATE event SET shared = 1 WHERE id = ? RETURNING *", (event_id,),
            ).fetchone()
            return event_error() if event is None else event_payload(event)

    def resolve_event(event_id: int, override: EventOverride | None):
        reason = override.reason if override else "resolved"
        note = override.note if override else None
        with closing(connect(db_path)) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            event = connection.execute("SELECT * FROM event WHERE id = ?", (event_id,)).fetchone()
            if event is None:
                return event_error()
            if event["closed_at"]:
                if event["closed_reason"] == reason and event["override_note"] == note:
                    return event_payload(event)
                return event_error("event_already_closed", "The event already has a recorded resolution.", 409)
            if event["level"] == "warning" and override is None:
                return event_error("override_required", "A warning requires an override reason to close.", 409)
            event = connection.execute(
                """UPDATE event SET closed_reason = ?, closed_at = ?, override_note = ?
                   WHERE id = ? RETURNING *""",
                (reason, clock.isoformat(), note, event_id),
            ).fetchone()
            return event_payload(event)

    @app.post("/events/{event_id}/close")
    def close_event(event_id: int):
        return resolve_event(event_id, None)

    @app.post("/events/{event_id}/override")
    def override_event(event_id: int, override: EventOverride):
        return resolve_event(event_id, override)

    return app


app = create_app()
