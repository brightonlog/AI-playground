import logging
import threading
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, JobError
from app.core.ids import new_id
from app.db.models import ANALYSIS_ACTIVE_STATUSES, Analysis, utcnow
from app.db.session import SessionLocal
from app.schemas.analysis import AnalysisOut, ErrorInfo
from app.services import events
from app.sources import youtube
from app.storage import local
from app.workers import analysis_tasks
from app.workers.pipeline import stage_start

log = logging.getLogger(__name__)
_create_lock = threading.Lock()


def _utc(value: datetime | None) -> datetime | None:
    return value.replace(tzinfo=UTC) if value else None


def progress_of(analysis: Analysis) -> float:
    if analysis.status == "ready":
        return 1.0
    if analysis.status == "queued":
        return 0.0
    live = events.get_progress("analyses", analysis.id)
    if live is not None:
        return live
    return round(stage_start(analysis.progress_weight_mode, analysis.stage), 3)


def to_out(analysis: Analysis) -> AnalysisOut:
    error = None
    if analysis.error_code:
        error = ErrorInfo(code=analysis.error_code, message=analysis.error_message or "")
    return AnalysisOut(
        id=analysis.id,
        video_id=analysis.video_id,
        url=analysis.url,
        template_id=analysis.template_id,
        status=analysis.status,  # type: ignore[arg-type]
        stage=analysis.stage,
        progress=progress_of(analysis),
        transcript_source=analysis.transcript_source,
        warnings=analysis.warnings,
        error=error,
        retry_count=analysis.retry_count,
        source=analysis.source,
        created_at=_utc(analysis.created_at),  # type: ignore[arg-type]
        finished_at=_utc(analysis.finished_at),
    )


def count_active(db: Session) -> int:
    return db.scalar(select(func.count()).where(Analysis.status.in_(ANALYSIS_ACTIVE_STATUSES))) or 0


def _fetch_info(video_id: str) -> youtube.VideoInfo:
    try:
        info = youtube.get_source().get_info(youtube.canonical_url(video_id))
    except JobError as exc:
        raise AppError(422, exc.code, exc.detail) from exc
    limit = get_settings().max_source_sec
    if info.duration_sec > limit:
        raise AppError(422, "video_too_long", f"{limit // 60}분이 넘는 영상은 지원하지 않습니다")
    return info


def _enqueue_or_fail(db: Session, analysis: Analysis) -> None:
    # A row left "queued" with no task would block the job cap and dedupe forever.
    try:
        analysis_tasks.enqueue(analysis.id)
    except Exception as exc:
        log.exception("enqueue failed: %s", analysis.id)
        analysis.status = "failed"
        analysis.error_code = "queue_unavailable"
        analysis.error_message = "작업 큐에 연결하지 못했습니다"
        analysis.finished_at = utcnow()
        db.commit()
        raise AppError(503, "queue_unavailable", "작업 큐에 연결하지 못했습니다") from exc


def create_analysis(db: Session, url: str, template_id: str) -> tuple[Analysis, bool]:
    """Return (analysis, created). An unfailed analysis of the same video is reused."""
    if template_id not in get_settings().templates_available:
        raise AppError(422, "invalid_template", "사용할 수 없는 템플릿입니다")
    video_id = youtube.parse_video_id(url)
    if video_id is None:
        raise AppError(422, "invalid_url", "유튜브 영상 링크가 아닙니다")
    # ponytail: in-process lock (one API process); needs a DB-level guard if that changes.
    with _create_lock:
        return _create_locked(db, video_id, template_id)


def _create_locked(db: Session, video_id: str, template_id: str) -> tuple[Analysis, bool]:
    existing = db.scalar(
        select(Analysis)
        .where(Analysis.video_id == video_id, Analysis.template_id == template_id)
        .where(Analysis.status != "failed")
        .order_by(Analysis.created_at.desc())
    )
    if existing:
        return existing, False
    if count_active(db) >= get_settings().max_active_jobs:
        raise AppError(429, "too_many_jobs", "진행 중인 작업이 끝난 뒤 다시 시도해 주세요")

    info = _fetch_info(video_id)
    analysis = Analysis(
        id=new_id("an"),
        video_id=video_id,
        url=youtube.canonical_url(video_id),
        template_id=template_id,
        source={
            "title": info.title,
            "channel": info.channel,
            "duration_sec": info.duration_sec,
            "thumbnail_url": info.thumbnail_url,
        },
    )
    local.write_json(local.analysis_dir(analysis.id) / "meta.json", asdict(info))
    db.add(analysis)
    db.commit()
    _enqueue_or_fail(db, analysis)
    return analysis, True


def get_or_404(db: Session, analysis_id: str) -> Analysis:
    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        raise AppError(404, "not_found", "분석을 찾을 수 없습니다")
    return analysis


def list_analyses(
    db: Session, status: str | None, limit: int, cursor: str | None
) -> tuple[list[Analysis], str | None]:
    query = select(Analysis).order_by(Analysis.created_at.desc(), Analysis.id.desc())
    if status:
        query = query.where(Analysis.status == status)
    if cursor:
        last = db.get(Analysis, cursor)
        if last is None:
            raise AppError(422, "invalid_cursor", "잘못된 cursor 값입니다")
        query = query.where(
            or_(
                Analysis.created_at < last.created_at,
                and_(Analysis.created_at == last.created_at, Analysis.id < last.id),
            )
        )
    rows = list(db.scalars(query.limit(limit + 1)))
    next_cursor = rows[limit - 1].id if len(rows) > limit else None
    return rows[:limit], next_cursor


def delete_analysis(db: Session, analysis_id: str) -> None:
    analysis = get_or_404(db, analysis_id)
    if analysis.status in ANALYSIS_ACTIVE_STATUSES:
        raise AppError(409, "analysis_running", "진행 중인 분석은 삭제할 수 없습니다")
    db.delete(analysis)
    db.commit()
    local.remove_analysis_dir(analysis_id)


def read_artifact(db: Session, analysis_id: str, name: str, not_ready_code: str) -> Any:
    analysis = get_or_404(db, analysis_id)
    path = local.analysis_dir(analysis.id) / name
    if not path.exists():
        raise AppError(409, not_ready_code, "아직 준비되지 않았습니다")
    return local.read_json(path)


def event_snapshot(analysis_id: str) -> tuple[str, dict[str, Any]]:
    """Current state as an SSE event; payloads match what the worker publishes."""
    with SessionLocal() as db:
        analysis = get_or_404(db, analysis_id)
        if analysis.status == "ready":
            return "done", {"status": "ready"}
        if analysis.status == "failed":
            return "failed", {"error": analysis.error_code, "detail": analysis.error_message}
        return "progress", {"stage": analysis.stage or "queued", "progress": progress_of(analysis)}


def retry_analysis(db: Session, analysis_id: str) -> Analysis:
    analysis = get_or_404(db, analysis_id)
    if analysis.status != "failed":
        raise AppError(409, "invalid_state", "실패한 분석만 다시 시도할 수 있습니다")
    if analysis.retry_count >= get_settings().max_retries:
        raise AppError(409, "retry_limit", "재시도 횟수를 모두 사용했습니다")
    if count_active(db) >= get_settings().max_active_jobs:
        raise AppError(429, "too_many_jobs", "진행 중인 작업이 끝난 뒤 다시 시도해 주세요")
    # Stage stays: the pipeline skips finished outputs, so it resumes at the failed stage.
    analysis.status = "queued"
    analysis.retry_count += 1
    analysis.error_code = analysis.error_message = None
    analysis.finished_at = None
    db.commit()
    _enqueue_or_fail(db, analysis)
    return analysis
