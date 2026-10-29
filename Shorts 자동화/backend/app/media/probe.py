import json
import subprocess
from pathlib import Path
from typing import Any

from app.core.errors import JobError


def probe(path: Path) -> dict[str, Any]:
    """ffprobe format and stream info."""
    cmd = ["ffprobe", "-v", "error", "-print_format", "json",
           "-show_format", "-show_streams", str(path)]  # fmt: skip
    result = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise JobError("probe_failed", "영상 파일을 읽지 못했습니다")
    return json.loads(result.stdout)  # type: ignore[no-any-return]


def video_size(path: Path) -> tuple[int, int]:
    for stream in probe(path)["streams"]:
        if stream.get("codec_type") == "video":
            return int(stream["width"]), int(stream["height"])
    raise JobError("probe_failed", "영상 트랙이 없습니다")


def duration_sec(path: Path) -> float:
    return round(float(probe(path)["format"]["duration"]), 2)
