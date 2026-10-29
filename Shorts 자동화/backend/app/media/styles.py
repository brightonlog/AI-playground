"""Style presets (STY-01). Colors are ASS &HAABBGGRR; sizes are 1080x1920 pixels."""

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
