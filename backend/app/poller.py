from __future__ import annotations

import asyncio
import logging
import time

from app.config import settings
from app.devin_client import get_session as devin_get_session
from app.models import PullRequestInfo, SessionStatus
from app.storage import get_active_sessions, save_session

logger = logging.getLogger(__name__)

DEVIN_STATUS_MAP: dict[str, SessionStatus] = {
    "running": SessionStatus.RUNNING,
    "new": SessionStatus.PENDING,
    "claimed": SessionStatus.PENDING,
    "exit": SessionStatus.COMPLETED,
    "error": SessionStatus.FAILED,
    "suspended": SessionStatus.SUSPENDED,
    "resuming": SessionStatus.RUNNING,
}

TERMINAL_STATUSES = {SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.SUSPENDED}

_polling_task: asyncio.Task | None = None


async def _poll_once() -> None:
    active = get_active_sessions()
    if not active:
        return

    logger.debug("Polling %d active sessions", len(active))

    for session in active:
        try:
            data = await devin_get_session(session.session_id)
            devin_status = data.get("status", "running")
            session.status = DEVIN_STATUS_MAP.get(devin_status, SessionStatus.RUNNING)
            session.status_detail = data.get("status_detail")
            session.acus_consumed = data.get("acus_consumed", session.acus_consumed)

            prs = data.get("pull_requests", [])
            if prs:
                session.pull_requests = [
                    PullRequestInfo(
                        url=pr.get("url", ""),
                        title=pr.get("title"),
                        number=pr.get("number"),
                    )
                    for pr in prs
                ]

            if session.status in TERMINAL_STATUSES:
                session.completed_at = time.time()
                session.duration_seconds = round(session.completed_at - session.created_at, 1)
                if session.status == SessionStatus.FAILED:
                    session.error = data.get("status_detail", "Unknown error")

            save_session(session)

        except Exception:
            logger.exception("Error polling session %s", session.session_id)


async def _poll_loop() -> None:
    while True:
        try:
            await _poll_once()
        except Exception:
            logger.exception("Unexpected error in poll loop")
        await asyncio.sleep(settings.poll_interval_seconds)


def start_polling() -> None:
    global _polling_task
    if _polling_task is None or _polling_task.done():
        _polling_task = asyncio.create_task(_poll_loop())
        logger.info(
            "Started session poller (interval: %ds)", settings.poll_interval_seconds
        )


def stop_polling() -> None:
    global _polling_task
    if _polling_task and not _polling_task.done():
        _polling_task.cancel()
        _polling_task = None
        logger.info("Stopped session poller")
