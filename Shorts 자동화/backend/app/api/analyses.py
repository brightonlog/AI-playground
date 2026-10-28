from typing import Annotated, Any

from fastapi import APIRouter, Query, Response
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.db.session import DbSession
from app.schemas.analysis import (
    AnalysisCreate,
    AnalysisList,
    AnalysisOut,
    AnalysisStatus,
    TranscriptOut,
    WaveformOut,
)
from app.services import analyses, events

router = APIRouter(prefix="/analyses", tags=["analyses"])
_settings = get_settings()


@router.post("", status_code=202)
def create_analysis(body: AnalysisCreate, response: Response, db: DbSession) -> AnalysisOut:
    analysis, created = analyses.create_analysis(db, body.url, body.template_id)
    if not created:
        response.status_code = 200
    return analyses.to_out(analysis)


@router.get("")
def list_analyses(
    db: DbSession,
    status: AnalysisStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=_settings.list_max_limit)] = _settings.list_default_limit,
    cursor: str | None = None,
) -> AnalysisList:
    rows, next_cursor = analyses.list_analyses(db, status, limit, cursor)
    return AnalysisList(items=[analyses.to_out(a) for a in rows], next_cursor=next_cursor)


@router.get("/{analysis_id}")
def get_analysis(analysis_id: str, db: DbSession) -> AnalysisOut:
    return analyses.to_out(analyses.get_or_404(db, analysis_id))


@router.delete("/{analysis_id}", status_code=204)
def delete_analysis(analysis_id: str, db: DbSession) -> None:
    analyses.delete_analysis(db, analysis_id)


@router.get("/{analysis_id}/transcript")
def get_transcript(
    analysis_id: str,
    db: DbSession,
    start_sec: Annotated[float | None, Query(ge=0)] = None,
    end_sec: Annotated[float | None, Query(ge=0)] = None,
) -> TranscriptOut:
    data: dict[str, Any] = analyses.read_artifact(
        db, analysis_id, "transcript.json", "transcript_not_ready"
    )
    sentences = [
        s
        for s in data["sentences"]
        if (end_sec is None or s["start_sec"] < end_sec)
        and (start_sec is None or s["end_sec"] > start_sec)
    ]
    return TranscriptOut(source=data["source"], sentences=sentences)


@router.get("/{analysis_id}/waveform")
def get_waveform(analysis_id: str, db: DbSession) -> WaveformOut:
    data = analyses.read_artifact(db, analysis_id, "waveform.json", "waveform_not_ready")
    return WaveformOut(**data)


@router.post("/{analysis_id}/retry", status_code=202)
def retry_analysis(analysis_id: str, db: DbSession) -> AnalysisOut:
    return analyses.to_out(analyses.retry_analysis(db, analysis_id))


@router.get("/{analysis_id}/events")
async def analysis_events(analysis_id: str) -> StreamingResponse:
    await run_in_threadpool(analyses.event_snapshot, analysis_id)  # 404 before streaming starts

    async def snapshot() -> tuple[str, dict[str, Any]]:
        return await run_in_threadpool(analyses.event_snapshot, analysis_id)

    return StreamingResponse(
        events.stream("analyses", analysis_id, snapshot),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
