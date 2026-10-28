from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, JobError
from app.core.ids import new_id
from app.db.models import ANALYSIS_ACTIVE_STATUSES, Analysis
from app.schemas.analysis import AnalysisOut, ErrorInfo
from app.services import events
from app.sources import youtube
from app.storage import local
from app.workers import analysis_tasks
from app.workers.pipeline import stage_start


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


def create_analysis(db: Session, url: str, template_id: str) -> tuple[Analysis, bool]:
    """Return (analysis, created). An unfailed analysis of the same video is reused."""
    if template_id not in get_settings().templates_available:
        raise AppError(422, "invalid_template", "사용할 수 없는 템플릿입니다")
    video_id = youtube.parse_video_id(url)
    if video_id is None:
        raise AppError(422, "invalid_url", "유튜브 영상 링크가 아닙니다")
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
    analysis_tasks.enqueue(analysis.id)
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
