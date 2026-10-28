import pytest

from app.recommend.candidates import Candidate, _group, build_candidates
from app.recommend.rank import iou, recommend
from app.recommend.signals import length_fit
from app.recommend.tags import make_tags


def make_sentences(n, sec=4.0, gap=0.0, text="이 제품 진짜 좋아요 매일 써요"):
    out, t = [], 0.0
    for i in range(n):
        out.append({"id": f"s{i + 1}", "start_sec": t, "end_sec": t + sec, "text": text})
        t += sec + gap
    return out


def mention(i, product, brand=None, strength=0.5, usage=False):
    return {"sentence_id": f"s{i}", "product": product, "brand": brand,
            "category": "선크림", "recommend_strength": strength, "usage": usage}  # fmt: skip


def test_length_fit():
    assert [length_fit(x) for x in (29.9, 30, 32.5, 35, 55, 57.5, 60, 60.1)] == [
        0.0, 0.5, 0.75, 1.0, 1.0, 0.75, 0.5, 0.0
    ]  # fmt: skip


def test_group_allows_one_empty_sentence_between():
    assert _group({1: "a", 3: "a", 6: "a"}) == [(1, 3, "a"), (6, 6, "a")]
    assert _group({1: "a", 2: "b", 3: "a"}) == [(1, 1, "a"), (2, 2, "b"), (3, 3, "a")]


def test_candidates_fit_30_to_60_and_prefer_following_sentences():
    sentences = make_sentences(40)
    [c] = build_candidates(sentences, {10: "a"}, duration_sec=160)
    # One mention + 1 context sentence each side = 12s, grown forward to >= 30s.
    assert c.first == 9 and c.last == 16
    assert 30 <= c.duration_sec <= 60
    assert (c.start_sec, c.end_sec) == (35.8, 68.2)  # 0.2s padding


def test_long_run_is_split_at_sentence_boundaries():
    sentences = make_sentences(40)
    cands = build_candidates(sentences, {i: "a" for i in range(1, 30)}, duration_sec=160)
    assert len(cands) >= 2
    assert all(30 <= c.duration_sec <= 60 for c in cands)


def test_short_video_has_no_candidates():
    assert build_candidates(make_sentences(5), {1: "a"}, duration_sec=20) == []


def test_iou():
    a = Candidate(0, 0, "a", 0, 40)
    assert iou(a, Candidate(0, 0, "a", 40, 80)) == 0
    assert iou(a, Candidate(0, 0, "a", 20, 60)) == pytest.approx(20 / 60)


def test_tags_ranked_by_margin_and_capped():
    signals = {"product_specific": 1.0, "recommend_strength": 0.95, "usage": 0.35,
               "density": 0.9, "continuity": 1.0, "length_fit": 1.0}  # fmt: skip
    codes = [code for code, _ in make_tags(signals, "라운드랩")]
    assert codes == ["brand_mention", "strong_recommend"]  # 0.4 and 0.25 beat 0.2, 0.2, 0.05
    assert make_tags({**signals, "product_specific": 0.6}, None)[0][0] == "strong_recommend"


def test_recommend_end_to_end():
    sentences = make_sentences(80, gap=0.3)
    mentions = [
        mention(5, "톤업 선크림", "라운드랩", 0.9, usage=True),
        mention(6, "톤업 선크림", "라운드랩", 0.6, usage=True),
        mention(8, "톤업 선크림", "라운드랩", 0.5),
        mention(30, "립밤", None, 0.3),
        mention(31, "립 밤", None, 0.4),  # same product, different spacing
        mention(60, "쿠션", "클리오", 0.7),
        mention(61, "쿠션", "클리오", 0.7, usage=True),
    ]
    signals_doc, recs = recommend(sentences, mentions, duration_sec=400)
    items = recs["items"]
    assert recs["scorer_version"] == signals_doc["scorer_version"] == "rules-v1"
    assert 1 <= len(items) <= 3
    assert [i["rank"] for i in items] == list(range(1, len(items) + 1))
    assert all(30 <= i["duration_sec"] <= 60 for i in items)
    assert [i["score"] for i in items] == sorted((i["score"] for i in items), reverse=True)
    for a in items:
        for b in items:
            if a is not b:
                ca = Candidate(0, 0, "", a["start_sec"], a["end_sec"])
                cb = Candidate(0, 0, "", b["start_sec"], b["end_sec"])
                assert iou(ca, cb) <= 0.3
    top = items[0]
    assert top["products"][0] == {
        "product": "톤업 선크림",
        "brand": "라운드랩",
        "category": "선크림",
    }
    assert "brand_mention" in top["tags"]
    assert set(top["signals"]) == {"product_specific", "recommend_strength", "usage",
                                   "density", "continuity", "length_fit"}  # fmt: skip
    # Every candidate is logged with its signals; the picked ones carry their rank.
    assert {c["selected_rank"] for c in signals_doc["candidates"]} >= {1}
    assert len(signals_doc["candidates"]) >= len(items)


def test_recommend_without_mentions():
    signals_doc, recs = recommend(make_sentences(20), [], duration_sec=80)
    assert recs["items"] == [] and signals_doc["candidates"] == []
