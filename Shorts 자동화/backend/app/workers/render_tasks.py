"""Preview render (spec 6: 540x960): once at the end of preparing, then after every edit
with a debounce. A render that falls behind a newer edit is cancelled."""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Short
from app.db.session import SessionLocal
from app.media import render
from app.schemas.edit import EditDoc
from app.services import events
from app.storage import local
from app.workers.celery_app import celery_app

log = logging.getLogger(__name__)


def _edit_version(short_id: str) -> int | None:
    with SessionLocal() as db:  # a fresh session sees commits made by the API meanwhile
        return db.scalar(select(Short.edit_version).where(Short.id == short_id))


def render_preview(db: Session, short: Short, on_progress: render.ProgressFn) -> None:
    """Render preview.mp4 for the current edit unless it is already up to date."""
    folder = local.short_dir(short.id)
    if short.preview_status == "ready" and short.preview_version == short.edit_version:
        if (folder / "preview.mp4").exists():
            return
    s = get_settings()
    doc = EditDoc.model_validate(local.read_json(folder / "edit.json"))
    short.preview_status = "rendering"
    db.commit()
    render.render(
        folder, doc, local.read_json(folder / "crop.json"), short.section_offset_sec or 0.0,
        "preview.mp4", s.preview_size, s.preview_crf, on_progress,
        cancelled=lambda: _edit_version(short.id) != doc.version,
    )  # fmt: skip
    db.refresh(short)
    if short.edit_version != doc.version:
        return  # edited during the last moments; the newer task renders it
    short.preview_status = "ready"
    short.preview_version = doc.version
    db.commit()
    events.publish("shorts", short.id, "preview_ready", {"preview_version": doc.version})


@celery_app.task(name="render.preview")
def run_preview(short_id: str) -> None:
    with SessionLocal() as db:
        short = db.get(Short, short_id)
        if short is None or short.status != "editing":
            return
        try:
            render_preview(db, short, lambda f: None)
        except render.RenderCancelled:
            log.info("preview of %s cancelled by a newer edit", short_id)
        except Exception:
            log.exception("preview render failed for %s", short_id)
            db.rollback()
            short.preview_status = "failed"
            db.commit()
            events.publish("shorts", short_id, "preview_failed", {})


def enqueue_preview(short_id: str) -> None:
    # ponytail: debounce by delay only; a burst of edits queues several tasks, and all but the
    # last return early or get cancelled. A per-short pending marker if the queue gets busy.
    run_preview.apply_async((short_id,), countdown=get_settings().preview_debounce_sec)
