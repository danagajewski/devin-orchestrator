from __future__ import annotations

import time
from enum import Enum

from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SUSPENDED = "suspended"
    MERGED = "merged"


class PullRequestInfo(BaseModel):
    url: str
    title: str | None = None
    number: int | None = None
    merged: bool = False
    merged_at: str | None = None


class OrchestratedSession(BaseModel):
    session_id: str
    devin_url: str
    github_issue_number: int
    github_issue_title: str
    github_issue_url: str
    github_issue_labels: list[str] = Field(default_factory=list)
    status: SessionStatus = SessionStatus.PENDING
    status_detail: str | None = None
    acus_consumed: float = 0.0
    estimated_acus: float | None = None
    num_user_messages: int | None = None
    num_devin_messages: int | None = None
    session_size: str | None = None
    created_at: float = Field(default_factory=time.time)
    completed_at: float | None = None
    duration_seconds: float | None = None
    pull_requests: list[PullRequestInfo] = Field(default_factory=list)
    error: str | None = None
    issue_closed: bool = False
    issue_closed_at: float | None = None


class MetricsResponse(BaseModel):
    total_sessions: int = 0
    active_sessions: int = 0
    completed_sessions: int = 0
    failed_sessions: int = 0
    success_rate: float = 0.0
    total_acus: float = 0.0
    avg_acus_per_session: float = 0.0
    total_estimated_acus: float = 0.0
    avg_estimated_acus: float = 0.0
    avg_resolution_seconds: float | None = None


class WebhookEvent(BaseModel):
    action: str
    issue: dict
    repository: dict
    sender: dict


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    active_sessions: int = 0
    total_sessions: int = 0
