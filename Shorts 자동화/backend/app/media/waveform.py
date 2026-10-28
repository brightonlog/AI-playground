import subprocess
from array import array
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.errors import JobError


def peak(pcm: bytes) -> float:
    samples = array("h")
    samples.frombytes(pcm[: len(pcm) // 2 * 2])
    return max(-min(samples), max(samples)) / 32768 if samples else 0.0


def build_waveform(audio_path: Path) -> dict[str, Any]:
    """Peaks per 1/N second, scaled so the loudest is 1.0 (spec: 10 per second)."""
    s = get_settings()
    chunk_bytes = s.waveform_sample_rate // s.waveform_peaks_per_sec * 2  # s16le mono
    cmd = ["ffmpeg", "-v", "error", "-i", str(audio_path), "-ac", "1",
           "-ar", str(s.waveform_sample_rate), "-f", "s16le", "-"]  # fmt: skip
    peaks: list[float] = []
    total_bytes = 0
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as proc:
        assert proc.stdout is not None
        while data := proc.stdout.read(chunk_bytes):
            total_bytes += len(data)
            peaks.append(peak(data))
    if proc.returncode != 0:
        raise JobError("waveform_failed", "파형을 만들지 못했습니다")
    top = max(peaks, default=0.0) or 1.0
    return {
        "duration_sec": round(total_bytes / 2 / s.waveform_sample_rate, 2),
        "peaks_per_sec": s.waveform_peaks_per_sec,
        "peaks": [round(p / top, 3) for p in peaks],
    }
