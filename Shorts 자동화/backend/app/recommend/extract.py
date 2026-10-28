"""Product mentions per sentence (spec 5.1 step 1): one LLM call, keyword rules on failure."""

import logging
from typing import Any

from pydantic import BaseModel

from app.core.config import get_settings
from app.generate import load_prompt
from app.llm import client as llm
from app.recommend.keywords import keyword_mentions

log = logging.getLogger(__name__)


class Mention(BaseModel):
    sentence_id: str
    product: str
    brand: str | None
    category: str
    recommend_strength: float
    usage: bool


class MentionList(BaseModel):
    mentions: list[Mention]


def _user_message(meta: dict[str, Any], sentences: list[dict[str, Any]]) -> str:
    s = get_settings()
    hints = [
        f"제목: {meta.get('title', '')}",
        f"설명란: {(meta.get('description') or '')[: s.llm_description_max_chars]}",
        f"태그: {', '.join(meta.get('tags') or [])}",
    ]
    lines = [f"{x['id']}\t{x['start_sec']}\t{x['text']}" for x in sentences]
    return "\n".join(hints) + "\n\n## 대사\n" + "\n".join(lines)


def _clean(raw: list[Mention], sentence_ids: set[str]) -> list[dict[str, Any]]:
    """Drop unknown ids, empty products and duplicates; clamp strength to 0~1."""
    seen: set[str] = set()
    mentions = []
    for m in raw:
        product = m.product.strip()
        if m.sentence_id not in sentence_ids or m.sentence_id in seen or not product:
            continue
        seen.add(m.sentence_id)
        mentions.append(
            {
                "sentence_id": m.sentence_id,
                "product": product,
                "brand": (m.brand or "").strip() or None,
                "category": m.category.strip(),
                "recommend_strength": round(min(max(m.recommend_strength, 0.0), 1.0), 2),
                "usage": m.usage,
            }
        )
    return mentions


def extract_mentions(meta: dict[str, Any], sentences: list[dict[str, Any]]) -> dict[str, Any]:
    """Return mentions.json content. `source` is "llm" or "keywords" (fallback)."""
    try:
        result = llm.get_llm().parse(
            load_prompt("extract_mentions"), _user_message(meta, sentences), MentionList
        )
    except llm.LLMError as exc:
        log.warning("mention extraction fell back to keywords: %s", exc)
        return {"source": "keywords", "model": None, "mentions": keyword_mentions(sentences)}
    ids = {x["id"] for x in sentences}
    model = get_settings().llm_model
    return {"source": "llm", "model": model, "mentions": _clean(result.mentions, ids)}
