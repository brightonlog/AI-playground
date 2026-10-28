import pytest
from sqlalchemy import select, update

from app.core.errors import JobError
from app.db.models import Analysis, SelectionLog, Short
from app.db.session import SessionLocal
from app.storage import local
from app.workers.analysis_tasks import run_analysis
from app.workers.short_tasks import run_short
from tests.conftest import HAS_FFMPEG

pytestmark = pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")


def ready_analysis(client, vid="dQw4w9WgXcQ"):
    analysis_id = client.post("/api/v1/analyses", json={"url": f"https://youtu.be/{vid}"}).json()[
        "id"
    ]
    run_analysis(analysis_id)
    return analysis_id


def create_short(client, analysis_id, start=10.0, end=40.0, rank=1):
    return client.post(
        "/api/v1/shorts",
        json={"analysis_id": analysis_id, "start_sec": start, "end_sec": end,
              "recommendation_rank": rank},
    )  # fmt: skip


def test_create_queues_and_logs_selection(client, _isolate):
    _, queued = _isolate
    analysis_id = ready_analysis(client)
    r = create_short(client, analysis_id)
    assert r.status_code == 202
    body = r.json()
    assert body["id"].startswith("sh_")
    assert (body["status"], body["start_sec"], body["end_sec"]) == ("queued", 10.0, 40.0)
    assert queued[-1] == body["id"]
    with SessionLocal() as db:
        log = db.scalars(select(SelectionLog)).one()
    assert (log.short_id, log.analysis_id, log.recommendation_rank) == (body["id"], analysis_id, 1)
    assert (log.chosen_start_sec, log.chosen_end_sec, log.scorer_version) == (
        10.0,
        40.0,
        "rules-v1",
    )


@pytest.mark.parametrize(
    ("start", "end"),
    [(10, 20), (10, 80), (590, 610)],  # too short, too long, past the 600s video
)
def test_create_rejects_bad_range(client, start, end):
    analysis_id = ready_analysis(client)
    r = create_short(client, analysis_id, start, end)
    assert (r.status_code, r.json()["error"]) == (422, "invalid_range")


def test_create_requires_ready_analysis(client):
    analysis_id = client.post(
        "/api/v1/analyses", json={"url": "https://youtu.be/dQw4w9WgXcQ"}
    ).json()["id"]
    r = create_short(client, analysis_id)
    assert (r.status_code, r.json()["error"]) == (409, "analysis_not_ready")
    assert create_short(client, "an_zzzzzzzz").status_code == 404


def test_shorts_count_toward_job_cap(client):
    analysis_id = ready_analysis(client)
    assert create_short(client, analysis_id).status_code == 202
    assert create_short(client, analysis_id, 50, 80).status_code == 202
    r = create_short(client, analysis_id, 90, 120)
    assert (r.status_code, r.json()["error"]) == (429, "too_many_jobs")


def test_pipeline_downloads_section_with_margin(client, _isolate):
    source, _ = _isolate
    analysis_id = ready_analysis(client)
    short_id = create_short(client, analysis_id, 0.5, 30).json()["id"]
    run_short(short_id)
    body = client.get(f"/api/v1/shorts/{short_id}").json()
    assert (body["status"], body["progress"]) == ("editing", 1.0)
    assert source.sections == [(0.0, 31.0)]  # 1s margin, clipped at the video start
    assert (local.short_dir(short_id) / "section.mp4").exists()
    with SessionLocal() as db:
        assert db.get(Short, short_id).section_offset_sec == 0.0


def test_download_failure_then_retry(client, _isolate):
    source, queued = _isolate
    source.section_error = JobError("download_failed", "선택 구간 영상을 받지 못했습니다")
    analysis_id = ready_analysis(client)
    short_id = create_short(client, analysis_id).json()["id"]
    run_short(short_id)
    body = client.get(f"/api/v1/shorts/{short_id}").json()
    assert (body["status"], body["stage"], body["error"]["code"]) == (
        "failed",
        "downloading",
        "download_failed",
    )

    r = client.post(f"/api/v1/shorts/{short_id}/retry")
    assert (r.status_code, r.json()["retry_count"]) == (202, 1)
    assert queued[-1] == short_id
    run_short(short_id)
    assert client.get(f"/api/v1/shorts/{short_id}").json()["status"] == "editing"


def test_events_report_editing_as_done(client):
    analysis_id = ready_analysis(client)
    short_id = create_short(client, analysis_id).json()["id"]
    run_short(short_id)
    with client.stream("GET", f"/api/v1/shorts/{short_id}/events") as r:
        lines = [line for line in r.iter_lines() if line]
    assert lines == ["event: done", 'data: {"status": "editing"}']


def test_delete_analysis_removes_shorts_keeps_logs(client):
    analysis_id = ready_analysis(client)
    short_id = create_short(client, analysis_id).json()["id"]
    r = client.delete(f"/api/v1/analyses/{analysis_id}")
    assert (r.status_code, r.json()["error"]) == (409, "short_running")

    run_short(short_id)
    assert client.delete(f"/api/v1/analyses/{analysis_id}").status_code == 204
    assert client.get(f"/api/v1/shorts/{short_id}").status_code == 404
    with SessionLocal() as db:
        log = db.scalars(select(SelectionLog)).one()
        assert (log.analysis_id, log.short_id, log.video_id) == (None, None, "dQw4w9WgXcQ")
        assert db.get(Analysis, analysis_id) is None


def test_missing_analysis_fails_cleanly(client):
    analysis_id = ready_analysis(client)
    short_id = create_short(client, analysis_id).json()["id"]
    with SessionLocal() as db:  # simulate the analysis row vanishing mid-queue
        db.execute(update(Short).where(Short.id == short_id).values(analysis_id="an_aaaaaaaa"))
        db.commit()
    run_short(short_id)
    assert client.get(f"/api/v1/shorts/{short_id}").json()["error"]["code"] == "analysis_missing"
