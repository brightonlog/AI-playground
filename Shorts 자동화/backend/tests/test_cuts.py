import pytest

from app.services.cuts import is_filler
from tests.conftest import HAS_FFMPEG
from tests.test_edit import edit_of, patch, short_clip_ok, words_of  # noqa: F401
from tests.test_prepare import made_short

pytestmark = pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")


def suggest(client, short_id, body):
    return client.post(f"/api/v1/shorts/{short_id}/cut-suggestions", json=body)


def test_is_filler():
    assert all(map(is_filler, ["음", "음...", "으음", "어어,", "그니까"]))
    assert not any(map(is_filler, ["음식", "아니요", "그", "...", ""]))


def test_silence_suggestion_trims_the_pause(client):
    short_id, _ = made_short(client)
    r = suggest(client, short_id, {"type": "silence", "min_gap_sec": 0.5})
    body = r.json()
    assert body["version"] == 2
    assert [(s["id"], s["type"], s["word_ids"]) for s in body["suggestions"]] == [
        ("s1", "silence", ["w4"])  # 좋아요. (ends 13.2) ... 매일 (starts 13.8)
    ]
    short = client.get(f"/api/v1/shorts/{short_id}").json()
    assert short["preview_version"] == 2  # suggestions alone do not change the video

    r = patch(client, short_id, [{"op": "apply_suggestions", "suggestion_ids": ["s1"]}])
    assert r.json()["duration_sec"] == 2.55  # 0.6s pause cut to 0.15s
    edit = edit_of(client, short_id)["edit"]
    assert words_of(edit)["w4"]["trim_gap_after"] and edit["pending_suggestions"] == []


def test_filler_and_repeat_suggestions(client):
    short_id, _ = made_short(client)
    ops = [{"op": "set_word_text", "word_id": "w1", "text": "음..."},
           {"op": "set_word_text", "word_id": "w3", "text": "선크림"}]  # fmt: skip
    patch(client, short_id, ops)
    silence = suggest(client, short_id, {"type": "silence"}).json()["suggestions"]
    fillers = suggest(client, short_id, {"type": "filler"}).json()["suggestions"]
    assert [(s["id"], s["word_ids"]) for s in fillers] == [("s2", ["w1"]), ("s3", ["w2"])]
    assert "반복" in fillers[1]["reason"]

    again = suggest(client, short_id, {"type": "filler"}).json()  # replaces, keeps silence
    assert [s["id"] for s in again["suggestions"]] == ["s4", "s5"]
    pending = edit_of(client, short_id)["edit"]["pending_suggestions"]
    assert [s["id"] for s in pending] == [silence[0]["id"], "s4", "s5"]

    patch(client, short_id, [{"op": "apply_suggestions", "suggestion_ids": ["s4"]}])
    assert words_of(edit_of(client, short_id)["edit"])["w1"]["deleted"]
    assert suggest(client, short_id, {"type": "nope"}).status_code == 422
