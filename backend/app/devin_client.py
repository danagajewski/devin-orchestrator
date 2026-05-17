from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url=settings.devin_api_base_url,
            headers={
                "Authorization": f"Bearer {settings.devin_api_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
    return _client


async def create_session(
    prompt: str,
    title: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    client = _get_client()
    payload: dict = {
        "prompt": prompt,
        "repos": [settings.target_repo],
    }
    if title:
        payload["title"] = title
    if tags:
        payload["tags"] = tags

    response = await client.post(
        f"/organizations/{settings.devin_org_id}/sessions",
        json=payload,
    )
    response.raise_for_status()
    data = response.json()
    logger.info("Created Devin session: %s", data.get("session_id"))
    return data


async def get_session(session_id: str) -> dict:
    client = _get_client()
    response = await client.get(
        f"/organizations/{settings.devin_org_id}/sessions/{session_id}",
    )
    response.raise_for_status()
    return response.json()


async def close_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None
