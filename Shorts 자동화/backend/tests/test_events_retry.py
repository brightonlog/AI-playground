import json

import pytest
from sqlalchemy import update

from app.core.config import get_settings
from app.db.models import Analysis
from app.db.session import SessionLocal
from app.services.events import sse
from app.workers.analysis_tasks import run_analysis


def create(client):
    r = client.post("/api/v1/analyses", json={"url": "https://youtu.be/dQw4w9WgXcQ"})
    return r.json()["id"]


def set_status(analysis_id, **values):
    with SessionLocal() as db:
        db.execute(update(Analysis).where(Analysis.id == analysis_id).values(**values))
        db.commit()


def read_events(lines, until=("done", "failed")):
    events, event = [], None
    for line in lines:
        if line.startswith("event: "):
            event = line[len("event: ") :]
        elif line.startswith("data: "):
            events.append((event, json.loads(line[len("data: ") :])))
            if event in until:
                break
    return events


@pytest.fixture
def fast_heartbeat(monkeypatch):
    monkeypatch.setattr(get_settings(), "sse_heartbeat_sec", 0.05)


def test_sse_format():
    assert sse("progress", {"p": 0.5}) == 'event: progress\ndata: {"p": 0.5}\n\n'


def test_events_unknown_404(client):
    r = client.get("/api/v1/analyses/an_zzzzzzzz/events")
    assert (r.status_code, r.json()["error"]) == (404, "not_found")


def test_events_terminal_closes(client):
    analysis_id = create(client)
    set_status(analysis_id, status="ready")
    with client.stream("GET", f"/api/v1/analyses/{analysis_id}/events") as r:
        assert r.headers["content-type"].startswith("text/event-stream")
        assert read_events(r.iter_lines()) == [("done", {"status": "ready"})]


def test_events_progress_then_failed(client, fast_heartbeat):
    analysis_id = create(client)
    set_status(analysis_id, status="fetching", stage="fetching")
    with client.stream("GET", f"/api/v1/analyses/{analysis_id}/events") as r:
        lines = r.iter_lines()
        first = read_events(lines, until=("progress",))
        assert first == [("progress", {"stage": "fetching", "progress": 0.0})]
        set_status(analysis_id, status="failed", error_code="download_failed", error_message="x")
        rest = read_events(lines)
    assert rest[-1] == ("failed", {"error": "download_failed", "detail": "x"})


def test_retry_requeues_failed(client, _isolate):
    _, queued = _isolate
    analysis_id = create(client)
    r = client.post(f"/api/v1/analyses/{analysis_id}/retry")
    assert (r.status_code, r.json()["error"]) == (409, "invalid_state")

    set_status(analysis_id, status="failed", stage="transcribing", error_code="no_speech")
    r = client.post(f"/api/v1/analyses/{analysis_id}/retry")
    assert r.status_code == 202
    body = r.json()
    assert (body["status"], body["stage"], body["retry_count"], body["error"]) == (
        "queued",
        "transcribing",
        1,
        None,
    )
    assert queued == [analysis_id, analysis_id]


def test_retry_limit(client):
    analysis_id = create(client)
    set_status(analysis_id, status="failed", retry_count=3)
    r = client.post(f"/api/v1/analyses/{analysis_id}/retry")
    assert (r.status_code, r.json()["error"]) == (409, "retry_limit")


@pytest.mark.skipif(not __import__("shutil").which("ffmpeg"), reason="ffmpeg not installed")
def test_retry_resumes_after_failure(client, _isolate, monkeypatch):
    source, _ = _isolate
    calls = []
    real_download = source.download_audio

    def flaky(url, dest, on_progress):
        calls.append(url)
        if len(calls) == 1:
            from app.core.errors import JobError

            raise JobError("download_failed", "오디오를 받지 못했습니다")
        real_download(url, dest, on_progress)

    monkeypatch.setattr(source, "download_audio", flaky)
    fetch_captions = []
    real_captions = source.fetch_captions
    monkeypatch.setattr(
        source, "fetch_captions", lambda u: fetch_captions.append(u) or real_captions(u)
    )

    analysis_id = create(client)
    run_analysis(analysis_id)
    assert client.get(f"/api/v1/analyses/{analysis_id}").json()["status"] == "failed"

    client.post(f"/api/v1/analyses/{analysis_id}/retry")
    run_analysis(analysis_id)
    assert client.get(f"/api/v1/analyses/{analysis_id}").json()["status"] == "ready"
    assert len(fetch_captions) == 1  # transcript.json from the first run was reused
