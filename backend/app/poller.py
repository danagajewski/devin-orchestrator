from __future__ import annotations

import asyncio
import logging
import time

from app.config import settings
from app.devin_client import get_session as devin_get_session
from app.github_client import (
    add_issue_comment,
    close_issue,
    get_pr_status,
    parse_pr_repo_and_number,
)
from app.models import PullRequestInfo, SessionStatus
from app.storage import get_active_sessions, get_all_sessions, save_session

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


async def _check_pr_merges(session) -> bool:
    """Check if any PRs for a session have been merged. Returns True if a merge was detected."""
    if not session.pull_requests:
        return False

    any_merged = False
    for pr in session.pull_requests:
        if pr.merged:
            continue
        parsed = parse_pr_repo_and_number(pr.url)
        if not parsed:
            continue
        repo, pr_number = parsed
        try:
            status = await get_pr_status(repo, pr_number)
            if status["merged"]:
                pr.merged = True
                pr.merged_at = status["merged_at"]
                any_merged = True
                logger.info(
                    "PR #%d merged for session %s (issue #%d)",
                    pr_number,
                    session.session_id,
                    session.github_issue_number,
                )
        except Exception:
            logger.exception("Error checking PR #%d status", pr_number)

    return any_merged


async def close_issue_for_session(session) -> None:
    """Close the GitHub issue associated with a session and leave a comment."""
    repo = settings.target_repo
    issue_num = session.github_issue_number

    merged_prs = [pr for pr in session.pull_requests if pr.merged]
    pr_links = ", ".join(
        f"[#{pr.number}]({pr.url})" if pr.number else f"[PR]({pr.url})"
        for pr in merged_prs
    )
    comment = (
        f"This issue has been resolved. "
        f"The following PR(s) have been merged: {pr_links}\n\n"
        f"*Closed automatically by Devin Orchestrator.*"
    )
    await add_issue_comment(repo, issue_num, comment)
    closed = await close_issue(repo, issue_num)
    if closed:
        session.issue_closed = True
        session.issue_closed_at = time.time()
        session.status = SessionStatus.MERGED
        logger.info("Closed issue #%d for session %s", issue_num, session.session_id)


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
                existing_prs = {pr.url: pr for pr in session.pull_requests}
                session.pull_requests = [
                    PullRequestInfo(
                        url=pr.get("url", ""),
                        title=pr.get("title"),
                        number=pr.get("number"),
                        merged=existing_prs.get(
                            pr.get("url", ""), PullRequestInfo(url="")
                        ).merged,
                        merged_at=existing_prs.get(
                            pr.get("url", ""), PullRequestInfo(url="")
                        ).merged_at,
                    )
                    for pr in prs
                ]

            if session.status in TERMINAL_STATUSES:
                session.completed_at = session.completed_at or time.time()
                session.duration_seconds = round(
                    session.completed_at - session.created_at, 1
                )
                if session.status == SessionStatus.FAILED:
                    session.error = data.get("status_detail", "Unknown error")

            save_session(session)

        except Exception:
            logger.exception("Error polling session %s", session.session_id)


async def _check_merges_once() -> None:
    """Check for PR merges on completed sessions that haven't had their issues closed."""
    all_sessions = get_all_sessions()
    candidates = [
        s
        for s in all_sessions
        if s.status in (SessionStatus.COMPLETED, SessionStatus.SUSPENDED)
        and s.pull_requests
        and not s.issue_closed
    ]
    if not candidates:
        return

    logger.debug("Checking PR merge status for %d sessions", len(candidates))

    for session in candidates:
        try:
            merged = await _check_pr_merges(session)
            if merged:
                await close_issue_for_session(session)
            save_session(session)
        except Exception:
            logger.exception(
                "Error checking merges for session %s", session.session_id
            )


async def _poll_loop() -> None:
    while True:
        try:
            await _poll_once()
            await _check_merges_once()
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
