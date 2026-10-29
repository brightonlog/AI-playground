"""Short preparing: words -> crop -> fixes, title, narration, TTS -> edit.json -> preview.

Each step skips when its output file exists, so a retry resumes at the failed step.
"""

import logging
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import JobError
from app.db.models import Analysis, Short
from app.generate import copywriter, corrector, tts
from app.media import crop
from app.media.probe import duration_sec, video_size
from app.schemas.edit import EditDoc, NarrationLine, SpeechLine, Style, Title, Word
from app.storage import local
from app.transcript import whisper
from app.transcript.sentences import Token, group_tokens, join_text
from app.workers import jobs, render_tasks

log = logging.getLogger(__name__)


def _warn(short: Short, code: str) -> None:
    if code not in short.warnings:
        short.warnings = [*short.warnings, code]


def build_lines(words: list[dict[str, Any]], start: float, end: float) -> list[SpeechLine]:
    """Speech lines from words whose middle falls inside the chosen range."""
    tokens = [
        Token(w["text"], w["start_sec"], w["end_sec"])
        for w in words
        if start <= (w["start_sec"] + w["end_sec"]) / 2 <= end
    ]
    lines: list[SpeechLine] = []
    count = 0
    for group in group_tokens(tokens):
        if not (text := join_text(group)):
            continue
        items = []
        for t in group:
            if t.text.strip():
                count += 1
                items.append(Word(id=f"w{count}", text=t.text.strip(),
                                  start_sec=t.start, end_sec=t.end))  # fmt: skip
        lines.append(SpeechLine(id=f"l{len(lines) + 1}", text=text, words=items))
    return lines


def _words(
    short: Short, folder: Path, products: list[str], on_progress: whisper.ProgressFn
) -> list[dict[str, Any]]:
    path = folder / "words.json"
    if not path.exists():
        offset = short.section_offset_sec or 0.0
        hints = " ".join(products)[: get_settings().whisper_hint_max_chars]
        tokens = whisper.get_transcriber().transcribe(
            folder / "section.mp4", on_progress, words=True, hints=hints
        )
        words = [
            {"text": t.text, "start_sec": round(offset + t.start, 2),
             "end_sec": round(offset + t.end, 2)}
            for t in tokens
        ]  # fmt: skip
        local.write_json(path, {"source": "whisper", "words": words})
    return local.read_json(path)["words"]  # type: ignore[no-any-return]


def _crop(db: Session, short: Short, folder: Path, on_progress: crop.ProgressFn) -> None:
    path = folder / "crop.json"
    if path.exists():
        return
    section = folder / "section.mp4"
    try:
        centers = crop.get_face_finder().centers(section, on_progress)
    except Exception:
        # A centered crop still makes a usable draft; the user can see the warning.
        log.exception("face detection failed for %s", short.id)
        centers = []
        _warn(short, "crop_fallback")
        db.commit()
    width, height = video_size(section)
    local.write_json(path, crop.build_crop(centers, width, height, short.section_offset_sec or 0.0))


def _products(analysis: Analysis, start: float, end: float) -> list[str]:
    folder = local.analysis_dir(analysis.id)
    sentences = local.read_json(folder / "transcript.json")["sentences"]
    inside = {x["id"] for x in sentences if x["end_sec"] > start and x["start_sec"] < end}
    names: list[str] = []
    for m in local.read_json(folder / "mentions.json")["mentions"]:
        name = " ".join(filter(None, [m["brand"], m["product"]]))
        if m["sentence_id"] in inside and name not in names:
            names.append(name)
    return names


def _narrations(folder: Path, copy: dict[str, Any]) -> list[NarrationLine]:
    out = []
    for i, n in enumerate(copy["narrations"], start=1):
        audio_path = f"narration/n{i}.mp3"
        tts.speak(n["text"], "default", folder / audio_path)
        out.append(NarrationLine(id=f"n{i}", text=n["text"], anchor_line_id=n["anchor_line_id"],
                                 audio_path=audio_path,
                                 audio_sec=duration_sec(folder / audio_path)))  # fmt: skip
    return out


def _edit(
    db: Session, short: Short, analysis: Analysis, folder: Path, words: list, products: list[str]
) -> None:
    path = folder / "edit.json"
    if path.exists():
        return
    lines = build_lines(words, short.start_sec, short.end_sec)
    if not lines:
        raise JobError(
            "no_speech", "선택한 구간에서 대사를 찾지 못했습니다. 다른 구간을 골라 주세요"
        )
    transcript = local.read_json(local.analysis_dir(analysis.id) / "transcript.json")
    used = corrector.correct_lines(lines, transcript, analysis.source, products)
    log.info("speech-to-text corrected with %s for %s", used, short.id)
    texts = [{"id": x.id, "text": x.text} for x in lines]
    copy = copywriter.draft_copy(analysis.source, products, texts)
    if copy is None:
        copy = copywriter.fallback_copy(analysis.source)
        _warn(short, "llm_fallback")
    by_anchor = {n.anchor_line_id: n for n in _narrations(folder, copy)}
    ordered: list[SpeechLine | NarrationLine] = []
    for line in lines:  # a narration sits right before the line it plays over
        if line.id in by_anchor:
            ordered.append(by_anchor[line.id])
        ordered.append(line)
    doc = EditDoc(
        title=Title(text=copy["title"]),
        lines=ordered,
        style=Style(preset_id=get_settings().default_style_preset),
    )
    local.write_json(path, doc.model_dump())
    short.edit_version = doc.version
    db.commit()


def prepare(db: Session, short: Short, analysis: Analysis, progress: jobs.Progress) -> None:
    shares = get_settings().prepare_shares
    crop_from = shares["words"]
    copy_from = crop_from + shares["crop"]
    preview_from = copy_from + shares["copy"]

    def scaled(base: float, share: float) -> whisper.ProgressFn:
        return lambda f: progress.update("preparing", base + share * f)

    folder = local.short_dir(short.id)
    products = _products(analysis, short.start_sec, short.end_sec)
    words = _words(short, folder, products, scaled(0.0, shares["words"]))
    _crop(db, short, folder, scaled(crop_from, shares["crop"]))
    progress.update("preparing", copy_from)
    _edit(db, short, analysis, folder, words, products)
    render_tasks.render_preview(db, short, scaled(preview_from, shares["preview"]))
