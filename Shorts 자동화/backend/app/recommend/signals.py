"""Per-candidate signals (spec 5.2). All values are 0~1 and saved as training features."""

from typing import Any

from app.core.config import get_settings
from app.recommend.candidates import Candidate, Sentences, product_key


def length_fit(duration: float) -> float:
    s = get_settings()
    full_lo, full_hi = s.length_fit_full
    edge = s.length_fit_edge_score
    if full_lo <= duration <= full_hi:
        return 1.0
    if s.candidate_min_sec <= duration < full_lo:
        return edge + (1 - edge) * (duration - s.candidate_min_sec) / (
            full_lo - s.candidate_min_sec
        )
    if full_hi < duration <= s.candidate_max_sec:
        return edge + (1 - edge) * (s.candidate_max_sec - duration) / (
            s.candidate_max_sec - full_hi
        )
    return 0.0


def compute_signals(
    c: Candidate, sentences: Sentences, mentions_by_idx: dict[int, dict[str, Any]]
) -> dict[str, float]:
    s = get_settings()
    span = sentences[c.first : c.last + 1]
    mentions = [mentions_by_idx[i] for i in range(c.first, c.last + 1) if i in mentions_by_idx]
    main = [m for m in mentions if product_key(m["product"]) == c.product_key]
    if any(m["brand"] for m in main):
        product_specific = s.product_specific_with_brand
    else:
        product_specific = s.product_specific_product_only if main else 0.0

    duration = c.duration_sec
    chars = sum(len(x["text"].replace(" ", "")) for x in span)
    gaps = sum(
        1
        for a, b in zip(span, span[1:], strict=False)
        if b["start_sec"] - a["end_sec"] > s.continuity_gap_sec
    )
    continuity = max(0.0, 1 - gaps / len(span))
    if len({product_key(m["product"]) for m in mentions}) >= 2:
        continuity *= s.continuity_mixed_products_factor

    signals = {
        "product_specific": product_specific,
        "recommend_strength": max((m["recommend_strength"] for m in mentions), default=0.0),
        "usage": min(1.0, sum(m["usage"] for m in mentions) / len(span) * s.usage_ratio_scale),
        "density": min(1.0, chars / duration / s.density_full_chars_per_sec) if duration else 0.0,
        "continuity": continuity,
        "length_fit": length_fit(duration),
    }
    return {k: round(v, 3) for k, v in signals.items()}
