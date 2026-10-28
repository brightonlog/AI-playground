"""Reason tags (spec 5.3): at most N per section, largest margin over threshold first."""

from app.core.config import get_settings

# tag code -> (signal it checks, screen label)
_SIGNAL_TAGS = {
    "usage_scene": ("usage", "사용하는 장면"),
    "strong_recommend": ("recommend_strength", "강하게 추천해요"),
    "dense_speech": ("density", "대사가 촘촘합니다"),
    "continuous": ("continuity", "끊김 없이 이어집니다"),
}


def make_tags(signals: dict[str, float], brand: str | None) -> list[tuple[str, str]]:
    s = get_settings()
    scored: list[tuple[float, str, str]] = []
    if brand:
        # Brand is yes/no; rank it by how far product_specific sits above "product only".
        margin = signals["product_specific"] - s.product_specific_product_only
        scored.append((margin, "brand_mention", f"소개하는 말 '{brand}'"))
    for code, (signal, label) in _SIGNAL_TAGS.items():
        threshold = s.tag_thresholds[code]
        if signals[signal] >= threshold:
            scored.append((signals[signal] - threshold, code, label))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [(code, label) for _, code, label in scored[: s.tags_max]]
