from __future__ import annotations

import logging
import re

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        headers: dict[str, str] = {
            "Accept": "application/vnd.github.v3+json",
        }
        if settings.github_token:
            headers["Authorization"] = f"token {settings.github_token}"
        _client = httpx.AsyncClient(
            base_url="https://api.github.com",
            headers=headers,
            timeout=15.0,
        )
    return _client


def parse_pr_repo_and_number(pr_url: str) -> tuple[str, int] | None:
    """Extract owner/repo and PR number from a GitHub PR URL."""
    match = re.match(r"https://github\.com/([^/]+/[^/]+)/pull/(\d+)", pr_url)
    if match:
        return match.group(1), int(match.group(2))
    return None


async def get_pr_status(repo: str, pr_number: int) -> dict:
    """Get the merge status of a pull request."""
    client = _get_client()
    response = await client.get(f"/repos/{repo}/pulls/{pr_number}")
    response.raise_for_status()
    data = response.json()
    return {
        "merged": data.get("merged", False),
        "state": data.get("state", "open"),
        "merged_at": data.get("merged_at"),
    }


async def close_issue(repo: str, issue_number: int) -> bool:
    """Close a GitHub issue. Returns True if successful."""
    if not settings.github_token:
        logger.warning("No GITHUB_TOKEN configured, cannot close issue #%d", issue_number)
        return False
    client = _get_client()
    response = await client.patch(
        f"/repos/{repo}/issues/{issue_number}",
        json={"state": "closed", "state_reason": "completed"},
    )
    if response.status_code == 200:
        logger.info("Closed issue #%d on %s", issue_number, repo)
        return True
    logger.warning(
        "Failed to close issue #%d on %s: %d %s",
        issue_number,
        repo,
        response.status_code,
        response.text,
    )
    return False


async def add_issue_comment(repo: str, issue_number: int, body: str) -> bool:
    """Add a comment to a GitHub issue. Returns True if successful."""
    if not settings.github_token:
        return False
    client = _get_client()
    response = await client.post(
        f"/repos/{repo}/issues/{issue_number}/comments",
        json={"body": body},
    )
    return response.status_code == 201


async def merge_pr(repo: str, pr_number: int) -> bool:
    """Merge a pull request. Returns True if successful."""
    if not settings.github_token:
        logger.warning("No GITHUB_TOKEN configured, cannot merge PR #%d", pr_number)
        return False
    client = _get_client()
    response = await client.put(
        f"/repos/{repo}/pulls/{pr_number}/merge",
        json={"merge_method": "squash"},
    )
    if response.status_code == 200:
        logger.info("Auto-merged PR #%d on %s", pr_number, repo)
        return True
    logger.warning(
        "Failed to merge PR #%d on %s: %d %s",
        pr_number,
        repo,
        response.status_code,
        response.text,
    )
    return False


async def get_pr_check_status(repo: str, pr_number: int) -> dict:
    """Get the combined CI check status for a PR's head commit.

    Returns {"state": "success"|"failure"|"pending"|"no_checks",
             "total": int, "passed": int, "failed": int}.
    """
    client = _get_client()
    # First get the PR to find the head SHA
    pr_resp = await client.get(f"/repos/{repo}/pulls/{pr_number}")
    pr_resp.raise_for_status()
    head_sha = pr_resp.json().get("head", {}).get("sha", "")
    if not head_sha:
        return {"state": "no_checks", "total": 0, "passed": 0, "failed": 0}

    # Get combined status
    status_resp = await client.get(f"/repos/{repo}/commits/{head_sha}/status")
    status_resp.raise_for_status()
    status_data = status_resp.json()

    # Also check GitHub Actions check runs
    checks_resp = await client.get(f"/repos/{repo}/commits/{head_sha}/check-runs")
    checks_resp.raise_for_status()
    checks_data = checks_resp.json()
    check_runs = checks_data.get("check_runs", [])

    statuses = status_data.get("statuses", [])
    total = len(statuses) + len(check_runs)
    if total == 0:
        return {"state": "no_checks", "total": 0, "passed": 0, "failed": 0}

    passed = sum(1 for s in statuses if s.get("state") == "success")
    passed += sum(1 for c in check_runs if c.get("conclusion") == "success")
    failed = sum(1 for s in statuses if s.get("state") == "failure")
    failed += sum(1 for c in check_runs if c.get("conclusion") == "failure")
    pending = total - passed - failed

    if failed > 0:
        state = "failure"
    elif pending > 0:
        state = "pending"
    else:
        state = "success"

    return {"state": state, "total": total, "passed": passed, "failed": failed}


async def add_pr_comment(repo: str, pr_number: int, body: str) -> bool:
    """Add a comment to a pull request. Returns True if successful."""
    if not settings.github_token:
        return False
    client = _get_client()
    response = await client.post(
        f"/repos/{repo}/issues/{pr_number}/comments",
        json={"body": body},
    )
    return response.status_code == 201


async def close_github_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None
