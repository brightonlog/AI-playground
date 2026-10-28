from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery("shorts", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(task_acks_late=True, worker_prefetch_multiplier=1)


@celery_app.task(name="ping")
def ping() -> str:
    return "pong"
