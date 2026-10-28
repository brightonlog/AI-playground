import redis

from app.core.config import get_settings


def redis_ok() -> bool:
    timeout = get_settings().health_check_timeout_sec
    client = redis.Redis.from_url(
        get_settings().redis_url, socket_connect_timeout=timeout, socket_timeout=timeout
    )
    try:
        return bool(client.ping())
    except redis.RedisError:
        return False
    finally:
        client.close()
