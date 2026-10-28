"""Short draft stages (spec 2): downloading -> preparing -> editing.

Each step skips when its output file exists, so a retry resumes at the failed step.
"""

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import JobError
from app.db.models import SHORT_ACTIVE_STATUSES, Analysis, Short
from app.db.session import SessionLocal
from app.services import events
from app.sources import youtube
from app.storage import local
from app.workers import jobs
from app.workers.celery_app import celery_app


def _download(db: Session, short: Short, analysis: Analysis, progress: jobs.Progress) -> None:
    section = local.short_dir(short.id) / "section.mp4"
    if section.exists():
        return
    s = get_settings()
    # A margin on both sides leaves room to adjust the cut later without re-downloading.
    start = max(0.0, short.start_sec - s.section_margin_sec)
    end = min(
        float(analysis.source.get("duration_sec") or short.end_sec),
        short.end_sec + s.section_margin_sec,
    )
    youtube.get_source().download_section(
        analysis.url, start, end, section, lambda f: progress.update("downloading", f)
    )
    short.section_offset_sec = round(start, 2)
    db.commit()


def run_short_pipeline(db: Session, short: Short) -> None:
    analysis = db.get(Analysis, short.analysis_id)
    if analysis is None:
        raise JobError("analysis_missing", "원본 분석이 삭제되었습니다")
    progress = jobs.Progress("shorts", short.id, lambda: get_settings().short_stage_weights)

    jobs.enter_stage(db, short, progress, "downloading")
    _download(db, short, analysis, progress)

    jobs.enter_stage(db, short, progress, "preparing")
    # M4-b: section Whisper, crop, title/narration, TTS, edit.json. M4-c: preview render.

    short.status = "editing"
    db.commit()
    progress.update("preparing", 1.0)
    events.publish("shorts", short.id, "done", {"status": "editing"})


@celery_app.task(name="short.run")
def run_short(short_id: str) -> None:
    with SessionLocal() as db:
        short = db.get(Short, short_id)
        # Redelivery after a worker crash resumes; anything else was handled already.
        if short is None or short.status not in SHORT_ACTIVE_STATUSES:
            return
        try:
            run_short_pipeline(db, short)
        except Exception as exc:
            jobs.fail(db, short, "shorts", exc, "쇼츠를 만드는 중 알 수 없는 오류가 발생했습니다")


def enqueue(short_id: str) -> None:
    run_short.delay(short_id)
