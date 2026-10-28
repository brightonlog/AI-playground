from typing import Any


def hangul_ratio(json3: dict[str, Any]) -> float:
    """Share of Hangul among letters in a json3 caption track."""
    text = "".join(
        seg.get("utf8", "") for event in json3.get("events", []) for seg in event.get("segs") or []
    )
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return 0.0
    return sum("가" <= ch <= "힣" for ch in letters) / len(letters)
