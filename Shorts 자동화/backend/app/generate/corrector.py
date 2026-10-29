"""Speech-to-text fixes for section words: human captions when they line up, else one LLM
call (no fixes when it fails)."""

import logging
from typing import Any

from pydantic import BaseModel

from app.core.config import get_settings
from app.generate import load_prompt
from app.llm import client as llm
from app.schemas.edit import SpeechLine
from app.transcript.align import align_words

log = logging.getLogger(__name__)


class WordFix(BaseModel):
    word_id: str
    text: str


class WordFixList(BaseModel):
    fixes: list[WordFix]


def _user_message(source: dict[str, Any], products: list[str], lines: list[SpeechLine]) -> str:
    s = get_settings()
    head = [
        f"원본 제목: {source.get('title', '')}",
        f"설명란: {(source.get('description') or '')[: s.llm_description_max_chars]}",
        f"제품: {', '.join(products) or '없음'}",
    ]
    body = [" ".join(f"{w.id}={w.text}" for w in line.words) for line in lines]
    return "\n".join(head) + "\n\n## 음성 인식 결과\n" + "\n".join(body)


def llm_fixes(
    source: dict[str, Any], products: list[str], lines: list[SpeechLine]
) -> dict[str, str]:
    """word id -> corrected text. Empty when the call fails or nothing needs fixing."""
    try:
        result = llm.get_llm().parse(
            load_prompt("correct_words"), _user_message(source, products, lines), WordFixList
        )
    except llm.LLMError as exc:
        log.warning("word correction skipped: %s", exc)
        return {}
    current = {w.id: w.text for line in lines for w in line.words}
    max_chars = get_settings().word_max_chars
    fixes = {}
    for f in result.fixes:
        text = f.text.strip()
        if f.word_id in current and text and len(text) <= max_chars and text != current[f.word_id]:
            fixes[f.word_id] = text
    return fixes


def caption_fixes(lines: list[SpeechLine], captions: list[dict[str, Any]]) -> dict[str, str] | None:
    """Fixes from human captions overlapping the lines, or None when they do not line up."""
    words = [w for line in lines for w in line.words]
    if not words:
        return None
    start, end = words[0].start_sec, words[-1].end_sec
    caption = " ".join(x["text"] for x in captions if x["end_sec"] > start and x["start_sec"] < end)
    aligned = align_words([w.text for w in words], caption)
    if aligned is None:
        return None
    return {w.id: new for w, new in zip(words, aligned, strict=True) if new != w.text}


def apply_fixes(lines: list[SpeechLine], fixes: dict[str, str]) -> None:
    """Replace word text in place, keeping the speech-to-text original in `raw_text`."""
    for line in lines:
        for w in line.words:
            if w.id in fixes:
                w.raw_text = w.raw_text or w.text
                w.text = fixes[w.id]
        line.text = " ".join(w.text for w in line.words)


def correct_lines(
    lines: list[SpeechLine],
    transcript: dict[str, Any],
    source: dict[str, Any],
    products: list[str],
) -> str:
    """Fix speech-to-text errors in place. Human captions first, the LLM otherwise.
    Returns which one was used: "captions" or "llm"."""
    if transcript["source"] == "manual":
        fixes = caption_fixes(lines, transcript["sentences"])
        if fixes is not None:
            apply_fixes(lines, fixes)
            return "captions"
    apply_fixes(lines, llm_fixes(source, products, lines))
    return "llm"
