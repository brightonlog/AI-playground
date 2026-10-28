"""Keyword fallback for product mentions, used only when the LLM call fails."""

from typing import Any

from app.core.config import get_settings

# ponytail: fixed beauty/fashion word lists; misses brands and anything off-list.
# Longest first so "선크림" wins over "크림".
_PRODUCT_WORDS = sorted(
    [
        "선크림",
        "크림",
        "세럼",
        "앰플",
        "토너",
        "쿠션",
        "파운데이션",
        "립밤",
        "립스틱",
        "틴트",
        "마스카라",
        "아이섀도",
        "향수",
        "샴푸",
        "클렌저",
        "로션",
        "에센스",
        "마스크팩",
        "가방",
        "지갑",
        "핸드크림",
        "미스트",
        "선스틱",
        "블러셔",
        "컨실러",
    ],  # fmt: skip
    key=len,
    reverse=True,
)
_RECOMMEND_WORDS = ("추천", "강추", "인생템", "애정템", "꿀템", "최고", "좋아요", "좋더라", "사랑")
_USAGE_WORDS = ("발라", "바르", "써보", "써 보", "사용", "뿌려", "뿌리", "얹어", "찍어", "덜어")


def keyword_mentions(sentences: list[dict[str, Any]]) -> list[dict[str, Any]]:
    s = get_settings()
    mentions = []
    for sentence in sentences:
        text = sentence["text"]
        product = next((w for w in _PRODUCT_WORDS if w in text), None)
        if product is None:
            continue
        recommended = any(w in text for w in _RECOMMEND_WORDS)
        mentions.append(
            {
                "sentence_id": sentence["id"],
                "product": product,
                "brand": None,
                "category": product,
                "recommend_strength": (
                    s.keyword_recommend_strength if recommended else s.keyword_base_strength
                ),
                "usage": any(w in text for w in _USAGE_WORDS),
            }
        )
    return mentions
