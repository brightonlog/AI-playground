import pytest

from app.media import timeline
from app.media.probe import duration_sec, video_size
from app.media.render import crop_x_expr
from app.media.styles import resolve
from app.media.subtitles import build_ass, wrap
from app.schemas.edit import EditDoc
from app.storage import local
from tests.conftest import HAS_FFMPEG
from tests.test_prepare import made_short


def doc(*words, deleted_line=False):
    return EditDoc.model_validate(
        {
            "title": {"text": "제목"},
            "style": {"preset_id": "title_pink"},
            "lines": [
                {"id": "l1", "kind": "speech", "text": "x", "deleted": deleted_line,
                 "words": [{"id": f"w{i}", "text": t, "start_sec": a, "end_sec": b, **extra}
                           for i, (t, a, b, extra) in enumerate(words, start=1)]},
            ],
        }
    )  # fmt: skip


def test_kept_words_cut_deleted_and_trimmed():
    d = doc(("가", 10.0, 10.5, {}), ("나", 11.0, 11.4, {"deleted": True}),
            ("다", 12.0, 12.3, {"trim_gap_after": True}), ("라", 13.0, 13.5, {}))  # fmt: skip
    kept = timeline.kept_words(d)
    # 가 runs to 나's start (not past it), 다 stops at end + 0.15, 라 ends at its end
    assert [(k.start, k.end, k.out_start) for k in kept] == [
        (10.0, 11.0, 0.0),
        (12.0, 12.45, 1.0),
        (13.0, 13.5, 1.45),
    ]
    assert timeline.segments(kept) == [(10.0, 11.0), (12.0, 12.45), (13.0, 13.5)]
    assert timeline.duration(kept) == 1.95
    assert timeline.kept_words(doc(("가", 1, 2, {}), deleted_line=True)) == []


def test_wrap_limits_lines_and_chars():
    words = ["가나다라마바", "사아자차", "카타파하", "가나다", "가나다라마바사아자차카타파하가나다"]
    events = wrap(words, lambda x: x)
    # "가나다라마바 사아자차 카타파하" is exactly 16 chars; the 17+ char word gets its own line
    assert events == [
        [["가나다라마바", "사아자차", "카타파하"], ["가나다"]],
        [["가나다라마바사아자차카타파하가나다"]],
    ]


def test_ass_marks_emphasis_and_title():
    d = doc(("진짜", 1.0, 1.5, {"emphasis": True}), ("좋아요", 1.5, 2.0, {}))
    kept = timeline.kept_words(d)
    ass = build_ass(d, kept, 1.0, resolve("title_pink", {}))
    assert "Dialogue: 1,0:00:00.00,0:00:01.00,Title,,0,0,0,,제목" in ass
    assert r"Sub,,0,0,0,,{\1c&H00E5FF&}진짜{\r} 좋아요" in ass


def test_crop_expression_interpolates():
    crop = {"keyframes": [{"t": 10.0, "x": 100}, {"t": 10.5, "x": 200}]}
    assert crop_x_expr(crop, 10.0) == (
        "lt(t,0.0)*100+gte(t,0.0)*lt(t,0.5)*(100+(100)*(t-0.0)/0.5)+gte(t,0.5)*200"
    )


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")
def test_preview_rendered_and_served(client):
    short_id, folder = made_short(client)
    body = client.get(f"/api/v1/shorts/{short_id}").json()
    assert (body["status"], body["preview_status"], body["preview_version"]) == (
        "editing",
        "ready",
        1,
    )
    preview = local.short_dir(short_id) / "preview.mp4"
    assert video_size(preview) == (540, 960)
    assert 2.5 < duration_sec(preview) < 3.5  # words 10.5 ~ 13.5

    url = f"/api/v1/shorts/{short_id}/files/preview"
    r = client.get(url, headers={"Range": "bytes=0-99"})
    assert (r.status_code, len(r.content), r.headers["content-type"]) == (206, 100, "video/mp4")
    assert "attachment" in client.get(url + "?download=1").headers["content-disposition"]
    r = client.get(f"/api/v1/shorts/{short_id}/files/video")
    assert (r.status_code, r.json()["error"]) == (404, "file_not_found")
    assert client.get(f"/api/v1/shorts/{short_id}/files/etc").status_code == 422
