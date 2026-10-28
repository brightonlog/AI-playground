from collections.abc import Callable
from typing import Any

from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from app.services import events

SnapshotFn = Callable[[str], tuple[str, dict[str, Any]]]


async def job_events(kind: str, job_id: str, snapshot: SnapshotFn) -> StreamingResponse:
    """SSE for one job. `snapshot` reads current state from the DB (and 404s if missing)."""
    await run_in_threadpool(snapshot, job_id)  # 404 before streaming starts

    async def current() -> tuple[str, dict[str, Any]]:
        return await run_in_threadpool(snapshot, job_id)

    return StreamingResponse(
        events.stream(kind, job_id, current),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
