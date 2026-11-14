from contextlib import asynccontextmanager, closing

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.db import connect, initialize
from backend.seed import DEMO_DB, DEMO_SOL, seed
from backend.today import today


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
        allow_methods=["GET"],
    )

    @app.get("/crew/{crew_id}/today")
    def read_today(crew_id: str):
        with closing(connect(db_path)) as connection:
            crew = connection.execute("SELECT id FROM crew WHERE id = ?", (crew_id,)).fetchone()
            if crew is None:
                return JSONResponse(
                    status_code=404,
                    content={"error": {"code": "crew_not_found", "message": "Crew member not found."}},
                )
            return today(connection, crew_id, DEMO_SOL)

    return app


app = create_app()
