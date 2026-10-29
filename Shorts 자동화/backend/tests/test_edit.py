import pytest

from app.core.config import get_settings
from app.media import render
from app.schemas.edit import EditDoc
from app.storage import local
from app.workers.render_tasks import run_preview
from tests.conftest import HAS_FFMPEG
from tests.test_prepare import made_short
from tests.test_shorts import create_short, ready_analysis

pytestmark = pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")


@pytest.fixture(autouse=True)
def short_clip_ok(monkeypatch):
    # The 5-second test clip holds 3 seconds of speech, under the 5-second output minimum.
    monkeypatch.setattr(get_settings(), "output_min_sec", 1.0)


def patch(client, short_id, ops, base=None):
    if base is None:
        base = client.get(f"/api/v1/shorts/{short_id}/edit").json()["edit"]["version"]
    return client.patch(f"/api/v1/shorts/{short_id}/edit", json={"base_version": base, "ops": ops})


def edit_of(client, short_id):
    return client.get(f"/api/v1/shorts/{short_id}/edit").json()


def words_of(edit):
    return {w["id"]: w for x in edit["lines"] if x["kind"] == "speech" for w in x["words"]}


def test_get_edit(client):
    short_id = create_short(client, ready_analysis(client)).json()["id"]
    r = client.get(f"/api/v1/shorts/{short_id}/edit")
    assert (r.status_code, r.json()["error"]) == (409, "edit_not_ready")

    short_id, _ = made_short(client)
    body = edit_of(client, short_id)
    assert (body["duration_sec"], body["out_start_sec"]) == (3.0, 10.5)
    assert body["edit"]["version"] == 1


def test_delete_words_then_preview(client, _isolate):
    _, queued = _isolate
    short_id, folder = made_short(client)
    r = patch(client, short_id, [{"op": "delete_words", "word_ids": ["w2", "w3"]}])
    assert r.json() == {"version": 2, "duration_sec": 2.1, "preview_status": "pending"}
    assert queued[-1] == f"preview:{short_id}"
    edit = edit_of(client, short_id)
    assert edit["edit"]["lines"][1]["words"][1]["deleted"] is True

    run_preview(short_id)
    short = client.get(f"/api/v1/shorts/{short_id}").json()
    assert (short["preview_status"], short["preview_version"]) == ("ready", 2)

    r = patch(client, short_id, [{"op": "restore_all"}])
    assert r.json()["duration_sec"] == 3.0


def test_conflict_and_atomic_failure(client):
    short_id, _ = made_short(client)
    r = patch(client, short_id, [{"op": "restore_all"}], base=0)
    assert (r.status_code, r.json()["error"]) == (409, "version_conflict")

    r = patch(client, short_id, [{"op": "delete_words", "word_ids": ["w1"]},
                                 {"op": "delete_words", "word_ids": ["w99"]}])  # fmt: skip
    assert (r.status_code, r.json()["error"]) == (422, "invalid_op")
    edit = edit_of(client, short_id)["edit"]
    assert edit["version"] == 1 and not words_of(edit)["w1"]["deleted"]  # nothing applied

    r = patch(client, short_id, [{"op": "delete_line", "line_id": "l1"},
                                 {"op": "delete_line", "line_id": "l2"}])  # fmt: skip
    assert (r.status_code, r.json()["error"]) == (422, "invalid_duration")
    r = patch(client, short_id, [{"op": "set_title", "text": "가" * 31}])
    assert r.status_code == 422


def test_word_text_and_split(client):
    short_id, _ = made_short(client)
    ops = [{"op": "set_word_text", "word_id": "w2", "text": "썬크림"},
           {"op": "split_line", "line_id": "l1", "word_id": "w3"}]  # fmt: skip
    assert patch(client, short_id, ops).status_code == 200
    edit = edit_of(client, short_id)["edit"]
    speech = [x for x in edit["lines"] if x["kind"] == "speech"]
    assert [(x["id"], x["text"]) for x in speech] == [
        ("l1", "이 썬크림"),
        ("l3", "진짜 좋아요."),
        ("l2", "매일매일 써요."),
    ]
    assert words_of(edit)["w2"]["raw_text"] == "선크림"

    patch(client, short_id, [{"op": "set_word_text", "word_id": "w2", "text": "선크림"}])
    assert words_of(edit_of(client, short_id)["edit"])["w2"]["raw_text"] is None
    r = patch(client, short_id, [{"op": "split_line", "line_id": "l1", "word_id": "w1"}])
    assert r.status_code == 422


def test_narration_ops_manage_audio(client):
    short_id, folder = made_short(client)
    ops = [{"op": "add_narration", "text": "두 번째 나레이션", "anchor_line_id": "l2"},
           {"op": "set_narration", "line_id": "n1", "text": "바꾼 첫 나레이션"}]  # fmt: skip
    assert patch(client, short_id, ops).status_code == 200
    lines = edit_of(client, short_id)["edit"]["lines"]
    assert [x["id"] for x in lines] == ["n1", "l1", "n2", "l2"]
    n1 = lines[0]
    assert n1["text"] == "바꾼 첫 나레이션" and n1["audio_path"].startswith("narration/n1_")
    files = sorted(p.name for p in (folder / "narration").iterdir())
    assert len(files) == 2 and "n1.mp3" not in files  # replaced audio removed

    patch(client, short_id, [{"op": "delete_narration", "line_id": "n2"}])
    assert len(list((folder / "narration").iterdir())) == 1


def test_style_overrides_are_checked(client):
    short_id, _ = made_short(client)
    ok = {"op": "set_style", "preset_id": "title_pink", "overrides": {"sub_size": 80}}
    assert patch(client, short_id, [ok]).status_code == 200
    for bad in ({"font": "Arial"}, {"sub_color": "&H00FFFFFF,}{\\b1"}, {"sub_size": "80"},
                {"nope": 1}):  # fmt: skip
        r = patch(client, short_id, [{**ok, "overrides": bad}])
        assert (r.status_code, r.json()["error"]) == (422, "invalid_op"), bad
    assert client.get("/api/v1/styles").json()[0]["id"] == "title_pink"


def test_render_stops_when_cancelled(client):
    short_id, folder = made_short(client)
    before = (folder / "preview.mp4").stat().st_mtime_ns
    doc = EditDoc.model_validate(local.read_json(folder / "edit.json"))
    s = get_settings()
    with pytest.raises(render.RenderCancelled):
        render.render(folder, doc, local.read_json(folder / "crop.json"), 9.0, "preview.mp4",
                      s.preview_size, s.preview_crf, lambda f: None,
                      cancelled=lambda: True)  # fmt: skip
    assert (folder / "preview.mp4").stat().st_mtime_ns == before
