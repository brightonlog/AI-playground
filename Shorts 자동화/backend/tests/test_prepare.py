import pytest

from app.core.config import get_settings
from app.db.models import Short
from app.db.session import SessionLocal
from app.generate import tts
from app.llm.client import LLMError
from app.media.crop import build_crop
from app.storage import local
from app.workers.short_tasks import run_short
from tests.conftest import HAS_FFMPEG
from tests.test_shorts import create_short, ready_analysis

pytestmark = pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")


def made_short(client, start=10.0, end=40.0):
    short_id = create_short(client, ready_analysis(client), start, end).json()["id"]
    run_short(short_id)
    return short_id, local.short_dir(short_id)


def test_products_in_range_become_whisper_hints(client, _isolate):
    source, _ = _isolate
    made_short(client, 0.5, 30)  # the fixture mentions the sunscreen at 1.5~9s
    assert source.transcriber.hints == "라운드랩 톤업 선크림"


def test_prepare_writes_draft(client):
    short_id, folder = made_short(client)
    body = client.get(f"/api/v1/shorts/{short_id}").json()
    assert (body["status"], body["edit_version"], body["warnings"]) == ("editing", 1, [])

    words = local.read_json(folder / "words.json")["words"]
    assert words[0] == {"text": " 이", "start_sec": 10.5, "end_sec": 10.7}  # offset 9 + 1.5

    edit = local.read_json(folder / "edit.json")
    assert edit["version"] == 1 and edit["title"]["visible"]
    assert len(edit["title"]["text"]) == get_settings().title_max_chars
    assert [(x["id"], x["kind"]) for x in edit["lines"]] == [
        ("n1", "narration"),  # one narration survives cleaning, placed before its anchor
        ("l1", "speech"),
        ("l2", "speech"),
    ]
    narration, first = edit["lines"][0], edit["lines"][1]
    assert (narration["anchor_line_id"], narration["audio_path"]) == ("l1", "narration/n1.mp3")
    assert narration["audio_sec"] > 0 and (folder / "narration" / "n1.mp3").exists()
    assert first["text"] == "이 선크림 진짜 좋아요."
    assert [w["id"] for w in first["words"]] == ["w1", "w2", "w3", "w4"]
    second = edit["lines"][2]  # LLM fix (no manual captions in range), original kept
    assert (second["text"], second["words"][0]["raw_text"]) == ("매일매일 써요.", "매일")
    assert second["words"][0]["id"] == "w5"

    crop = local.read_json(folder / "crop.json")
    assert (crop["width"], crop["height"], crop["crop_h"]) == (640, 360, 360)
    assert crop["keyframes"][0]["t"] == 9.0


def test_llm_failure_uses_video_title(client, _isolate):
    source, _ = _isolate
    source.llm.error = LLMError("down")
    short_id, folder = made_short(client)
    assert client.get(f"/api/v1/shorts/{short_id}").json()["warnings"] == ["llm_fallback"]
    edit = local.read_json(folder / "edit.json")
    assert edit["title"]["text"] == "t"
    assert all(x["kind"] == "speech" for x in edit["lines"])


def test_face_failure_centers_crop(client, _isolate):
    source, _ = _isolate
    source.faces.error = RuntimeError("model broke")
    short_id, folder = made_short(client)
    assert client.get(f"/api/v1/shorts/{short_id}").json()["warnings"] == ["crop_fallback"]
    crop = local.read_json(folder / "crop.json")
    assert crop["keyframes"] == [{"t": 9.0, "x": (640 - crop["crop_w"]) // 2}]


def test_no_speech_fails(client, _isolate):
    source, _ = _isolate
    source.transcriber.words = []
    short_id, _ = made_short(client)
    body = client.get(f"/api/v1/shorts/{short_id}").json()
    assert (body["status"], body["stage"], body["error"]["code"]) == (
        "failed",
        "preparing",
        "no_speech",
    )
    with SessionLocal() as db:
        assert db.get(Short, short_id).edit_version == 0


def test_build_crop_follows_face_and_clamps():
    crop = build_crop([None, 1.0, 1.0, 1.0, 1.0, None], 1920, 1080, 100.0)
    assert (crop["crop_w"], crop["crop_h"], crop["y"]) == (608, 1080, 0)
    assert [k["t"] for k in crop["keyframes"]] == [100.0, 100.5, 101.0, 101.5, 102.0, 102.5]
    assert all(k["x"] == 1920 - 608 for k in crop["keyframes"])  # pushed to the right edge

    tall = build_crop([0.5], 1080, 1920, 0.0)  # already vertical: full width, centered
    assert (tall["crop_w"], tall["crop_h"], tall["keyframes"][0]["x"]) == (1080, 1920, 0)


def test_tts_cache_reuses_audio(tmp_path, monkeypatch):
    calls = []
    real = tts.FakeTTS.synthesize
    monkeypatch.setattr(
        tts.FakeTTS, "synthesize", lambda self, *a: (calls.append(a[0]), real(self, *a))
    )
    tts.speak("캐시 확인 문장", "default", tmp_path / "a.mp3")
    tts.speak("캐시 확인 문장", "default", tmp_path / "b.mp3")
    assert len(calls) == 1
    assert (tmp_path / "a.mp3").read_bytes() == (tmp_path / "b.mp3").read_bytes()


def test_progress_stores_plain_float(monkeypatch):
    import numpy as np

    from app.services import events
    from app.workers.jobs import Progress

    seen = []
    monkeypatch.setattr(events, "set_progress", lambda kind, job_id, stage, p: seen.append(p))
    Progress("shorts", "sh_aaaaaaaa", lambda: {"preparing": 1.0}).update(
        "preparing", np.float64(0.5)
    )
    assert type(seen[0]) is float  # numpy floats reach Redis as "np.float64(0.5)"
