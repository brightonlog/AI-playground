"""Style presets (STY-01). Colors are ASS &HAABBGGRR; sizes are 1080x1920 pixels."""

import re
from typing import Any

PRESETS: dict[str, dict[str, Any]] = {
    "title_pink": {
        "font": "Pretendard",
        "title_size": 78,
        "title_color": "&H00FFFFFF",
        "title_box": "&H00A055F0",  # pink box behind the title
        "title_margin_v": 200,
        "sub_size": 72,
        "sub_color": "&H00FFFFFF",
        "sub_outline": "&H00000000",
        "sub_outline_px": 5,
        "sub_margin_v": 420,
        "emphasis_color": "&H0000E5FF",  # yellow
    },
}


def resolve(preset_id: str, overrides: dict[str, Any]) -> dict[str, Any]:
    base = PRESETS.get(preset_id, PRESETS["title_pink"])
    return {**base, **{k: v for k, v in overrides.items() if k in base}}


FONTS = ("Pretendard",)
_COLOR = re.compile(r"&H[0-9A-F]{8}")
_INT_RANGE = (0, 1920)  # sizes and margins in 1080x1920 pixels


def clean_overrides(preset_id: str, overrides: dict[str, Any]) -> dict[str, Any]:
    """Only known keys with safe values; anything else could inject ASS. Raises ValueError."""
    if preset_id not in PRESETS:
        raise ValueError(f"unknown preset: {preset_id}")
    base = PRESETS[preset_id]
    for key, value in overrides.items():
        if key not in base:
            raise ValueError(f"unknown style key: {key}")
        if key == "font":
            ok = value in FONTS
        elif isinstance(base[key], int):
            ok = type(value) is int and _INT_RANGE[0] <= value <= _INT_RANGE[1]
        else:
            ok = isinstance(value, str) and _COLOR.fullmatch(value) is not None
        if not ok:
            raise ValueError(f"invalid value for {key}")
    return dict(overrides)
