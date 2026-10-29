"""9:16 crop that follows the face (spec 6: crop.json, interpolated linearly at render)."""

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from app.core.config import get_settings
from app.core.errors import JobError
from app.media.probe import duration_sec, video_size

ProgressFn = Callable[[float], None]


class FaceFinder(Protocol):
    def centers(self, video: Path, on_progress: ProgressFn) -> list[float | None]:
        """Face center x (0~1 of frame width) every `crop_sample_sec`, None where no face."""
        ...


def _largest_center(detections: Any, frame_width: int) -> float | None:
    boxes = [d.bounding_box for d in detections]
    if not boxes:
        return None
    box = max(boxes, key=lambda b: b.width * b.height)
    return float((box.origin_x + box.width / 2) / frame_width)


class MediaPipeFaces:
    def centers(self, video: Path, on_progress: ProgressFn) -> list[float | None]:
        import mediapipe as mp  # heavy import, only in the worker
        import numpy as np
        from mediapipe.tasks.python import BaseOptions, vision

        s = get_settings()
        width, height = video_size(video)
        dw = s.crop_detect_width
        dh = max(2, round(dw * height / width / 2) * 2)
        total = duration_sec(video) or 1.0
        options = vision.FaceDetectorOptions(
            # A buffer, not a path: the native loader cannot open non-ASCII paths on Windows.
            base_options=BaseOptions(model_asset_buffer=s.face_model_path.read_bytes()),
            min_detection_confidence=s.crop_min_confidence,
        )
        cmd = ["ffmpeg", "-v", "error", "-i", str(video),
               "-vf", f"fps={1 / s.crop_sample_sec},scale={dw}:{dh}",
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]  # fmt: skip
        frame_bytes = dw * dh * 3
        centers: list[float | None] = []
        with (
            vision.FaceDetector.create_from_options(options) as detector,
            subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as proc,
        ):
            assert proc.stdout is not None
            while len(data := proc.stdout.read(frame_bytes)) == frame_bytes:
                frame = np.frombuffer(data, np.uint8).reshape(dh, dw, 3)
                result = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=frame))
                centers.append(_largest_center(result.detections, dw))
                on_progress(min(len(centers) * s.crop_sample_sec / total, 1.0))
        if proc.returncode != 0:
            raise JobError("crop_failed", "얼굴 위치를 찾지 못했습니다")
        return centers


def _fill(centers: list[float | None]) -> list[float]:
    """Hold the last face through gaps, use the first face before it, the middle if none."""
    known = [c for c in centers if c is not None]
    last = known[0] if known else 0.5
    filled = []
    for c in centers:
        last = c if c is not None else last
        filled.append(last)
    return filled


def _smooth(values: list[float], window: int) -> list[float]:
    half = window // 2
    out = []
    for i in range(len(values)):
        part = values[max(0, i - half) : i + half + 1]
        out.append(sum(part) / len(part))
    return out


def build_crop(
    centers: list[float | None], width: int, height: int, offset_sec: float
) -> dict[str, Any]:
    """crop.json: a fixed-size 9:16 window panned horizontally. `t` is source-video seconds."""
    s = get_settings()
    if width / height > s.crop_aspect:
        crop_h, crop_w = height, round(height * s.crop_aspect / 2) * 2
    else:  # already narrow: keep the width, cut top and bottom
        crop_w, crop_h = width, min(height, round(width / s.crop_aspect / 2) * 2)
    xs = _smooth(_fill(centers or [None]), s.crop_smooth_window)
    keyframes = [
        {
            "t": round(offset_sec + i * s.crop_sample_sec, 2),
            "x": min(max(round(c * width - crop_w / 2), 0), width - crop_w),
        }
        for i, c in enumerate(xs)
    ]
    return {
        "width": width,
        "height": height,
        "crop_w": crop_w,
        "crop_h": crop_h,
        "y": (height - crop_h) // 2,
        "keyframes": keyframes,
    }


def get_face_finder() -> FaceFinder:
    return MediaPipeFaces()
