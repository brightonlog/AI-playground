"""ffmpeg render of an edit (spec 6 렌더 규칙): cut, 9:16 crop, subtitles, narration mix.

ffmpeg runs inside the short's folder with relative paths, so filter strings never contain
the (possibly non-ASCII, drive-lettered) absolute path.
"""

import logging
import os
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.errors import JobError
from app.media import styles, subtitles, timeline
from app.schemas.edit import EditDoc, NarrationLine

log = logging.getLogger(__name__)

ProgressFn = Callable[[float], None]


class RenderCancelled(Exception):
    """A newer edit arrived while rendering; the output was not replaced."""


def crop_x_expr(crop: dict[str, Any], offset: float) -> str:
    """Crop left edge as an ffmpeg expression of section time `t`, linear between keyframes."""
    pts = [(round(k["t"] - offset, 3), k["x"]) for k in crop["keyframes"]]
    if len(pts) == 1:
        return str(pts[0][1])
    terms = [f"lt(t,{pts[0][0]})*{pts[0][1]}"]
    for (a, xa), (b, xb) in zip(pts, pts[1:], strict=False):
        terms.append(f"gte(t,{a})*lt(t,{b})*({xa}+({xb - xa})*(t-{a})/{round(b - a, 3)})")
    terms.append(f"gte(t,{pts[-1][0]})*{pts[-1][1]}")
    return "+".join(terms)


def _fonts_dir(folder: Path) -> str:
    fonts = get_settings().fonts_dir
    try:
        return os.path.relpath(fonts, folder).replace("\\", "/")
    except ValueError:  # different drive on Windows
        return fonts.as_posix().replace(":", r"\:")


Narration = tuple[str, float, float]  # relative audio path, output start, audio seconds


def _narrations(doc: EditDoc, folder: Path, kept: list[timeline.Kept]) -> list[Narration]:
    """Narrations narrations whose anchor line is still alive."""
    first_out: dict[str, float] = {}
    for k in kept:
        first_out.setdefault(k.line_id, k.out_start)
    out = []
    for n in doc.lines:
        if not isinstance(n, NarrationLine) or n.anchor_line_id not in first_out:
            continue
        if not (folder / n.audio_path).resolve().is_relative_to(folder.resolve()):
            raise JobError("render_failed", "나레이션 파일 경로가 올바르지 않습니다")
        out.append((n.audio_path, first_out[n.anchor_line_id], n.audio_sec))
    return out


def _filter(
    doc: EditDoc, folder: Path, crop: dict[str, Any], offset: float, size: tuple[int, int],
    kept: list[timeline.Kept], narrations: list[Narration],
) -> str:  # fmt: skip
    s = get_settings()
    select = "+".join(
        f"between(t,{round(a - offset, 3)},{round(b - offset, 3)})"
        for a, b in timeline.segments(kept)
    )
    video = (
        f"[0:v]crop=w={crop['crop_w']}:h={crop['crop_h']}:x='{crop_x_expr(crop, offset)}'"
        f":y={crop['y']},select='{select}',setpts=N/FRAME_RATE/TB,"
        f"scale={size[0]}:{size[1]},setsar=1,"
        f"subtitles=filename=subs.ass:fontsdir='{_fonts_dir(folder)}'[v]"
    )
    audio = [f"[0:a]aselect='{select}',asetpts=N/SR/TB"]
    if narrations:
        duck = "+".join(f"between(t,{start},{start + sec})" for _, start, sec in narrations)
        audio[0] += f",volume='if({duck},{s.narration_duck_volume},1)':eval=frame"
    audio[0] += "[orig]"
    labels = "[orig]"
    for i, (_, start, _sec) in enumerate(narrations, start=1):
        audio.append(f"[{i}:a]adelay=delays={round(start * 1000)}:all=1[n{i}]")
        labels += f"[n{i}]"
    audio.append(f"{labels}amix=inputs={len(narrations) + 1}:duration=first:normalize=0[a]")
    return ";\n".join([video, *audio])


def render(
    folder: Path, doc: EditDoc, crop: dict[str, Any], offset: float, out_name: str,
    size: tuple[int, int], crf: int, on_progress: ProgressFn,
    cancelled: Callable[[], bool] = lambda: False,
) -> float:  # fmt: skip
    """Render `folder/out_name` atomically; returns the output duration in seconds.
    `cancelled` is polled on each ffmpeg progress report (about twice a second)."""
    s = get_settings()
    kept = timeline.kept_words(doc)
    if not kept:
        raise JobError("empty_output", "남은 대사가 없어 영상을 만들 수 없습니다")
    duration = timeline.duration(kept)
    style = styles.resolve(doc.style.preset_id, doc.style.overrides)
    (folder / "subs.ass").write_text(
        subtitles.build_ass(doc, kept, duration, style), encoding="utf-8"
    )
    narrations = _narrations(doc, folder, kept)
    graph = _filter(doc, folder, crop, offset, size, kept, narrations)
    (folder / "render.filter").write_text(graph, encoding="utf-8")

    tmp = f"{out_name}.tmp.mp4"
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", "section.mp4"]
    for path, _, _ in narrations:
        cmd += ["-i", path]
    cmd += ["-/filter_complex", "render.filter", "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", s.render_preset, "-crf", str(crf),
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
            "-progress", "pipe:1", "-nostats", tmp]  # fmt: skip
    with (
        open(folder / "render.log", "wb") as errlog,
        subprocess.Popen(cmd, cwd=folder, stdout=subprocess.PIPE, stderr=errlog, text=True) as proc,
    ):
        assert proc.stdout is not None
        for line in proc.stdout:
            if line.startswith("out_time_us=") and line[12:].strip().isdigit():
                on_progress(min(int(line[12:]) / 1e6 / duration, 1.0))
            elif line.startswith("progress=") and cancelled():
                proc.kill()
                proc.wait()
                raise RenderCancelled
    if proc.returncode != 0:
        log.error("render failed: %s", (folder / "render.log").read_text("utf-8", "replace"))
        raise JobError("render_failed", "영상을 만들지 못했습니다")
    os.replace(folder / tmp, folder / out_name)
    return duration
