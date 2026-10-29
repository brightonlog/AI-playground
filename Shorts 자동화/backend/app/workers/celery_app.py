from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery("shorts", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    include=["app.workers.analysis_tasks", "app.workers.short_tasks", "app.workers.render_tasks"],
    # Longer than the slowest job, or Redis redelivers a task that is still running.
    broker_transport_options={"visibility_timeout": settings.task_visibility_timeout_sec},
)


@celery_app.task(name="ping")
def ping() -> str:
    return "pong"
