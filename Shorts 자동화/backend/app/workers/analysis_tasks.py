import logging

from sqlalchemy.orm import Session

from app.core.errors import JobError
from app.db.models import ANALYSIS_ACTIVE_STATUSES, Analysis, utcnow
from app.db.session import SessionLocal
from app.services import events
from app.workers.celery_app import celery_app
from app.workers.pipeline import run_pipeline

log = logging.getLogger(__name__)


def _fail(db: Session, analysis: Analysis, exc: Exception) -> None:
    db.rollback()
    if isinstance(exc, JobError):
        code, message = exc.code, exc.detail
    else:
        log.exception("analysis %s failed", analysis.id)
        code, message = "internal_error", "분석 중 알 수 없는 오류가 발생했습니다"
    analysis.status = "failed"
    analysis.error_code, analysis.error_message = code, message
    analysis.finished_at = utcnow()
    db.commit()
    events.publish("analyses", analysis.id, "failed", {"error": code, "detail": message})


@celery_app.task(name="analysis.run")
def run_analysis(analysis_id: str) -> None:
    with SessionLocal() as db:
        analysis = db.get(Analysis, analysis_id)
        # A non-queued active status means a redelivery after a worker crash (acks_late).
        # Steps skip finished outputs, so running again resumes where it stopped.
        if analysis is None or analysis.status not in ANALYSIS_ACTIVE_STATUSES:
            return
        try:
            run_pipeline(db, analysis)
        except Exception as exc:
            _fail(db, analysis, exc)


def enqueue(analysis_id: str) -> None:
    run_analysis.delay(analysis_id)
