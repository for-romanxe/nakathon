from contextlib import asynccontextmanager, closing
from threading import Lock
from typing import Literal

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.checkin import Checkin, save_checkin
from backend.db import connect, initialize
from backend.events import SymptomInput, event_payload, save_event
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


def create_app(db_path=DEMO_DB) -> FastAPI:
    clock = DEMO_TIME
    clock_lock = Lock()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
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
            return {"event_id": event_id, "needs_question": False}

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

    @app.get("/events/{event_id}")
    def read_event(event_id: int):
        with closing(connect(db_path)) as connection:
            event = connection.execute("SELECT * FROM event WHERE id = ?", (event_id,)).fetchone()
            if event is None:
                return JSONResponse(
                    status_code=404,
                    content={"error": {"code": "event_not_found", "message": "Event not found."}},
                )
            return event_payload(event)

    return app


app = create_app()
