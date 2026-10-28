import pytest

from app.core.errors import JobError
from app.workers.analysis_tasks import run_analysis
from tests.conftest import HAS_FFMPEG

URL = "https://youtu.be/dQw4w9WgXcQ"
needs_ffmpeg = pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")


def create(client, url=URL):
    return client.post("/api/v1/analyses", json={"url": url, "template_id": "celeb_item"})


def test_create_queues_job(client, _isolate):
    _, queued = _isolate
    r = create(client)
    assert r.status_code == 202
    body = r.json()
    assert body["status"] == "queued"
    assert body["id"].startswith("an_")
    assert body["url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert body["source"]["title"] == "t"
    assert queued == [body["id"]]


def test_create_reuses_existing(client):
    first = create(client).json()
    r = create(client, "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert r.status_code == 200
    assert r.json()["id"] == first["id"]


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ({"url": "https://evil.com/x"}, "invalid_url"),
        ({"url": URL, "template_id": "top3"}, "invalid_template"),
    ],
)
def test_create_validation(client, payload, code):
    r = client.post("/api/v1/analyses", json=payload)
    assert (r.status_code, r.json()["error"]) == (422, code)


def test_create_too_long(client, _isolate):
    source, _ = _isolate
    source.info.duration_sec = 7201
    assert create(client).json()["error"] == "video_too_long"


def test_create_unavailable(client, _isolate, monkeypatch):
    source, _ = _isolate

    def boom(url):
        raise JobError("video_unavailable", "연령 제한 영상은 지원하지 않습니다")

    monkeypatch.setattr(source, "get_info", boom)
    r = create(client)
    assert r.status_code == 422
    assert r.json() == {
        "error": "video_unavailable",
        "detail": "연령 제한 영상은 지원하지 않습니다",
    }


def test_create_limit_active_jobs(client, _isolate):
    source, _ = _isolate
    for vid in ("aaaaaaaaaaa", "bbbbbbbbbbb"):
        assert create(client, f"https://youtu.be/{vid}").status_code == 202
    r = create(client, "https://youtu.be/ccccccccccc")
    assert (r.status_code, r.json()["error"]) == (429, "too_many_jobs")


@needs_ffmpeg
def test_pipeline_ready_with_captions(client):
    analysis_id = create(client).json()["id"]
    run_analysis(analysis_id)
    body = client.get(f"/api/v1/analyses/{analysis_id}").json()
    assert (body["status"], body["progress"], body["transcript_source"]) == ("ready", 1.0, "manual")
    assert body["finished_at"].endswith("Z") or "+00:00" in body["finished_at"]

    transcript = client.get(f"/api/v1/analyses/{analysis_id}/transcript").json()
    assert len(transcript["sentences"]) == 3
    window = client.get(
        f"/api/v1/analyses/{analysis_id}/transcript", params={"start_sec": 6.5, "end_sec": 13}
    ).json()
    assert [s["id"] for s in window["sentences"]] == ["s2", "s3"]

    wave = client.get(f"/api/v1/analyses/{analysis_id}/waveform").json()
    assert wave["peaks_per_sec"] == 10 and wave["peaks"]


@needs_ffmpeg
def test_pipeline_auto_captions_warns(client, _isolate):
    source, _ = _isolate
    source.captions.kind = "auto"
    analysis_id = create(client).json()["id"]
    run_analysis(analysis_id)
    body = client.get(f"/api/v1/analyses/{analysis_id}").json()
    assert body["warnings"] == ["auto_captions"]


@needs_ffmpeg
def test_pipeline_without_captions_uses_whisper(client, _isolate):
    source, _ = _isolate
    source.captions = None
    analysis_id = create(client).json()["id"]
    run_analysis(analysis_id)
    body = client.get(f"/api/v1/analyses/{analysis_id}").json()
    assert (body["status"], body["transcript_source"]) == ("ready", "whisper")
    sentences = client.get(f"/api/v1/analyses/{analysis_id}/transcript").json()["sentences"]
    assert [s["text"] for s in sentences] == ["이 선크림 진짜 좋아요.", "매일 써요."]


@needs_ffmpeg
def test_pipeline_no_speech_fails(client, _isolate):
    source, _ = _isolate
    source.captions = None
    source.transcriber.tokens = []
    analysis_id = create(client).json()["id"]
    run_analysis(analysis_id)
    body = client.get(f"/api/v1/analyses/{analysis_id}").json()
    assert (body["status"], body["stage"]) == ("failed", "transcribing")
    assert body["error"]["code"] == "no_speech"


def test_pipeline_unexpected_error_hides_message(client, _isolate, monkeypatch):
    source, _ = _isolate

    def boom(url):
        raise RuntimeError("C:/secret/path sk-key")

    monkeypatch.setattr(source, "fetch_captions", boom)
    analysis_id = create(client).json()["id"]
    run_analysis(analysis_id)
    body = client.get(f"/api/v1/analyses/{analysis_id}").json()
    assert body["status"] == "failed"
    assert body["error"]["code"] == "internal_error"
    assert "secret" not in body["error"]["message"]


def test_artifacts_not_ready(client):
    analysis_id = create(client).json()["id"]
    r = client.get(f"/api/v1/analyses/{analysis_id}/transcript")
    assert (r.status_code, r.json()["error"]) == (409, "transcript_not_ready")
    r = client.get(f"/api/v1/analyses/{analysis_id}/waveform")
    assert (r.status_code, r.json()["error"]) == (409, "waveform_not_ready")


def test_get_unknown_and_bad_ids(client):
    for bad in ("an_zzzzzzzz", "..%2F..%2Fetc", "x"):
        r = client.get(f"/api/v1/analyses/{bad}")
        assert r.status_code == 404
    assert client.get("/api/v1/analyses/an_zzzzzzzz/transcript").status_code == 404


def test_delete(client):
    analysis_id = create(client).json()["id"]
    r = client.delete(f"/api/v1/analyses/{analysis_id}")
    assert (r.status_code, r.json()["error"]) == (409, "analysis_running")

    run_analysis(analysis_id)  # fails or finishes; either way no longer active
    assert client.delete(f"/api/v1/analyses/{analysis_id}").status_code == 204
    assert client.get(f"/api/v1/analyses/{analysis_id}").status_code == 404


def test_list_pagination_and_filter(client, _isolate):
    ids = []
    for vid in ("aaaaaaaaaaa", "bbbbbbbbbbb"):
        ids.append(create(client, f"https://youtu.be/{vid}").json()["id"])
        run_analysis(ids[-1])  # frees the active-job slot
    ids.append(create(client, "https://youtu.be/ccccccccccc").json()["id"])

    page = client.get("/api/v1/analyses", params={"limit": 2}).json()
    assert [a["id"] for a in page["items"]] == ids[::-1][:2]
    rest = client.get("/api/v1/analyses", params={"limit": 2, "cursor": page["next_cursor"]}).json()
    assert [a["id"] for a in rest["items"]] == [ids[0]]
    assert rest["next_cursor"] is None

    queued = client.get("/api/v1/analyses", params={"status": "queued"}).json()
    assert [a["id"] for a in queued["items"]] == [ids[2]]

    r = client.get("/api/v1/analyses", params={"cursor": "an_zzzzzzzz"})
    assert r.json()["error"] == "invalid_cursor"


def test_enqueue_failure_marks_failed(client, monkeypatch):
    from app.workers import analysis_tasks

    def down(_id):
        raise ConnectionError("redis down")

    monkeypatch.setattr(analysis_tasks, "enqueue", down)
    r = create(client)
    assert (r.status_code, r.json()["error"]) == (503, "queue_unavailable")
    items = client.get("/api/v1/analyses").json()["items"]
    assert [a["status"] for a in items] == ["failed"]  # not a stuck "queued" row
    assert create(client).status_code == 503  # failed rows are not reused


@needs_ffmpeg
def test_tag_only_captions_fall_back_to_whisper(client, _isolate):
    source, _ = _isolate
    source.captions.json3 = {
        "events": [{"tStartMs": 0, "dDurationMs": 5000, "segs": [{"utf8": "[음악]"}]}]
    }
    analysis_id = create(client).json()["id"]
    run_analysis(analysis_id)
    assert client.get(f"/api/v1/analyses/{analysis_id}").json()["transcript_source"] == "whisper"


@needs_ffmpeg
def test_pipeline_writes_mentions(client, _isolate):
    from app.storage import local

    analysis_id = create(client).json()["id"]
    run_analysis(analysis_id)
    mentions = local.read_json(local.analysis_dir(analysis_id) / "mentions.json")
    assert mentions["source"] == "llm"
    assert len(mentions["mentions"]) == 2


@needs_ffmpeg
def test_pipeline_llm_failure_warns(client, _isolate):
    from app.llm.client import LLMError

    source, _ = _isolate
    source.llm.error = LLMError("down")
    analysis_id = create(client).json()["id"]
    run_analysis(analysis_id)
    body = client.get(f"/api/v1/analyses/{analysis_id}").json()
    assert body["status"] == "ready"
    assert body["warnings"] == ["llm_fallback"]
