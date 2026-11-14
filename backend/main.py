from contextlib import asynccontextmanager, closing

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.checkin import Checkin, save_checkin
from backend.db import connect, initialize
from backend.seed import DEMO_DB, DEMO_SOL, seed
from backend.today import today


def crew_not_found() -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"error": {"code": "crew_not_found", "message": "Crew member not found."}},
    )


def create_app(db_path=DEMO_DB) -> FastAPI:
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
            content={"error": {"code": "invalid_request", "message": error.errors()[0]["msg"]}},
        )

    @app.get("/crew/{crew_id}/today")
    def read_today(crew_id: str):
        crew_id = crew_id.lower()
        with closing(connect(db_path)) as connection:
            crew = connection.execute("SELECT id FROM crew WHERE id = ?", (crew_id,)).fetchone()
            if crew is None:
                return crew_not_found()
            return today(connection, crew_id, DEMO_SOL)

    @app.post("/crew/{crew_id}/checkin")
    def submit_checkin(crew_id: str, checkin: Checkin):
        crew_id = crew_id.lower()
        with closing(connect(db_path)) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            crew = connection.execute("SELECT id FROM crew WHERE id = ?", (crew_id,)).fetchone()
            if crew is None:
                return crew_not_found()
            current = today(connection, crew_id, DEMO_SOL)
            save_checkin(connection, crew_id, DEMO_SOL, checkin, current["status"]["level"])
            return today(connection, crew_id, DEMO_SOL)

    return app


app = create_app()
