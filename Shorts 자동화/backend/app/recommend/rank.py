"""Mentions -> candidates -> signals -> scores -> top sections (spec 5.1)."""

from typing import Any

from app.core.config import get_settings
from app.recommend.candidates import Candidate, Sentences, build_candidates, product_key
from app.recommend.scorer import get_scorer
from app.recommend.signals import compute_signals
from app.recommend.tags import make_tags


def iou(a: Candidate, b: Candidate) -> float:
    inter = min(a.end_sec, b.end_sec) - max(a.start_sec, b.start_sec)
    if inter <= 0:
        return 0.0
    return inter / (a.duration_sec + b.duration_sec - inter)


def _pick(candidates: list[Candidate], scores: list[float]) -> list[int]:
    s = get_settings()
    picked: list[int] = []
    for i in sorted(range(len(candidates)), key=lambda i: scores[i], reverse=True):
        if all(iou(candidates[i], candidates[p]) <= s.overlap_iou_max for p in picked):
            picked.append(i)
        if len(picked) == s.recommend_top_k:
            break
    return picked


def _item(
    rank: int, c: Candidate, score: float, signals: dict[str, float],
    sentences: Sentences, mentions_by_idx: dict[int, dict[str, Any]],
) -> dict[str, Any]:  # fmt: skip
    mentions = [mentions_by_idx[i] for i in range(c.first, c.last + 1) if i in mentions_by_idx]
    mentions.sort(key=lambda m: product_key(m["product"]) != c.product_key)  # main product first
    products: list[dict[str, Any]] = []
    for m in mentions:
        if all(product_key(p["product"]) != product_key(m["product"]) for p in products):
            products.append({k: m[k] for k in ("product", "brand", "category")})
    tags = make_tags(signals, products[0]["brand"] if products else None)
    return {
        "rank": rank,
        "start_sec": c.start_sec,
        "end_sec": c.end_sec,
        "duration_sec": round(c.duration_sec, 2),
        "score": score,
        "signals": signals,
        "tags": [code for code, _ in tags],
        "tag_labels": [label for _, label in tags],
        "products": products,
        "preview": sentences[c.first]["text"],
    }


def recommend(
    sentences: Sentences, mentions: list[dict[str, Any]], duration_sec: float
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (signals.json, recommendations.json) contents."""
    index = {x["id"]: i for i, x in enumerate(sentences)}
    mentions_by_idx = {index[m["sentence_id"]]: m for m in mentions if m["sentence_id"] in index}
    products_by_idx = {i: product_key(m["product"]) for i, m in mentions_by_idx.items()}

    candidates = build_candidates(sentences, products_by_idx, duration_sec)
    signals = [compute_signals(c, sentences, mentions_by_idx) for c in candidates]
    scorer = get_scorer()
    scores = scorer.score(candidates, signals)
    picked = _pick(candidates, scores)

    rank_of = {i: r + 1 for r, i in enumerate(picked)}
    signals_doc = {
        "scorer_version": scorer.version,
        "candidates": [
            {"id": f"c{i + 1}", "start_sec": c.start_sec, "end_sec": c.end_sec,
             "product_key": c.product_key, "signals": signals[i], "score": scores[i],
             "selected_rank": rank_of.get(i)}
            for i, c in enumerate(candidates)
        ],
    }  # fmt: skip
    items = [
        _item(r + 1, candidates[i], scores[i], signals[i], sentences, mentions_by_idx)
        for r, i in enumerate(picked)
    ]
    return signals_doc, {"scorer_version": scorer.version, "items": items}
