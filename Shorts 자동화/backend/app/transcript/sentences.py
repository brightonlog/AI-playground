"""Caption/ASR tokens -> sentences with source-video timestamps."""

import re
from dataclasses import dataclass
from typing import Any

from app.core.config import Settings, get_settings

_TAG_RE = re.compile(r"\[[^\]]*\]")  # [음악], [박수]
_TERMINALS = (".", "?", "!", "…", "。")
# ponytail: naive Korean ending heuristic for unpunctuated auto captions ("바다" also matches).
_KO_ENDINGS = ("다", "요", "죠", "까")


@dataclass
class Token:
    text: str
    start: float
    end: float


def tokens_from_json3(data: dict[str, Any]) -> list[Token]:
    tokens: list[Token] = []
    for event in data.get("events", []):
        segs = event.get("segs") or []
        start = event.get("tStartMs", 0) / 1000
        end = start + event.get("dDurationMs", 0) / 1000
        starts = [start + seg.get("tOffsetMs", 0) / 1000 for seg in segs]
        for i, seg in enumerate(segs):
            text = _TAG_RE.sub("", seg.get("utf8", "")).replace("\n", " ")
            if not text.strip():
                continue
            if i == 0:
                text = " " + text  # events are separate lines; keep a word break between them
            tokens.append(Token(text, starts[i], starts[i + 1] if i + 1 < len(segs) else end))
    tokens.sort(key=lambda t: t.start)
    # Auto captions overlap: each window runs past the next one's start. Clip to it.
    for cur, nxt in zip(tokens, tokens[1:], strict=False):
        cur.end = max(cur.start, min(cur.end, nxt.start))
    return tokens


def _is_boundary(group: list[Token], nxt: Token, s: Settings) -> bool:
    last = group[-1]
    length = last.end - group[0].start
    if nxt.start - last.end >= s.sentence_gap_sec or length >= s.sentence_max_sec:
        return True
    text = last.text.strip()
    if text.endswith(_TERMINALS):
        return True
    return text.endswith(_KO_ENDINGS) and length >= s.sentence_min_sec


def join_text(tokens: list[Token]) -> str:
    return re.sub(r"\s+", " ", "".join(t.text for t in tokens)).strip()


def group_tokens(tokens: list[Token]) -> list[list[Token]]:
    s = get_settings()
    groups: list[list[Token]] = []
    group: list[Token] = []
    for i, token in enumerate(tokens):
        group.append(token)
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None
        if nxt is None or _is_boundary(group, nxt, s):
            groups.append(group)
            group = []
    return groups


def group_sentences(tokens: list[Token]) -> list[dict[str, Any]]:
    sentences: list[dict[str, Any]] = []
    for group in group_tokens(tokens):
        if text := join_text(group):
            sentences.append(
                {
                    "id": f"s{len(sentences) + 1}",
                    "start_sec": round(group[0].start, 2),
                    "end_sec": round(group[-1].end, 2),
                    "text": text,
                }
            )
    return sentences
