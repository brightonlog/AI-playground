from typing import Literal

from fastapi import APIRouter
from fastapi.responses import FileResponse, StreamingResponse

from app.api.sse import job_events
from app.db.session import DbSession
from app.schemas.short import ShortCreate, ShortOut
from app.services import shorts

router = APIRouter(prefix="/shorts", tags=["shorts"])


@router.post("", status_code=202)
def create_short(body: ShortCreate, db: DbSession) -> ShortOut:
    return shorts.to_out(shorts.create_short(db, body))


@router.get("/{short_id}")
def get_short(short_id: str, db: DbSession) -> ShortOut:
    return shorts.to_out(shorts.get_or_404(db, short_id))


@router.post("/{short_id}/retry", status_code=202)
def retry_short(short_id: str, db: DbSession) -> ShortOut:
    return shorts.to_out(shorts.retry_short(db, short_id))


@router.get("/{short_id}/events")
async def short_events(short_id: str) -> StreamingResponse:
    return await job_events("shorts", short_id, shorts.event_snapshot)


@router.get("/{short_id}/files/{kind}", response_class=FileResponse)
def get_file(
    short_id: str,
    kind: Literal["preview", "video", "srt", "thumbnail"],
    db: DbSession,
    download: bool = False,
) -> FileResponse:
    """Range requests are supported (video seeking)."""
    path, media_type = shorts.file_of(db, short_id, kind)
    return FileResponse(
        path,
        media_type=media_type,
        filename=f"{short_id}_{path.name}",
        content_disposition_type="attachment" if download else "inline",
    )
