"""Which parts of the source survive the edit, and where they land in the output (spec 6)."""

from dataclasses import dataclass

from app.core.config import get_settings
from app.schemas.edit import EditDoc, SpeechLine, Word


@dataclass
class Kept:
    """One live word: its kept source span and where that span starts in the output."""

    word: Word
    line_id: str
    start: float
    end: float
    out_start: float


def speech_lines(doc: EditDoc) -> list[SpeechLine]:
    return [x for x in doc.lines if isinstance(x, SpeechLine)]


def kept_words(doc: EditDoc) -> list[Kept]:
    """A live word keeps from its start to the next word's start (live or not), so deleting a
    word also drops it. With `trim_gap_after` it stops at its end + trim_gap_sec. The last word
    stops at its end."""
    gap = get_settings().trim_gap_sec
    words = sorted(
        ((w, line) for line in speech_lines(doc) for w in line.words), key=lambda p: p[0].start_sec
    )
    kept: list[Kept] = []
    out = 0.0
    for i, (w, line) in enumerate(words):
        if w.deleted or line.deleted:
            continue
        nxt = words[i + 1][0].start_sec if i + 1 < len(words) else w.end_sec
        end = min(nxt, w.end_sec + gap) if w.trim_gap_after else nxt
        end = round(max(end, w.start_sec), 3)
        kept.append(Kept(w, line.id, w.start_sec, end, round(out, 3)))
        out += end - w.start_sec
    return kept


def segments(kept: list[Kept]) -> list[tuple[float, float]]:
    """Kept source spans, touching spans merged."""
    spans: list[tuple[float, float]] = []
    for k in kept:
        if spans and abs(spans[-1][1] - k.start) < 1e-6:
            spans[-1] = (spans[-1][0], k.end)
        else:
            spans.append((k.start, k.end))
    return spans


def duration(kept: list[Kept]) -> float:
    return round(sum(k.end - k.start for k in kept), 2)
