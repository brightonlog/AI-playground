"""Candidate sections (spec 5.1 steps 2, 3, 6): group mentions, add context, fit 30~60s."""

import re
from dataclasses import dataclass
from typing import Any

from app.core.config import get_settings

Sentences = list[dict[str, Any]]


@dataclass(frozen=True)
class Candidate:
    first: int  # sentence index, inclusive
    last: int
    product_key: str
    start_sec: float  # padded section bounds
    end_sec: float

    @property
    def duration_sec(self) -> float:
        return self.end_sec - self.start_sec


def product_key(product: str) -> str:
    return re.sub(r"\s+", "", product).lower()


def _span(sentences: Sentences, first: int, last: int) -> float:
    return float(sentences[last]["end_sec"] - sentences[first]["start_sec"])


def _group(products_by_idx: dict[int, str]) -> list[tuple[int, int, str]]:
    """Runs of one product; up to N product-less sentences may sit in between."""
    max_gap = get_settings().candidate_max_gap_sentences
    groups: list[tuple[int, int, str]] = []
    for idx in sorted(products_by_idx):
        key = products_by_idx[idx]
        # Sorted iteration: a different product in between would already have closed the run.
        if groups and groups[-1][2] == key and idx - groups[-1][1] - 1 <= max_gap:
            groups[-1] = (groups[-1][0], idx, key)
        else:
            groups.append((idx, idx, key))
    return groups


def _split(sentences: Sentences, first: int, last: int, hi: float) -> list[tuple[int, int]]:
    """Cut at sentence boundaries into chunks no longer than `hi`."""
    chunks = []
    start = first
    while start <= last:
        end = start
        while end < last and _span(sentences, start, end + 1) <= hi:
            end += 1
        chunks.append((start, end))
        start = end + 1
    return chunks


def _expand(sentences: Sentences, first: int, last: int, lo: float, hi: float) -> tuple[int, int]:
    """Grow to at least `lo`, preferring following sentences, never past `hi`."""
    while _span(sentences, first, last) < lo:
        if last + 1 < len(sentences) and _span(sentences, first, last + 1) <= hi:
            last += 1
        elif first > 0 and _span(sentences, first - 1, last) <= hi:
            first -= 1
        else:
            break
    return first, last


def build_candidates(
    sentences: Sentences, products_by_idx: dict[int, str], duration_sec: float
) -> list[Candidate]:
    s = get_settings()
    pad, ctx = s.candidate_pad_sec, s.candidate_context_sentences
    lo, hi = s.candidate_min_sec, s.candidate_max_sec - 2 * pad  # padding must fit too
    seen: set[tuple[int, int]] = set()
    candidates = []
    for g_first, g_last, key in _group(products_by_idx):
        first, last = max(0, g_first - ctx), min(len(sentences) - 1, g_last + ctx)
        for c_first, c_last in _split(sentences, first, last, hi):
            c_first, c_last = _expand(sentences, c_first, c_last, lo, hi)
            if (c_first, c_last) in seen or not lo <= _span(sentences, c_first, c_last) <= hi:
                continue
            seen.add((c_first, c_last))
            start = max(0.0, sentences[c_first]["start_sec"] - pad)
            end = min(duration_sec, sentences[c_last]["end_sec"] + pad)
            candidates.append(Candidate(c_first, c_last, key, round(start, 2), round(end, 2)))
    return candidates
