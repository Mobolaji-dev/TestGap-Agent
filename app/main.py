from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent.telemetry import initialize_neatlogs, neatlogs_status, shutdown_neatlogs
from api.v1.projects import router as projects_router
from api.v1.runs import router as runs_router
from app.config.settings import settings
from db.repository.run_repository import run_repository

@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_neatlogs()
    try:
        yield
    finally:
        shutdown_neatlogs()
        run_repository.close()


app = FastAPI(
    title="TestGap Finder API",
    version="0.1.0",
    description="Agent-assisted discovery and verification of Python test gaps.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(projects_router, prefix=settings.api_prefix)
app.include_router(runs_router, prefix=settings.api_prefix)


@app.get("/health", tags=["health"])
async def health() -> dict[str, object]:
    database = run_repository.health()
    return {
        "status": "ok" if database["connected"] else "degraded",
        "database": database,
        "neatlogs": neatlogs_status(),
    }
