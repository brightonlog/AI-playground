"""yt-dlp wrapper. Everything that talks to YouTube goes through `VideoSource`.

No cookie, login or DRM options on purpose: restricted videos are rejected, never bypassed.
"""

import json
import logging
import os
import re
import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol
from urllib.parse import parse_qs, urlparse

import yt_dlp

from app.core.config import get_settings
from app.core.errors import JobError
from app.transcript.captions import hangul_ratio

log = logging.getLogger(__name__)

_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}
_PATH_PREFIXES = {"shorts", "live", "embed"}
_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_LIVE_STATUSES = {"is_live", "is_upcoming", "post_live"}
_BLOCKED_AVAILABILITY = {"private", "premium_only", "subscriber_only", "needs_auth"}


def parse_video_id(url: str) -> str | None:
    """Return the 11-char id for a YouTube video URL, else None. Only YouTube hosts pass."""
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return None
    host = parsed.hostname or ""
    if parsed.scheme not in ("http", "https") or host not in _HOSTS:
        return None
    if host == "youtu.be":
        candidate = parsed.path.strip("/").split("/")[0]
    elif parsed.path == "/watch":
        candidate = parse_qs(parsed.query).get("v", [""])[0]
    else:
        parts = parsed.path.strip("/").split("/")
        candidate = parts[1] if len(parts) >= 2 and parts[0] in _PATH_PREFIXES else ""
    return candidate if _VIDEO_ID_RE.fullmatch(candidate) else None


def canonical_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


@dataclass
class VideoInfo:
    video_id: str
    title: str
    channel: str
    duration_sec: float
    thumbnail_url: str | None = None
    description: str = ""
    tags: list[str] = field(default_factory=list)
    chapters: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Captions:
    kind: Literal["manual", "auto"]
    json3: dict[str, Any]


ProgressFn = Callable[[float], None]


class VideoSource(Protocol):
    def get_info(self, url: str) -> VideoInfo: ...

    def fetch_captions(self, url: str) -> Captions | None: ...

    def download_audio(self, url: str, dest: Path, on_progress: ProgressFn) -> None: ...


def _opts(**extra: Any) -> dict[str, Any]:
    return {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": get_settings().source_timeout_sec,
        **extra,
    }


def _check_available(info: dict[str, Any]) -> None:
    if info.get("live_status") in _LIVE_STATUSES:
        raise JobError("video_unavailable", "라이브 영상은 지원하지 않습니다")
    if (info.get("age_limit") or 0) >= 18:
        raise JobError("video_unavailable", "연령 제한 영상은 지원하지 않습니다")
    if info.get("availability") in _BLOCKED_AVAILABILITY or info.get("_has_drm"):
        raise JobError("video_unavailable", "로그인이나 권한이 필요한 영상은 지원하지 않습니다")


def _pick_track(tracks: dict[str, list[dict[str, Any]]], keys: list[str]) -> str | None:
    for key in keys:
        for track in tracks.get(key) or []:
            if track.get("ext") == "json3" and track.get("url"):
                return str(track["url"])
    return None


class YtDlpSource:
    def _extract(self, url: str) -> dict[str, Any]:
        try:
            with yt_dlp.YoutubeDL(_opts()) as ydl:
                info = ydl.extract_info(url, download=False)
        except yt_dlp.utils.DownloadError as exc:
            raise JobError("video_unavailable", "영상 정보를 가져올 수 없습니다") from exc
        if not info:
            raise JobError("video_unavailable", "영상 정보를 가져올 수 없습니다")
        _check_available(info)
        return dict(info)

    def get_info(self, url: str) -> VideoInfo:
        info = self._extract(url)
        return VideoInfo(
            video_id=str(info["id"]),
            title=info.get("title") or "",
            channel=info.get("channel") or info.get("uploader") or "",
            duration_sec=float(info.get("duration") or 0),
            thumbnail_url=info.get("thumbnail"),
            description=info.get("description") or "",
            tags=list(info.get("tags") or []),
            chapters=list(info.get("chapters") or []),
        )

    def fetch_captions(self, url: str) -> Captions | None:
        # Re-extract instead of storing caption URLs: they are signed and expire.
        info = self._extract(url)
        manual = info.get("subtitles") or {}
        auto_keys = ["ko-orig"]
        if str(info.get("language") or "").startswith("ko"):
            auto_keys.append("ko")  # otherwise "ko" is a machine translation
        candidates: list[tuple[Literal["manual", "auto"], str | None]] = [
            (
                "manual",
                _pick_track(manual, [k for k in manual if k == "ko" or k.startswith("ko-")]),
            ),
            ("auto", _pick_track(info.get("automatic_captions") or {}, auto_keys)),
        ]
        for kind, track_url in candidates:
            if not track_url:
                continue
            try:
                with yt_dlp.YoutubeDL(_opts()) as ydl:
                    data = json.loads(ydl.urlopen(track_url).read())
            except Exception:
                # Captions are optional: Whisper covers a track that fails to download.
                log.warning("caption download failed (%s), skipping track", kind)
                continue
            # Uploaders sometimes label other-language tracks as "ko"; skip those.
            if hangul_ratio(data) >= get_settings().captions_min_hangul_ratio:
                return Captions(kind=kind, json3=data)
        return None

    def download_audio(self, url: str, dest: Path, on_progress: ProgressFn) -> None:
        tmp_dir = dest.parent / "_audio_tmp"
        shutil.rmtree(tmp_dir, ignore_errors=True)

        def hook(d: dict[str, Any]) -> None:
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            if d.get("status") == "downloading" and total:
                on_progress(min(d.get("downloaded_bytes", 0) / total, 1.0))

        opts = _opts(
            format="bestaudio[ext=m4a]/bestaudio",
            outtmpl=str(tmp_dir / "audio.%(ext)s"),
            postprocessors=[{"key": "FFmpegExtractAudio", "preferredcodec": "m4a"}],
            progress_hooks=[hook],
        )
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
        except yt_dlp.utils.DownloadError as exc:
            raise JobError("download_failed", "오디오를 받지 못했습니다") from exc
        if not (tmp_dir / "audio.m4a").exists():
            raise JobError("download_failed", "오디오를 받지 못했습니다")
        # Move into place only when complete, so an existing audio.m4a is never partial.
        os.replace(tmp_dir / "audio.m4a", dest)
        shutil.rmtree(tmp_dir, ignore_errors=True)


def get_source() -> VideoSource:
    return YtDlpSource()
