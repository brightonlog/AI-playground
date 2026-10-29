"""Preview render (spec 6: 540x960). M5 adds the debounced re-render after edits."""

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Short
from app.media import render
from app.schemas.edit import EditDoc
from app.services import events
from app.storage import local


def render_preview(db: Session, short: Short, on_progress: render.ProgressFn) -> None:
    """Render preview.mp4 for the current edit unless it is already up to date."""
    folder = local.short_dir(short.id)
    if short.preview_status == "ready" and short.preview_version == short.edit_version:
        if (folder / "preview.mp4").exists():
            return
    s = get_settings()
    short.preview_status = "rendering"
    db.commit()
    doc = EditDoc.model_validate(local.read_json(folder / "edit.json"))
    crop = local.read_json(folder / "crop.json")
    offset = short.section_offset_sec or 0.0
    render.render(folder, doc, crop, offset, "preview.mp4", s.preview_size, s.preview_crf,
                  on_progress)  # fmt: skip
    short.preview_status = "ready"
    short.preview_version = doc.version
    db.commit()
    events.publish("shorts", short.id, "preview_ready", {"preview_version": doc.version})
