"""Cut suggestions (spec 7 POST /cut-suggestions): long pauses and filler words."""

import re

from app.core.config import get_settings
from app.media import timeline
from app.schemas.edit import EditDoc, SilenceRequest, Suggestion, Word

_PUNCT = re.compile(r"[^\w]")


def is_filler(text: str) -> bool:
    s = get_settings()
    bare = _PUNCT.sub("", text)
    return bool(bare) and (set(bare) <= set(s.filler_sounds) or bare in s.filler_words)


def _live_words(doc: EditDoc) -> list[Word]:
    return [w for line in timeline.speech_lines(doc) if not line.deleted
            for w in line.words if not w.deleted]  # fmt: skip


def silence(doc: EditDoc, min_gap_sec: float) -> list[tuple[list[str], str]]:
    """Pauses after a word that the cut keeps, i.e. not already trimmed."""
    words = _live_words(doc)
    out = []
    for w, nxt in zip(words, words[1:], strict=False):
        gap = nxt.start_sec - w.end_sec
        if gap >= min_gap_sec and not w.trim_gap_after:
            out.append(([w.id], f"'{w.text}' 뒤 {gap:.1f}초 쉼"))
    return out


def fillers(doc: EditDoc) -> list[tuple[list[str], str]]:
    """Filler sounds and a word said twice in a row (the first one is suggested)."""
    words = _live_words(doc)
    out = []
    for i, w in enumerate(words):
        nxt = words[i + 1] if i + 1 < len(words) else None
        if is_filler(w.text):
            out.append(([w.id], f"군말 '{w.text}'"))
        elif nxt and _PUNCT.sub("", w.text) and _PUNCT.sub("", w.text) == _PUNCT.sub("", nxt.text):
            out.append(([w.id], f"반복 '{w.text}'"))
    return out


def suggest(doc: EditDoc, request_type: str, found: list[tuple[list[str], str]]) -> EditDoc:
    """A copy of `doc` whose suggestions of this type are replaced by `found`."""
    new = doc.model_copy(deep=True)
    kept = [x for x in new.pending_suggestions if x.type != request_type]
    nums = [int(x.id[1:]) for x in doc.pending_suggestions if x.id[1:].isdigit()]
    start = max(nums, default=0) + 1
    new.pending_suggestions = kept + [
        Suggestion(id=f"s{start + i}", type=request_type, word_ids=ids, reason=reason)
        for i, (ids, reason) in enumerate(found)
    ]
    return new


def find(doc: EditDoc, request: object) -> list[tuple[list[str], str]]:
    if isinstance(request, SilenceRequest):
        return silence(doc, request.min_gap_sec)
    return fillers(doc)
