from __future__ import annotations

import json
import logging
from pathlib import Path
from threading import Lock

from app.config import settings
from app.models import MetricsResponse, OrchestratedSession, SessionStatus

logger = logging.getLogger(__name__)

_lock = Lock()


def _data_path() -> Path:
    return Path(settings.data_file_path)


def _read_all() -> list[dict]:
    path = _data_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        logger.warning("Corrupted data file, starting fresh")
        return []


def _write_all(records: list[dict]) -> None:
    path = _data_path()
    path.write_text(json.dumps(records, indent=2, default=str))


def save_session(session: OrchestratedSession) -> None:
    with _lock:
        records = _read_all()
        existing_idx = next(
            (i for i, r in enumerate(records) if r["session_id"] == session.session_id),
            None,
        )
        data = session.model_dump()
        if existing_idx is not None:
            records[existing_idx] = data
        else:
            records.append(data)
        _write_all(records)


def get_all_sessions() -> list[OrchestratedSession]:
    with _lock:
        records = _read_all()
    return [OrchestratedSession(**r) for r in records]


def get_session(session_id: str) -> OrchestratedSession | None:
    sessions = get_all_sessions()
    return next((s for s in sessions if s.session_id == session_id), None)


def get_active_sessions() -> list[OrchestratedSession]:
    return [
        s
        for s in get_all_sessions()
        if s.status in (SessionStatus.PENDING, SessionStatus.RUNNING)
    ]


def compute_metrics() -> MetricsResponse:
    sessions = get_all_sessions()
    total = len(sessions)
    if total == 0:
        return MetricsResponse()

    active = sum(1 for s in sessions if s.status in (SessionStatus.PENDING, SessionStatus.RUNNING))
    completed = sum(1 for s in sessions if s.status == SessionStatus.COMPLETED)
    failed = sum(1 for s in sessions if s.status == SessionStatus.FAILED)
    total_acus = sum(s.acus_consumed for s in sessions)

    finished = completed + failed
    success_rate = (completed / finished * 100) if finished > 0 else 0.0

    durations = [s.duration_seconds for s in sessions if s.duration_seconds is not None]
    avg_resolution = sum(durations) / len(durations) if durations else None

    return MetricsResponse(
        total_sessions=total,
        active_sessions=active,
        completed_sessions=completed,
        failed_sessions=failed,
        success_rate=round(success_rate, 1),
        total_acus=round(total_acus, 2),
        avg_acus_per_session=round(total_acus / total, 2) if total > 0 else 0.0,
        avg_resolution_seconds=round(avg_resolution, 1) if avg_resolution else None,
    )
