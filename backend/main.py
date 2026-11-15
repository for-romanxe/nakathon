import json
import logging
import os
import sqlite3
from contextlib import asynccontextmanager, closing
from pathlib import Path
from threading import Lock
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, StrictBool, field_validator
from backend.auth import CrewLogin, CrewSessions, SESSION_COOKIE, SESSION_SECONDS

from backend.checkin import Checkin, save_checkin
from backend.db import connect, initialize
from backend.docs import build_docs
from backend import event_flow, habitat
from backend.model import pipeline
from backend.events import EventOverride, SymptomAnswer, SymptomInput, event_payload, save_event
from backend.link_simulation import LinkSimulation, compare_packet
from backend.medication import (
    PRODUCT_ID, MedicationIntake, ProductIntake, intake_summary, load_medication_references, read_intakes, save_intake,
)
from backend.mission import ClockUpdate, DEMO_TIME, active_window, mission_sol, mission_status
from backend.preflight import PreflightUpdate, read_preflight, save_preflight
from backend.seed import CONTRACT, CREW, DEMO_DB, seed
from backend.today import today
from backend.trends import trends
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


class HabitatChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str | None = None

    @field_validator("reason")
    @classmethod
    def trim_reason(cls, value):
        if value is None:
            return None
        value = value.strip()
        if len(value) > 240:
            raise ValueError("Reason must be at most 240 characters.")
        return value or None


def habitat_cite_ids(evidence) -> dict:
    known = set()
    for item in evidence:
        if isinstance(item, dict) and isinstance(item.get("id"), str) and isinstance(item.get("text"), str):
            known.add(item["id"])
    try:
        data = json.loads(pipeline.ADJUSTMENTS.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, AttributeError):
        return {}
    if not isinstance(data, dict):
        return {}
    result = {}
    for target, entry in data.items():
        ids = entry.get("cite_ids") if isinstance(entry, dict) else None
        if isinstance(target, str) and isinstance(ids, list):
            result[target] = tuple(i for i in ids if isinstance(i, str) and i in known)
    return result


def habitat_fallback_evidence(evidence) -> list:
    """Add bundled English habitat citation paragraphs when no evidence file is configured."""
    if os.environ.get("CREW_HEALTH_EVIDENCE"):
        return evidence
    try:
        from ml.knowledge.export_evidence import export
        bundled = [item for item in export("en") if isinstance(item, dict)]
    except Exception:
        logging.getLogger(__name__).warning("Bundled habitat evidence could not be loaded.")
        return evidence
    wanted = {cite for ids in habitat_cite_ids(bundled).values() for cite in ids}
    present = {item.get("id") for item in evidence if isinstance(item, dict) and isinstance(item.get("id"), str)}
    extra = [item for item in bundled
             if isinstance(item.get("id"), str) and item["id"] in wanted and item["id"] not in present]
    return [*evidence, *extra]


def create_app(db_path=DEMO_DB) -> FastAPI:
    clock = DEMO_TIME
    clock_lock = Lock()
    event_locks = [Lock() for _ in range(32)]
    evidence = []
    docs = []
    cite_ids = {}
    medication_references = []
    medication_catalog_failed = False
    sessions = None
    frontend_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        nonlocal evidence, sessions, docs, medication_references, medication_catalog_failed, cite_ids
        sessions = CrewSessions(crew_id for crew_id, *_ in CREW)
        evidence = event_flow.load_evidence()
        try:
            medication_references = load_medication_references()
            medication_catalog_failed = False
        except (OSError, ValueError):
            logging.getLogger(__name__).warning("Medication catalog could not be loaded.")
            medication_references = []
            medication_catalog_failed = True
        initialize(db_path)
        with closing(connect(db_path)) as connection:
            seed(connection)
            mission_fixture = habitat.is_rehearsal(connection)
        if mission_fixture:
            evidence = habitat_fallback_evidence(evidence)
        docs = build_docs(evidence)
        cite_ids = habitat_cite_ids(evidence)
        with clock_lock, closing(connect(db_path)) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            habitat.sync(connection, clock, cite_ids)
        yield

    app = FastAPI(title="Crew Health Demo API", lifespan=lifespan, docs_url="/api/docs",
                  swagger_ui_oauth2_redirect_url="/api/docs/oauth2-redirect")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=frontend_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Content-Type", "X-Demo-Viewer"],
    )

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, error: RequestValidationError):
        message = "Invalid login request." if request.url.path == "/session/login" else str(error.errors()[0]["msg"])
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "invalid_request", "message": message}},
        )

    @app.get("/docs")
    def list_docs():
        return docs

    @app.get("/docs/{doc_id}")
    def get_doc(doc_id: str):
        found = next((doc for doc in docs if doc["id"] == doc_id), None)
        return found if found else event_error("doc_not_found", "Document not found.")

    def get_crew_member(crew_id):
        with closing(connect(db_path)) as connection:
            return connection.execute("SELECT * FROM crew WHERE id = ?", (crew_id.lower(),)).fetchone()

    def check_origin(request: Request):
        origin = request.headers.get("origin")
        if sessions.codes is not None and origin and request.method not in ("GET", "HEAD"):
            if origin not in frontend_origins and origin != str(request.base_url).rstrip("/"):
                raise HTTPException(403, "Request origin is not allowed.")

    def resolve_viewer(request: Request, header_id=None, query_id=None):
        check_origin(request)
        if sessions.codes is not None:
            crew_id = sessions.member_id(request.cookies.get(SESSION_COOKIE))
            if crew_id is None:
                raise HTTPException(401, "Sign in to continue.")
        else:
            if header_id is not None and query_id is not None and header_id.lower() != query_id.lower():
                raise HTTPException(400, "Conflicting demo viewer IDs.")
            crew_id = header_id if header_id is not None else query_id
            if crew_id is None:
                crew_id = "c1"
        member = get_crew_member(crew_id)
        if member is None:
            raise HTTPException(403, "Invalid demo viewer.")
        return member

    def viewer(request: Request, demo_viewer: str | None = Header(None, alias="X-Demo-Viewer")):
        return resolve_viewer(request, demo_viewer)

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

    def can_read_crew(connection, crew_id, member):
        crew = connection.execute("SELECT id, cmo_access FROM crew WHERE id = ?", (crew_id,)).fetchone()
        if crew is not None and not may_access(member, crew):
            raise HTTPException(403, "Crew record access denied.")
        return crew is not None

    @app.exception_handler(HTTPException)
    async def http_error(request, error: HTTPException):
        code = {401: "unauthorized", 403: "forbidden"}.get(error.status_code, "http_error")
        return event_error(code, error.detail, error.status_code)

    @app.get("/session")
    def read_session(request: Request):
        if sessions.codes is None:
            return {"login_required": False, "crew_id": None}
        return {"login_required": True, "crew_id": sessions.member_id(request.cookies.get(SESSION_COOKIE))}

    @app.post("/session/login", dependencies=[Depends(check_origin)])
    def login(request: Request, credentials: CrewLogin):
        if sessions.codes is None:
            return event_error("login_disabled", "Login is disabled in demo mode.", 409)
        token = sessions.login(credentials)
        if token is None:
            raise HTTPException(401, "Invalid crew ID or access code.")
        sessions.logout(request.cookies.get(SESSION_COOKIE))
        response = JSONResponse({"crew_id": credentials.crew_id.lower()})
        response.set_cookie(SESSION_COOKIE, token, max_age=SESSION_SECONDS, httponly=True,
                            secure=request.url.scheme == "https", samesite="strict")
        return response

    @app.post("/session/logout", dependencies=[Depends(check_origin)])
    def logout(request: Request):
        sessions.logout(request.cookies.get(SESSION_COOKIE))
        response = JSONResponse({"crew_id": None})
        response.delete_cookie(SESSION_COOKIE)
        return response

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
        if sessions.codes is not None:
            raise HTTPException(403, "Demo viewer switching is disabled while login is enabled.")
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
    def update_clock(request: Request, update: ClockUpdate):
        nonlocal clock
        if sessions.codes is not None:
            cmo_viewer(resolve_viewer(request))
        with clock_lock:
            upcoming = update.apply(clock)
            response = mission_status(upcoming)
            try:
                with closing(connect(db_path)) as connection, connection:
                    connection.execute("BEGIN IMMEDIATE")
                    habitat.sync(connection, upcoming, cite_ids)
            except sqlite3.Error:
                logging.getLogger(__name__).exception("clock sync failed")
                return JSONResponse(status_code=503, content={"error": {
                    "code": "clock_sync_failed", "message": "Clock not changed; storage unavailable."}})
            clock = upcoming
            return response

    @app.get("/habitat/actions")
    def read_habitat_actions(crew: str = Query(...), lang: Literal["en", "ko"] = "en", member=Depends(viewer)):
        crew_id = crew.lower()
        with closing(connect(db_path)) as connection:
            if not can_read_crew(connection, crew_id, member):
                return crew_not_found()
            return [habitat.payload(row, lang) for row in habitat.list_actions(connection, crew_id, mission_sol(clock))]

    def change_habitat(action_id, command, body, member, lang="en"):
        reason = body.reason if body is not None else None
        with clock_lock, closing(connect(db_path)) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            row = habitat.action(connection, action_id) if action_id > 0 else None
            if row is None:
                return event_error("action_not_found", "Habitat action not found.")
            if row["crew_id"] != member["id"]:
                raise HTTPException(403, "Habitat action write denied.")
            updated = habitat.change(connection, row, command, member["id"], clock, reason=reason)
            if updated is None:
                return event_error("action_stale", "Habitat action is no longer in that state.", 409)
            return habitat.payload(updated, lang)

    @app.post("/habitat/actions/{action_id}/approve")
    def approve_habitat(action_id: int, body: HabitatChange | None = None, lang: Literal["en", "ko"] = "en",
                        member=Depends(viewer)):
        return change_habitat(action_id, "approve", body, member, lang)

    @app.post("/habitat/actions/{action_id}/undo")
    def undo_habitat(action_id: int, body: HabitatChange | None = None, lang: Literal["en", "ko"] = "en",
                     member=Depends(viewer)):
        return change_habitat(action_id, "undo", body, member, lang)

    @app.get("/crew/{crew_id}/today")
    def read_today(crew_id: str, lang: Literal["en", "ko"] = "en", member=Depends(viewer)):
        crew_id = crew_id.lower()
        with closing(connect(db_path)) as connection:
            if not can_read_crew(connection, crew_id, member):
                return crew_not_found()
            return today(connection, crew_id, mission_sol(clock), lang)

    @app.get("/crew/{crew_id}/preflight")
    def get_preflight(crew_id: str, member=Depends(viewer)):
        crew_id = crew_id.lower()
        with closing(connect(db_path)) as connection, connection:
            connection.execute("BEGIN")
            if not can_read_crew(connection, crew_id, member):
                return crew_not_found()
            return read_preflight(connection, crew_id)

    @app.put("/crew/{crew_id}/preflight")
    def update_preflight(crew_id: str, update: PreflightUpdate, member=Depends(viewer)):
        crew_id = crew_id.lower()
        if member["id"] != crew_id:
            raise HTTPException(403, "Crew record write denied.")
        with closing(connect(db_path)) as connection, connection:
            return save_preflight(connection, crew_id, update)

    @app.get("/medication-references")
    def get_medication_references(member=Depends(viewer)):
        if medication_catalog_failed:
            return event_error("medication_catalog_invalid", "Medication catalog could not be loaded.", 503)
        return {"references": [reference.model_dump(mode="json", exclude_none=True) for reference in medication_references]}

    @app.get("/crew/{crew_id}/medication-intakes")
    def get_medication_intakes(crew_id: str, member=Depends(viewer)):
        crew_id = crew_id.lower()
        with closing(connect(db_path)) as connection:
            # Read consent and intake history from the same snapshot.
            connection.execute("BEGIN")
            try:
                if not can_read_crew(connection, crew_id, member):
                    return crew_not_found()
                return {"entries": read_intakes(connection, crew_id)}
            finally:
                connection.rollback()

    @app.get("/crew/{crew_id}/medication-intake-summary")
    def get_medication_intake_summary(
        crew_id: str, product_id: str = Query(pattern=PRODUCT_ID, max_length=80), member=Depends(viewer),
    ):
        crew_id = crew_id.lower()
        with closing(connect(db_path)) as connection:
            connection.execute("BEGIN")
            try:
                if not can_read_crew(connection, crew_id, member):
                    return crew_not_found()
                reference = next((row for row in medication_references if row.id == product_id), None)
                if reference is None or reference.count_unit is None:
                    return event_error("intake_product_unavailable", "This product has no configured count unit.", 404)
                return intake_summary(connection, crew_id, reference, clock, medication_references)
            finally:
                connection.rollback()

    @app.post("/crew/{crew_id}/medication-intakes")
    def post_medication_intake(crew_id: str, entry: MedicationIntake | ProductIntake, member=Depends(viewer)):
        crew_id = crew_id.lower()
        if member["id"] != crew_id:
            raise HTTPException(403, "Crew record write denied.")
        try:
            with closing(connect(db_path)) as connection, connection:
                connection.execute("BEGIN IMMEDIATE")
                saved = save_intake(connection, crew_id, entry, clock, medication_references)
        except ValueError as error:
            return event_error("intake_product_unavailable", str(error), 422)
        if saved is None:
            return event_error("intake_conflict", "Request ID already used for a different intake.", 409)
        return saved

    @app.get("/crew/{crew_id}/trends")
    def read_trends(crew_id: str, metric: str, days: int = Query(14, ge=1, le=90), member=Depends(viewer)):
        if metric not in CONTRACT["metrics"]:
            return event_error("invalid_request", "Unknown metric.", 422)
        crew_id = crew_id.lower()
        with closing(connect(db_path)) as connection, connection:
            connection.execute("BEGIN")
            if not can_read_crew(connection, crew_id, member):
                return crew_not_found()
            return trends(connection, crew_id, metric, days, mission_sol(clock))

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
    def stream_event(
        request: Request, event_id: int, demo_viewer: str | None = None,
        header_id: str | None = Header(None, alias="X-Demo-Viewer"),
    ):
        member = resolve_viewer(request, header_id, demo_viewer)
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

    @app.post("/events/{event_id}/action/{i}/done")
    def complete_action(event_id: int, i: int, member=Depends(viewer)):
        with closing(connect(db_path)) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            event = connection.execute("SELECT * FROM event WHERE id = ?", (event_id,)).fetchone()
            if event is None:
                return event_error()
            require_event_access(event, member, write=True)
            state = json.loads(event["pipeline"] or "{}")
            actions = state.get("risk", {}).get("actions", [])
            if not 0 <= i < len(actions):
                return event_error("action_not_found", "Action not found.")
            if actions[i]["done"]:
                return event_payload(event)
            if event["closed_at"]:
                return event_error("event_already_closed", "The event is closed.", 409)
            actions[i]["done"] = True
            event = connection.execute(
                "UPDATE event SET pipeline = ? WHERE id = ? RETURNING *",
                (json.dumps(state), event_id),
            ).fetchone()
            return event_payload(event)

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


app = create_app(Path(os.environ.get("CREW_HEALTH_DB") or DEMO_DB))
