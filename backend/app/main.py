from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.devin_client import close_client
from app.models import HealthResponse, MetricsResponse, OrchestratedSession
from app.poller import start_polling, stop_polling
from app.storage import compute_metrics, get_all_sessions, get_session
from app.webhook import router as webhook_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Devin Orchestrator")
    start_polling()
    yield
    logger.info("Shutting down Devin Orchestrator")
    stop_polling()
    await close_client()


app = FastAPI(
    title="Devin Orchestrator",
    description="Orchestrates Devin sessions triggered by GitHub issue creation",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router)


@app.get("/api/sessions", response_model=list[OrchestratedSession])
async def list_sessions():
    sessions = get_all_sessions()
    return sorted(sessions, key=lambda s: s.created_at, reverse=True)


@app.get("/api/sessions/{session_id}", response_model=OrchestratedSession)
async def get_session_detail(session_id: str):
    session = get_session(session_id)
    if not session:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.get("/api/metrics", response_model=MetricsResponse)
async def get_metrics():
    return compute_metrics()


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    sessions = get_all_sessions()
    active = sum(
        1
        for s in sessions
        if s.status in ("pending", "running")
    )
    return HealthResponse(
        active_sessions=active,
        total_sessions=len(sessions),
    )
