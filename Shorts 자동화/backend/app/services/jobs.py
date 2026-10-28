"""Shared service helpers for analysis and short jobs."""

import logging
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.models import ANALYSIS_ACTIVE_STATUSES, SHORT_ACTIVE_STATUSES, Analysis, Short, utcnow
from app.workers.jobs import Job

log = logging.getLogger(__name__)


def utc(value: datetime | None) -> datetime | None:
    return value.replace(tzinfo=UTC) if value else None


def count_active(db: Session) -> int:
    """Running analyses and shorts together (spec 2: at most MAX_ACTIVE_JOBS at once)."""
    analyses = db.scalar(select(func.count()).where(Analysis.status.in_(ANALYSIS_ACTIVE_STATUSES)))
    shorts = db.scalar(select(func.count()).where(Short.status.in_(SHORT_ACTIVE_STATUSES)))
    return (analyses or 0) + (shorts or 0)


def check_capacity(db: Session) -> None:
    if count_active(db) >= get_settings().max_active_jobs:
        raise AppError(429, "too_many_jobs", "진행 중인 작업이 끝난 뒤 다시 시도해 주세요")


def enqueue_or_fail(db: Session, job: Job, enqueue: Callable[[str], None]) -> None:
    # A row left "queued" with no task would block the job cap forever.
    try:
        enqueue(job.id)
    except Exception as exc:
        log.exception("enqueue failed: %s", job.id)
        job.status = "failed"
        job.error_code = "queue_unavailable"
        job.error_message = "작업 큐에 연결하지 못했습니다"
        if hasattr(job, "finished_at"):
            job.finished_at = utcnow()
        db.commit()
        raise AppError(503, "queue_unavailable", "작업 큐에 연결하지 못했습니다") from exc
