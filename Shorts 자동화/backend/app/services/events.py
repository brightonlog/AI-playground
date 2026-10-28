"""Job progress and events in Redis. The DB holds status; Redis holds live progress."""

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from functools import lru_cache
from typing import Any, cast

import redis
import redis.asyncio as aioredis

from app.core.config import get_settings

log = logging.getLogger(__name__)


def channel(kind: str, job_id: str) -> str:
    return f"events:{kind}:{job_id}"


def _progress_key(kind: str, job_id: str) -> str:
    return f"progress:{kind}:{job_id}"


@lru_cache
def _client() -> redis.Redis:
    return redis.Redis.from_url(get_settings().redis_url, decode_responses=True)


def publish(kind: str, job_id: str, event: str, data: dict[str, Any]) -> None:
    # A lost progress message must never fail the job itself.
    try:
        _client().publish(channel(kind, job_id), json.dumps({"event": event, "data": data}))
    except redis.RedisError:
        log.warning("event publish failed: %s %s", kind, job_id)


def set_progress(kind: str, job_id: str, stage: str, progress: float) -> None:
    value = round(progress, 3)
    try:
        _client().set(_progress_key(kind, job_id), value, ex=get_settings().progress_ttl_sec)
    except redis.RedisError:
        log.warning("progress store failed: %s %s", kind, job_id)
    publish(kind, job_id, "progress", {"stage": stage, "progress": value})


def get_progress(kind: str, job_id: str) -> float | None:
    try:
        value = cast(str | None, _client().get(_progress_key(kind, job_id)))
    except redis.RedisError:
        return None
    return float(value) if value is not None else None


TERMINAL_EVENTS = ("done", "failed")
Snapshot = Callable[[], Awaitable[tuple[str, dict[str, Any]]]]


def sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def stream(kind: str, job_id: str, snapshot: Snapshot) -> AsyncIterator[str]:
    """SSE stream: current state first, then Redis events until done/failed.

    Quiet periods re-check the DB via `snapshot`, so a missed message (or Redis being
    down entirely) only delays the final event by one heartbeat.
    """
    heartbeat = get_settings().sse_heartbeat_sec
    client = aioredis.Redis.from_url(get_settings().redis_url, decode_responses=True)
    pubsub: Any = client.pubsub()
    try:
        try:
            # Subscribe before reading state so nothing published in between is lost.
            await pubsub.subscribe(channel(kind, job_id))
        except redis.RedisError:
            log.warning("sse without redis, polling: %s %s", kind, job_id)
            pubsub = None
        event, data = await snapshot()
        yield sse(event, data)
        while event not in TERMINAL_EVENTS:
            message = await _next_message(pubsub, heartbeat)
            if message is None:
                # Doubles as the heartbeat, and keeps progress moving when polling.
                event, data = await snapshot()
                yield sse(event, data)
                continue
            payload = json.loads(message["data"])
            event = payload["event"]
            yield sse(event, payload["data"])
    finally:
        if pubsub is not None:
            await pubsub.aclose()
        await client.aclose()


async def _next_message(pubsub: Any, timeout: float) -> dict[str, Any] | None:
    if pubsub is None:
        await asyncio.sleep(timeout)
        return None
    try:
        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=timeout)
    except redis.RedisError:
        await asyncio.sleep(timeout)
        return None
    return cast(dict[str, Any] | None, message)
