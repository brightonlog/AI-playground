"""faster-whisper wrapper. Everything that runs Whisper goes through `Transcriber`."""

import logging
import os
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from app.core.config import get_settings
from app.core.errors import JobError
from app.transcript.sentences import Token

log = logging.getLogger(__name__)

ProgressFn = Callable[[float], None]


class Transcriber(Protocol):
    def transcribe(
        self, audio: Path, on_progress: ProgressFn, words: bool = False, hints: str = ""
    ) -> list[Token]: ...


def _add_cuda_dll_dirs() -> None:
    # Windows: CUDA DLLs from the optional `cuda` extra (nvidia-* wheels) are not on PATH.
    if os.name != "nt":
        return
    try:
        import nvidia  # type: ignore[import-not-found]
    except ImportError:
        return
    for root in nvidia.__path__:
        for bin_dir in Path(root).glob("*/bin"):
            os.add_dll_directory(str(bin_dir))
            os.environ["PATH"] = f"{bin_dir}{os.pathsep}{os.environ['PATH']}"


@lru_cache
def _model(name: str, device: str):  # type: ignore[no-untyped-def]
    if device == "cuda":
        _add_cuda_dll_dirs()
    from faster_whisper import WhisperModel  # heavy import, only in the worker

    compute_type = "float16" if device == "cuda" else "int8"
    return WhisperModel(name, device=device, compute_type=compute_type)


class FasterWhisper:
    def transcribe(
        self, audio: Path, on_progress: ProgressFn, words: bool = False, hints: str = ""
    ) -> list[Token]:
        """Segment tokens, or word tokens (leading space kept) when `words` is set.
        `hints` are names the audio likely contains (Whisper hotwords)."""
        s = get_settings()
        try:
            model = _model(s.whisper_model, s.whisper_device)
            segments, info = model.transcribe(
                str(audio),
                language="ko",
                vad_filter=True,
                word_timestamps=words,
                hotwords=hints or None,
            )
            tokens: list[Token] = []
            for seg in segments:  # lazy generator: decoding happens while iterating
                if words:
                    tokens.extend(Token(w.word, w.start, w.end) for w in seg.words or [])
                else:
                    tokens.append(Token(" " + seg.text.strip(), seg.start, seg.end))
                if info.duration:
                    on_progress(min(seg.end / info.duration, 1.0))
        except Exception as exc:
            log.exception("whisper failed (model=%s device=%s)", s.whisper_model, s.whisper_device)
            raise JobError(
                "transcribe_failed",
                "받아쓰기에 실패했습니다. WHISPER_MODEL·WHISPER_DEVICE 설정을 확인해 주세요",
            ) from exc
        return tokens


def get_transcriber() -> Transcriber:
    return FasterWhisper()
