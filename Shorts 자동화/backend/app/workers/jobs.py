"""Shared worker helpers for analysis and short jobs: progress and failure handling."""

import logging
from collections.abc import Callable
from typing import Protocol

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import JobError
from app.db.models import utcnow
from app.services import events

log = logging.getLogger(__name__)

Weights = dict[str, float]


class Job(Protocol):
    id: str
    status: str
    stage: str | None
    error_code: str | None
    error_message: str | None


def stage_start(weights: Weights, stage: str | None) -> float:
    """Overall progress at the start of `stage` (sum of earlier stage weights)."""
    done = 0.0
    for name, weight in weights.items():
        if name == stage:
            break
        done += weight
    return done


class Progress:
    """Publishes overall 0~1 progress. `weights` is read on each update (it can change mid-run)."""

    def __init__(self, kind: str, job_id: str, weights: Callable[[], Weights]) -> None:
        self.kind, self.job_id, self.weights = kind, job_id, weights
        self.last = -1.0

    def update(self, stage: str, fraction: float) -> None:
        weights = self.weights()
        # float(): Whisper times are numpy floats, whose str() is "np.float64(...)" in Redis.
        overall = float(stage_start(weights, stage) + weights.get(stage, 0.0) * fraction)
        if overall - self.last >= get_settings().progress_min_step or fraction >= 1:
            self.last = overall
            events.set_progress(self.kind, self.job_id, stage, overall)


def enter_stage(db: Session, job: Job, progress: Progress, stage: str) -> None:
    job.status = job.stage = stage
    db.commit()
    progress.update(stage, 0.0)


def fail(db: Session, job: Job, kind: str, exc: Exception, unknown_message: str) -> None:
    db.rollback()
    if isinstance(exc, JobError):
        code, message = exc.code, exc.detail
    else:
        log.exception("%s %s failed", kind, job.id)
        code, message = "internal_error", unknown_message
    job.status = "failed"
    job.error_code, job.error_message = code, message
    if hasattr(job, "finished_at"):
        job.finished_at = utcnow()
    db.commit()
    events.publish(kind, job.id, "failed", {"error": code, "detail": message})
