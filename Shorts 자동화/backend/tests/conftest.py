import os
import shutil
import subprocess
import tempfile
from pathlib import Path

# Point DATA_DIR at a temp dir before app modules read settings.
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="shorts-test-")
# Env beats .env: tests must never reach the real API, even if a key is configured.
os.environ["ANTHROPIC_API_KEY"] = ""

import json  # noqa: E402

import pytest  # noqa: E402
import redis  # noqa: E402
from sqlalchemy import delete  # noqa: E402

from app.db.models import Analysis, Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.llm import client as llm  # noqa: E402
from app.recommend.extract import MentionList  # noqa: E402
from app.services import events  # noqa: E402
from app.sources import youtube  # noqa: E402
from app.transcript import whisper  # noqa: E402
from app.transcript.sentences import Token  # noqa: E402
from app.workers import analysis_tasks  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
HAS_FFMPEG = shutil.which("ffmpeg") is not None

Base.metadata.create_all(engine)


def make_tone(path: Path, seconds: float = 2.0) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={seconds}",
            "-c:a",
            "aac",
            str(path),
        ],  # fmt: skip
        check=True,
    )


class FakeSource:
    def __init__(self, tone: Path | None) -> None:
        self.tone = tone
        self.info = youtube.VideoInfo(
            video_id="dQw4w9WgXcQ", title="t", channel="c", duration_sec=600
        )
        self.captions: youtube.Captions | None = youtube.Captions(
            kind="manual", json3=json.loads((FIXTURES / "captions_manual.json3").read_text("utf-8"))
        )

    def get_info(self, url: str) -> youtube.VideoInfo:
        return self.info

    def fetch_captions(self, url: str) -> youtube.Captions | None:
        return self.captions

    def download_audio(self, url: str, dest: Path, on_progress: youtube.ProgressFn) -> None:
        assert self.tone is not None, "ffmpeg required"
        on_progress(0.5)
        shutil.copy(self.tone, dest)


class FakeTranscriber:
    def __init__(self) -> None:
        self.tokens = [Token(" 이 선크림 진짜 좋아요.", 0.5, 2.0), Token(" 매일 써요.", 2.2, 3.4)]

    def transcribe(self, audio: Path, on_progress: whisper.ProgressFn) -> list[Token]:
        assert audio.exists()
        on_progress(1.0)
        return self.tokens


class FakeLLM:
    """Replays a recorded LLM response; set `error` to simulate a failed call."""

    def __init__(self) -> None:
        self.response = json.loads((FIXTURES / "llm_mentions.json").read_text("utf-8"))
        self.error: Exception | None = None
        self.calls: list[str] = []

    def parse(self, system, user, schema):
        self.calls.append(user)
        if self.error:
            raise self.error
        assert schema is MentionList
        return schema.model_validate(self.response)


class _NoRedis:
    """Async Redis stand-in that is always down, so SSE falls back to polling."""

    def pubsub(self):
        return self

    async def subscribe(self, *_):
        raise redis.ConnectionError("no redis in tests")

    async def aclose(self):
        pass


@pytest.fixture(scope="session")
def tone(tmp_path_factory: pytest.TempPathFactory) -> Path | None:
    if not HAS_FFMPEG:
        return None
    path = tmp_path_factory.mktemp("media") / "tone.m4a"
    make_tone(path)
    return path


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch, tone: Path | None):
    with SessionLocal() as db:
        db.execute(delete(Analysis))
        db.commit()
    source = FakeSource(tone)
    monkeypatch.setattr(youtube, "get_source", lambda: source)
    transcriber = FakeTranscriber()
    source.transcriber = transcriber  # type: ignore[attr-defined]
    monkeypatch.setattr(whisper, "get_transcriber", lambda: transcriber)
    fake_llm = FakeLLM()
    source.llm = fake_llm  # type: ignore[attr-defined]
    monkeypatch.setattr(llm, "get_llm", lambda: fake_llm)
    monkeypatch.setattr(events, "publish", lambda *a, **k: None)
    monkeypatch.setattr(events, "set_progress", lambda *a, **k: None)
    monkeypatch.setattr(events, "get_progress", lambda *a, **k: None)
    monkeypatch.setattr(events.aioredis.Redis, "from_url", lambda *a, **k: _NoRedis())
    queued: list[str] = []
    monkeypatch.setattr(analysis_tasks, "enqueue", queued.append)
    yield source, queued


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    # One portal (event loop) for the whole session instead of one per request.
    with TestClient(app) as c:
        yield c
