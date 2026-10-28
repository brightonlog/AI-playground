from app.db.models import ANALYSIS_ACTIVE_STATUSES, Analysis
from app.db.session import SessionLocal
from app.workers import jobs
from app.workers.celery_app import celery_app
from app.workers.pipeline import run_pipeline


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
            jobs.fail(db, analysis, "analyses", exc, "분석 중 알 수 없는 오류가 발생했습니다")


def enqueue(analysis_id: str) -> None:
    run_analysis.delay(analysis_id)
