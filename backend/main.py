import json
from contextlib import asynccontextmanager, closing
from threading import Lock
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, StrictBool

from backend.checkin import Checkin, save_checkin
from backend.db import connect, initialize
from backend import event_flow
from backend.events import EventOverride, SymptomAnswer, SymptomInput, event_payload, save_event
from backend.link_simulation import LinkSimulation, compare_packet
from backend.mission import ClockUpdate, DEMO_TIME, active_window, mission_sol, mission_status
from backend.seed import DEMO_DB, seed
from backend.today import today
from backend.transmission import (
    DeliveryResult, QueueRequest, dispatch, enqueue_daily, enqueue_event, packets, record_delivery, visible_packet,
)


def crew_not_found() -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"error": {"code": "crew_not_found", "message": "Crew member not found."}},
    )


def event_error(code="event_not_found", message="Event not found.", status=404) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


class CrewVisibility(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cmo_access: StrictBool


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
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Content-Type", "X-Demo-Viewer"],
    )

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, error: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "invalid_request", "message": str(error.errors()[0]["msg"])}},
        )

    def get_crew_member(crew_id):
        with closing(connect(db_path)) as connection:
            return connection.execute("SELECT * FROM crew WHERE id = ?", (crew_id.lower(),)).fetchone()

    def viewer(demo_viewer: str = Header("c1", alias="X-Demo-Viewer")):
        member = get_crew_member(demo_viewer)
        if member is None:
            raise HTTPException(403, "Invalid demo viewer.")
        return member

    def cmo_viewer(member=Depends(viewer)):
        if not member["cmo"]:
            raise HTTPException(403, "Medical officer access required.")
        return member

    def may_access(member, owner, *, write=False):
        return member["id"] == owner["id"] or (
            not write and bool(member["cmo"]) and bool(owner["cmo_access"])
        )

    def require_event_access(event, member, *, write=False):
        if event is not None and not may_access(member, get_crew_member(event["crew_id"]), write=write):
            raise HTTPException(403, "Event access denied.")

    @app.exception_handler(HTTPException)
    async def http_error(request, error: HTTPException):
        code = "forbidden" if error.status_code == 403 else "http_error"
        return event_error(code, error.detail, error.status_code)

    @app.get("/crew")
    def list_crew(member=Depends(cmo_viewer)):
        with closing(connect(db_path)) as connection:
            rows = connection.execute("SELECT id, name, role, cmo, cmo_access FROM crew ORDER BY id").fetchall()
            shared = connection.execute(
                """SELECT event.id, event.crew_id FROM event JOIN crew ON crew.id = event.crew_id
                   WHERE event.shared = 1 AND (crew.cmo_access = 1 OR crew.cmo = 1)
                   ORDER BY event.id DESC"""
            ).fetchall()
            return [
                dict(row, cmo=bool(row["cmo"]), cmo_access=bool(row["cmo_access"]),
                     shared_event_ids=[event["id"] for event in shared if event["crew_id"] == row["id"]])
                for row in rows
            ]

    @app.post("/demo/viewer/{crew_id}")
    def select_viewer(crew_id: str):
        member = get_crew_member(crew_id)
        if member is None:
            return crew_not_found()
        return {"id": member["id"], "name": member["name"], "cmo": bool(member["cmo"])}

    @app.get("/settings")
    def read_settings(member=Depends(viewer)):
        return {"cmo_access": bool(member["cmo_access"])}

    @app.put("/settings")
    def update_settings(settings: CrewVisibility, member=Depends(viewer)):
        with closing(connect(db_path)) as connection, connection:
            connection.execute("UPDATE crew SET cmo_access = ? WHERE id = ?", (settings.cmo_access, member["id"]))
        return settings

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
    def read_today(crew_id: str, lang: Literal["en", "ko"] = "en", member=Depends(viewer)):
        crew_id = crew_id.lower()
        with closing(connect(db_path)) as connection:
            crew = connection.execute("SELECT id, cmo_access FROM crew WHERE id = ?", (crew_id,)).fetchone()
            if crew is None:
                return crew_not_found()
            if not may_access(member, crew):
                raise HTTPException(403, "Crew record access denied.")
            return today(connection, crew_id, mission_sol(clock), lang)

    @app.post("/crew/{crew_id}/checkin")
    def submit_checkin(crew_id: str, checkin: Checkin, lang: Literal["en", "ko"] = "en", member=Depends(viewer)):
        crew_id = crew_id.lower()
        if member["id"] != crew_id:
            raise HTTPException(403, "Crew record write denied.")
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
    def report_symptom(crew_id: str, report: SymptomInput, member=Depends(viewer)):
        crew_id = crew_id.lower()
        if member["id"] != crew_id:
            raise HTTPException(403, "Crew record write denied.")
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
    def answer_symptom(event_id: int, answer: SymptomAnswer, member=Depends(viewer)):
        with closing(connect(db_path)) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            event = connection.execute("SELECT * FROM event WHERE id = ?", (event_id,)).fetchone()
            if event is None:
                return event_error()
            require_event_access(event, member, write=True)
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
    def stream_event(event_id: int, demo_viewer: str | None = None, member=Depends(viewer)):
        if demo_viewer is not None:
            member = viewer(demo_viewer)
        row = get_event(event_id)
        if row is None:
            return event_error()
        require_event_access(row, member)
        state = json.loads(row["pipeline"] or "{}")
        old_stages = ["collect", "rules", "done" if row["level"] == "warning" else "hold"]
        stages = state.get("stages", old_stages)
        if stages[-1] == "rules" or (stages[-1] == "question" and "answer" not in state):
            return event_error("event_not_ready", "The report is still processing or awaiting an answer.", 409)
        if stages[-1] not in ("done", "hold"):
            require_event_access(row, member, write=True)

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

    @app.get("/tx", dependencies=[Depends(cmo_viewer)])
    def read_queue():
        with closing(connect(db_path)) as connection:
            return packets(connection)

    def queue_summary(connection, request: QueueRequest, timestamp, member):
        if request.event_id is not None:
            event = connection.execute("SELECT * FROM event WHERE id = ?", (request.event_id,)).fetchone()
            if event is None:
                return JSONResponse(
                    status_code=404,
                    content={"error": {"code": "event_not_found", "message": "Event not found."}},
                )
            require_event_access(event, member)
            enqueue_event(connection, event)
        else:
            sol = mission_sol(timestamp)
            for crew in connection.execute("SELECT id FROM crew WHERE cmo_access = 1 OR cmo = 1"):
                crew_id = crew["id"]
                enqueue_daily(connection, crew_id, sol, today(connection, crew_id, sol))
        return None

    @app.post("/tx")
    def queue_transmission(request: QueueRequest, member=Depends(cmo_viewer)):
        with closing(connect(db_path)) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            error = queue_summary(connection, request, clock, member)
            return error if error is not None else packets(connection)

    @app.post("/tx/send")
    def send_transmissions(request: QueueRequest | None = None, member=Depends(cmo_viewer)):
        with closing(connect(db_path)) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            timestamp = clock
            if request is not None:
                error = queue_summary(connection, request, timestamp, member)
                if error is not None:
                    return error
            window_id = active_window(timestamp)
            if window_id is not None:
                dispatch(connection, window_id)
            return packets(connection)

    @app.post("/tx/{seq}/receipt", dependencies=[Depends(cmo_viewer)])
    def receive_transmission(seq: int, result: DeliveryResult):
        with closing(connect(db_path)) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            if visible_packet(connection, seq) is None:
                return event_error("packet_not_found", "Packet not found.")
            if not record_delivery(connection, seq, result):
                return event_error("invalid_receipt", "Receipt does not match the packet's current attempt.", 409)
            return packets(connection)

    @app.post("/tx/{seq}/simulate", dependencies=[Depends(cmo_viewer)])
    def simulate_link(seq: int, simulation: LinkSimulation):
        with closing(connect(db_path)) as connection:
            packet = visible_packet(connection, seq)
        if packet is None:
            return JSONResponse(
                status_code=404,
                content={"error": {"code": "packet_not_found", "message": "Packet not found."}},
            )
        return {"seq": seq, **compare_packet(packet["payload"], simulation)}

    @app.get("/events/{event_id}")
    def read_event(event_id: int, member=Depends(viewer)):
        event = get_event(event_id)
        require_event_access(event, member)
        return event_error() if event is None else event_payload(event)

    @app.post("/events/{event_id}/share")
    def share_event(event_id: int, member=Depends(viewer)):
        with closing(connect(db_path)) as connection, connection:
            event = connection.execute(
                "UPDATE event SET shared = 1 WHERE id = ? AND crew_id = ? RETURNING *", (event_id, member["id"]),
            ).fetchone()
            if event is None:
                require_event_access(get_event(event_id), member, write=True)
            return event_error() if event is None else event_payload(event)

    def resolve_event(event_id: int, override: EventOverride | None, member):
        reason = override.reason if override else "resolved"
        note = override.note if override else None
        with closing(connect(db_path)) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            event = connection.execute("SELECT * FROM event WHERE id = ?", (event_id,)).fetchone()
            if event is None:
                return event_error()
            require_event_access(event, member, write=True)
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
    def close_event(event_id: int, member=Depends(viewer)):
        return resolve_event(event_id, None, member)

    @app.post("/events/{event_id}/override")
    def override_event(event_id: int, override: EventOverride, member=Depends(viewer)):
        return resolve_event(event_id, override, member)

    return app


app = create_app()
