import pytest

from app.llm.client import AnthropicLLM, LLMError
from app.recommend.extract import MentionList, extract_mentions
from app.recommend.keywords import keyword_mentions

META = {"title": "라운드랩 선크림 리뷰", "description": "x" * 5000, "tags": ["선크림"]}
SENTENCES = [  # fmt: skip
    {
        "id": "s1",
        "start_sec": 1.5,
        "end_sec": 6.0,
        "text": "오늘은 제가 요즘 쓰는 선크림을 소개할게요.",
    },
    {"id": "s2", "start_sec": 6.0, "end_sec": 9.0, "text": "이거 진짜 안 끈적여요!"},
    {"id": "s3", "start_sec": 12.0, "end_sec": 14.0, "text": "립밤 바르면 진짜 추천해요"},
]


def test_llm_output_is_cleaned(_isolate):
    result = extract_mentions(META, SENTENCES)
    assert result["source"] == "llm"
    assert result["mentions"] == [
        {"sentence_id": "s1", "product": "톤업 선크림", "brand": "라운드랩",
         "category": "선크림", "recommend_strength": 0.5, "usage": False},
        {"sentence_id": "s2", "product": "톤업 선크림", "brand": "라운드랩",
         "category": "선크림", "recommend_strength": 1.0, "usage": True},
    ]  # fmt: skip


def test_prompt_input_has_hints_and_ids(_isolate):
    source, _ = _isolate
    extract_mentions(META, SENTENCES)
    user = source.llm.calls[0]
    assert "제목: 라운드랩 선크림 리뷰" in user
    assert "s2\t6.0\t이거 진짜 안 끈적여요!" in user
    assert "x" * 1501 not in user  # description is truncated


def test_llm_failure_falls_back_to_keywords(_isolate):
    source, _ = _isolate
    source.llm.error = LLMError("api error: RateLimitError")
    result = extract_mentions(META, SENTENCES)
    assert (result["source"], result["model"]) == ("keywords", None)
    assert [m["sentence_id"] for m in result["mentions"]] == ["s1", "s3"]


def test_keyword_rules():
    [sun, lip] = keyword_mentions([SENTENCES[0], SENTENCES[2]])
    assert (sun["product"], sun["usage"], sun["recommend_strength"]) == ("선크림", False, 0.2)
    assert (lip["product"], lip["usage"], lip["recommend_strength"]) == ("립밤", True, 0.6)


def test_missing_key_raises_without_network():
    with pytest.raises(LLMError, match="ANTHROPIC_API_KEY"):
        AnthropicLLM().parse("s", "u", MentionList)
