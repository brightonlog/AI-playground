import json
from pathlib import Path

from app.transcript.captions import hangul_ratio
from app.transcript.sentences import group_sentences, tokens_from_json3

FIXTURES = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIXTURES / name).read_text("utf-8"))


def test_manual_captions():
    sentences = group_sentences(tokens_from_json3(load("captions_manual.json3")))
    assert [s["text"] for s in sentences] == [
        "오늘은 제가 요즘 쓰는 선크림을 소개할게요.",
        "이거 진짜 안 끈적여요!",
        "다음은 립밤",
    ]
    first = sentences[0]
    assert (first["start_sec"], first["end_sec"]) == (1.5, 6.0)
    assert [s["id"] for s in sentences] == ["s1", "s2", "s3"]


def test_auto_captions_clip_overlap_and_split_on_endings():
    sentences = group_sentences(tokens_from_json3(load("captions_auto.json3")))
    assert [s["text"] for s in sentences] == [
        "오늘은 선크림 소개할게요",
        "이거 안 끈적여요",
        "그리고 향도 좋고",
    ]
    # First window (0~5s) overlaps the next line at 2.5s: clipped.
    assert sentences[0]["end_sec"] == 2.5
    for a, b in zip(sentences, sentences[1:], strict=False):
        assert a["end_sec"] <= b["start_sec"]


def test_empty():
    assert group_sentences(tokens_from_json3({})) == []


def test_hangul_ratio():
    assert hangul_ratio(load("captions_manual.json3")) > 0.9
    english = {"events": [{"segs": [{"utf8": "Even when you're going au naturel"}]}]}
    assert hangul_ratio(english) == 0.0
    assert hangul_ratio({}) == 0.0
