"""Edit state of a short (spec 6, 7: GET/PATCH /shorts/{id}/edit)."""

import logging
import threading
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.models import Short
from app.media import timeline
from app.schemas.edit import (
    CutRequest,
    CutResult,
    EditDoc,
    EditOut,
    EditPatch,
    EditResult,
    NarrationLine,
)
from app.services import cuts
from app.services.edit_ops import Editor, OpError
from app.services.shorts import get_or_404
from app.storage import local
from app.workers import render_tasks

log = logging.getLogger(__name__)

# ponytail: one lock for every short, fine for a single-user tool (per-short locks if not).
_patch_lock = threading.Lock()

_EDITABLE = ("editing", "done")


def _load(short: Short) -> tuple[EditDoc, Path]:
    folder = local.short_dir(short.id)
    path = folder / "edit.json"
    if short.status not in _EDITABLE or not path.exists():
        raise AppError(409, "edit_not_ready", "초안이 준비된 뒤에 편집할 수 있습니다")
    return EditDoc.model_validate(local.read_json(path)), folder


def get_edit(db: Session, short_id: str) -> EditOut:
    doc, _ = _load(get_or_404(db, short_id))
    kept = timeline.kept_words(doc)
    return EditOut(
        edit=doc,
        duration_sec=timeline.duration(kept),
        out_start_sec=kept[0].start if kept else 0.0,
    )


def _remove_unused_audio(doc: EditDoc, folder: Path) -> None:
    used = {x.audio_path for x in doc.lines if isinstance(x, NarrationLine)}
    for path in (folder / "narration").glob("*.mp3"):
        if f"narration/{path.name}" not in used:
            path.unlink(missing_ok=True)


def patch_edit(db: Session, short_id: str, body: EditPatch) -> EditResult:
    with _patch_lock:
        short = get_or_404(db, short_id)
        doc, folder = _load(short)
        if body.base_version != doc.version:
            raise AppError(
                409, "version_conflict", "다른 곳에서 먼저 편집했습니다. 새로 불러와 주세요"
            )
        editor = Editor(doc, folder)
        try:
            for op in body.ops:
                editor.apply(op)
        except OpError as exc:
            raise AppError(422, "invalid_op", str(exc)) from exc
        new = editor.doc
        new.version = doc.version + 1
        duration = timeline.duration(timeline.kept_words(new))
        s = get_settings()
        if not s.output_min_sec <= duration <= s.output_max_sec:
            raise AppError(
                422,
                "invalid_duration",
                f"영상 길이는 {s.output_min_sec:g}~{s.output_max_sec:g}초여야 합니다 "
                f"(지금 {duration:.1f}초)",
            )
        local.write_json(folder / "edit.json", new.model_dump())
        _remove_unused_audio(new, folder)
        short.edit_version = new.version
        short.status = "editing"  # editing after export sends it back (spec 2)
        short.preview_status = "pending"
        db.commit()
    try:
        render_tasks.enqueue_preview(short.id)
    except Exception:  # the edit is saved; only the preview is missing
        log.exception("could not queue preview for %s", short.id)
        short.preview_status = "failed"
        db.commit()
    return EditResult(
        version=new.version, duration_sec=duration, preview_status=short.preview_status
    )


def cut_suggestions(db: Session, short_id: str, request: CutRequest) -> CutResult:
    """Replace pending suggestions of the requested type. The cut itself does not change, so
    an up-to-date preview stays up to date."""
    with _patch_lock:
        short = get_or_404(db, short_id)
        doc, folder = _load(short)
        new = cuts.suggest(doc, request.type, cuts.find(doc, request))
        new.version = doc.version + 1
        local.write_json(folder / "edit.json", new.model_dump())
        if short.preview_status == "ready" and short.preview_version == doc.version:
            short.preview_version = new.version
        short.edit_version = new.version
        db.commit()
    found = [x for x in new.pending_suggestions if x.type == request.type]
    return CutResult(version=new.version, suggestions=found)
