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
from backend.mission import ClockUpdate, DEMO_TIME, mission_sol, mission_status
from backend.seed import DEMO_DB, seed
from backend.today import today


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
            return {"event_id": event_id, "needs_question": False}

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
