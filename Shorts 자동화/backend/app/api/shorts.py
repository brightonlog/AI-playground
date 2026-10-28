from fastapi import APIRouter
from fastapi.responses import StreamingResponse

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
