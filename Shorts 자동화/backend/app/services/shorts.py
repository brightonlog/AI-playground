from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.ids import new_id
from app.db.models import Analysis, SelectionLog, Short
from app.db.session import SessionLocal
from app.schemas.analysis import ErrorInfo
from app.schemas.short import ShortCreate, ShortOut
from app.services import events, jobs
from app.storage import local
from app.workers import short_tasks
from app.workers.jobs import stage_start

# Statuses where the draft exists and the job is waiting on the user (or finished).
_SETTLED = ("editing", "done")


def progress_of(short: Short) -> float:
    if short.status in _SETTLED:
        return 1.0
    if short.status == "queued":
        return 0.0
    live = events.get_progress("shorts", short.id)
    if live is not None:
        return live
    return round(stage_start(get_settings().short_stage_weights, short.stage), 3)


def to_out(short: Short) -> ShortOut:
    error = None
    if short.error_code:
        error = ErrorInfo(code=short.error_code, message=short.error_message or "")
    return ShortOut(
        id=short.id,
        analysis_id=short.analysis_id,
        template_id=short.template_id,
        status=short.status,  # type: ignore[arg-type]
        stage=short.stage,
        progress=progress_of(short),
        start_sec=short.start_sec,
        end_sec=short.end_sec,
        edit_version=short.edit_version,
        preview_version=short.preview_version,
        preview_status=short.preview_status,
        warnings=short.warnings,
        error=error,
        retry_count=short.retry_count,
        created_at=jobs.utc(short.created_at),  # type: ignore[arg-type]
        exported_at=jobs.utc(short.exported_at),
    )


def _validate(db: Session, body: ShortCreate) -> Analysis:
    s = get_settings()
    analysis = db.get(Analysis, body.analysis_id)
    if analysis is None:
        raise AppError(404, "not_found", "분석을 찾을 수 없습니다")
    if analysis.status != "ready":
        raise AppError(409, "analysis_not_ready", "분석이 끝난 뒤 쇼츠를 만들 수 있습니다")
    if body.template_id not in s.templates_available:
        raise AppError(422, "invalid_template", "사용할 수 없는 템플릿입니다")
    length = body.end_sec - body.start_sec
    if not s.short_min_sec <= length <= s.short_max_sec:
        detail = f"구간은 {s.short_min_sec:g}~{s.short_max_sec:g}초여야 합니다"
        raise AppError(422, "invalid_range", detail)
    if body.end_sec > float(analysis.source.get("duration_sec") or 0):
        raise AppError(422, "invalid_range", "구간이 영상 길이를 넘습니다")
    return analysis


def _log_selection(db: Session, analysis: Analysis, short: Short, rank: int | None) -> None:
    path = local.analysis_dir(analysis.id) / "recommendations.json"
    recs: dict[str, Any] = local.read_json(path) if path.exists() else {}
    recommended = [
        {k: item[k] for k in ("rank", "start_sec", "end_sec", "score", "signals")}
        for item in recs.get("items", [])
    ]
    db.add(
        SelectionLog(
            analysis_id=analysis.id,
            short_id=short.id,
            video_id=analysis.video_id,
            recommended=recommended,
            chosen_start_sec=short.start_sec,
            chosen_end_sec=short.end_sec,
            recommendation_rank=rank,
            scorer_version=recs.get("scorer_version"),
        )
    )


def create_short(db: Session, body: ShortCreate) -> Short:
    analysis = _validate(db, body)
    jobs.check_capacity(db)
    short = Short(
        id=new_id("sh"),
        analysis_id=analysis.id,
        template_id=body.template_id,
        start_sec=round(body.start_sec, 2),
        end_sec=round(body.end_sec, 2),
    )
    db.add(short)
    _log_selection(db, analysis, short, body.recommendation_rank)
    db.commit()
    jobs.enqueue_or_fail(db, short, short_tasks.enqueue)
    return short


def get_or_404(db: Session, short_id: str) -> Short:
    short = db.get(Short, short_id)
    if short is None:
        raise AppError(404, "not_found", "쇼츠를 찾을 수 없습니다")
    return short


def retry_short(db: Session, short_id: str) -> Short:
    short = get_or_404(db, short_id)
    if short.status != "failed":
        raise AppError(409, "invalid_state", "실패한 쇼츠만 다시 시도할 수 있습니다")
    if short.retry_count >= get_settings().max_retries:
        raise AppError(409, "retry_limit", "재시도 횟수를 모두 사용했습니다")
    jobs.check_capacity(db)
    short.status = "queued"
    short.retry_count += 1
    short.error_code = short.error_message = None
    db.commit()
    jobs.enqueue_or_fail(db, short, short_tasks.enqueue)
    return short


def event_snapshot(short_id: str) -> tuple[str, dict[str, Any]]:
    """Current state as an SSE event; payloads match what the worker publishes."""
    with SessionLocal() as db:
        short = get_or_404(db, short_id)
        if short.status in _SETTLED:
            return "done", {"status": short.status}
        if short.status == "failed":
            return "failed", {"error": short.error_code, "detail": short.error_message}
        return "progress", {"stage": short.stage or "queued", "progress": progress_of(short)}
