"""Narration speech. Everything that makes speech goes through `TTSProvider`."""

import hashlib
import os
import shutil
import subprocess
from pathlib import Path
from typing import Protocol

from app.core.config import get_settings
from app.core.errors import JobError


class TTSProvider(Protocol):
    name: str

    def synthesize(self, text: str, voice_id: str, dest: Path) -> None:
        """Write an mp3 of `text` to `dest`."""
        ...


class FakeTTS:
    """A quiet tone as long as the text would take to read. Stands in until a provider is chosen."""

    name = "fake"

    def synthesize(self, text: str, voice_id: str, dest: Path) -> None:
        s = get_settings()
        seconds = max(s.fake_tts_min_sec, len(text) * s.fake_tts_sec_per_char)
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
               "-i", f"sine=frequency=220:duration={seconds:.2f}",
               "-af", "volume=0.2", "-c:a", "libmp3lame", "-f", "mp3", str(dest)]  # fmt: skip
        if subprocess.run(cmd, capture_output=True).returncode != 0:
            raise JobError("tts_failed", "나레이션 음성을 만들지 못했습니다")


def get_tts() -> TTSProvider:
    provider = get_settings().tts_provider
    if provider == "fake":
        return FakeTTS()
    raise JobError("tts_unavailable", f"지원하지 않는 TTS_PROVIDER입니다: {provider}")


def speak(text: str, voice_id: str, dest: Path) -> None:
    """Synthesize through a cache keyed by provider, voice and text, then copy to `dest`."""
    tts = get_tts()
    key = hashlib.sha256(f"{tts.name}\n{voice_id}\n{text}".encode()).hexdigest()
    cache_dir = get_settings().data_dir / "tts_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = cache_dir / f"{key}.mp3"
    if not cached.exists():
        tmp = cache_dir / f"{key}.tmp"
        tts.synthesize(text, voice_id, tmp)
        os.replace(tmp, cached)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(cached, dest)
