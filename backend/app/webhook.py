from __future__ import annotations

import hashlib
import hmac
import logging
import time

from fastapi import APIRouter, Header, HTTPException, Request

from app.config import settings
from app.devin_client import create_session
from app.models import OrchestratedSession, SessionStatus
from app.poller import _parse_devin_pr, close_issue_for_session
from app.storage import get_all_sessions, save_session

logger = logging.getLogger(__name__)
router = APIRouter()


def _verify_signature(payload: bytes, signature: str | None) -> bool:
    if not settings.github_webhook_secret:
        logger.warning("No webhook secret configured, skipping signature verification")
        return True
    if not signature:
        return False
    expected = "sha256=" + hmac.new(
        settings.github_webhook_secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def _build_prompt(issue: dict, repo_full_name: str) -> str:
    number = issue.get("number", "?")
    title = issue.get("title", "Untitled")
    body = issue.get("body") or "No description provided."
    labels = [lbl.get("name", "") for lbl in issue.get("labels", [])]
    issue_url = issue.get("html_url", "")

    label_str = ", ".join(labels) if labels else "None"

    return f"""You are working on the repository {repo_full_name}.

A new GitHub issue has been created that needs to be resolved:

**Issue #{number}: {title}**

{body}

Labels: {label_str}
Issue URL: {issue_url}

Please analyze this issue carefully and implement a fix. Create a pull request \
with your changes. Reference issue #{number} in your PR title and description. \
Follow the repository's existing code style and conventions."""


@router.post("/webhook/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(None),
    x_github_event: str | None = Header(None),
):
    body = await request.body()

    if not _verify_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid signature")

    if x_github_event == "pull_request":
        return await _handle_pull_request_event(body, request)

    if x_github_event != "issues":
        return {"status": "ignored", "reason": f"Event type '{x_github_event}' not handled"}

    payload = await request.json()
    action = payload.get("action")

    if action != "opened":
        return {"status": "ignored", "reason": f"Action '{action}' not handled"}

    issue = payload.get("issue", {})
    repo = payload.get("repository", {})
    repo_full_name = repo.get("full_name", settings.target_repo)

    issue_number = issue.get("number", 0)
    issue_title = issue.get("title", "Untitled")
    issue_url = issue.get("html_url", "")
    labels = [lbl.get("name", "") for lbl in issue.get("labels", [])]

    prompt = _build_prompt(issue, repo_full_name)

    try:
        result = await create_session(
            prompt=prompt,
            title=f"Fix issue #{issue_number}: {issue_title}",
            tags=["orchestrator", f"issue-{issue_number}"],
        )

        session_id = result.get("session_id", "")
        devin_url = result.get("url", f"https://app.devin.ai/sessions/{session_id}")

        prs = [
            _parse_devin_pr(pr)
            for pr in result.get("pull_requests", [])
        ]

        orchestrated = OrchestratedSession(
            session_id=session_id,
            devin_url=devin_url,
            github_issue_number=issue_number,
            github_issue_title=issue_title,
            github_issue_url=issue_url,
            github_issue_labels=labels,
            status=SessionStatus.RUNNING,
            status_detail=result.get("status_detail"),
            acus_consumed=result.get("acus_consumed", 0.0),
            created_at=time.time(),
            pull_requests=prs,
        )
        save_session(orchestrated)

        logger.info(
            "Created Devin session %s for issue #%d: %s",
            session_id,
            issue_number,
            issue_title,
        )

        return {
            "status": "session_created",
            "session_id": session_id,
            "devin_url": devin_url,
            "issue_number": issue_number,
        }

    except Exception:
        logger.exception("Failed to create Devin session for issue #%d", issue_number)
        raise HTTPException(status_code=500, detail="Failed to create Devin session")


async def _handle_pull_request_event(raw_body: bytes, request: Request) -> dict:
    """Handle pull_request webhook events to detect merges."""
    payload = await request.json()
    action = payload.get("action")
    pr_data = payload.get("pull_request", {})
    merged = pr_data.get("merged", False)

    if action != "closed" or not merged:
        reason = f"PR action '{action}' (merged={merged}) not handled"
        return {"status": "ignored", "reason": reason}

    pr_number = pr_data.get("number")
    pr_url = pr_data.get("html_url", "")
    merged_at = pr_data.get("merged_at")

    logger.info("PR #%d merged, checking for matching sessions", pr_number)

    sessions = get_all_sessions()
    matched = False

    for session in sessions:
        if session.issue_closed:
            continue
        for pr in session.pull_requests:
            if pr.number == pr_number or pr.url == pr_url:
                pr.merged = True
                pr.merged_at = merged_at
                matched = True
                logger.info(
                    "Matched merged PR #%d to session %s (issue #%d)",
                    pr_number,
                    session.session_id,
                    session.github_issue_number,
                )
                await close_issue_for_session(session)
                save_session(session)
                break

    if not matched:
        logger.debug("Merged PR #%d did not match any tracked session", pr_number)
        return {"status": "ignored", "reason": "PR not linked to any tracked session"}

    return {"status": "issue_closed", "pr_number": pr_number}
