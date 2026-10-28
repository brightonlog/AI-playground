"""Job progress and events in Redis. The DB holds status; Redis holds live progress."""

import json
import logging
from functools import lru_cache
from typing import Any, cast

import redis

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
