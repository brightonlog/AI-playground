from app.generate.corrector import correct_lines
from app.schemas.edit import SpeechLine, Word
from app.transcript.align import align_words


def line(*texts):
    words = [Word(id=f"w{i}", text=t, start_sec=i, end_sec=i + 1)
             for i, t in enumerate(texts, start=1)]  # fmt: skip
    return SpeechLine(id="l1", text=" ".join(texts), words=words)


def test_align_keeps_whisper_word_boundaries():
    # Captions space differently and fix the brand; text outside the section is dropped.
    words = ["라운드렙", "선크림을", "매일바르는데", "좋아요."]
    caption = "어제 말한 라운드랩 선크림을 매일 바르는데 좋아요. 다음은 립밤"
    assert align_words(words, caption) == ["라운드랩", "선크림을", "매일바르는데", "좋아요."]


def test_align_rejects_unrelated_captions():
    assert align_words(["이", "선크림", "진짜"], "다음은 립밤입니다") is None
    assert align_words(["이"], "") is None


def test_manual_captions_win_over_llm(_isolate):
    source, _ = _isolate
    lines = [line("라운드렙", "좋아요.")]
    transcript = {
        "source": "manual",
        "sentences": [{"start_sec": 0.5, "end_sec": 4.0, "text": "라운드랩 좋아요."}],
    }
    assert correct_lines(lines, transcript, {}, []) == "captions"
    assert source.llm.calls == []
    w = lines[0].words[0]
    assert (w.text, w.raw_text, lines[0].text) == ("라운드랩", "라운드렙", "라운드랩 좋아요.")


def test_llm_fixes_when_no_manual_captions(_isolate):
    source, _ = _isolate
    lines = [line("이", "선크림", "진짜", "좋아요.", "매일", "써요.")]
    transcript = {"source": "auto", "sentences": []}
    assert correct_lines(lines, transcript, {"title": "t"}, ["라운드랩 선크림"]) == "llm"
    assert "w5=매일" in source.llm.calls[0] and "라운드랩 선크림" in source.llm.calls[0]
    # unknown id, unchanged text and over-long text are ignored
    assert [(w.text, w.raw_text) for w in lines[0].words if w.raw_text] == [("매일매일", "매일")]


def test_llm_failure_leaves_words(_isolate):
    from app.llm.client import LLMError

    source, _ = _isolate
    source.llm.error = LLMError("down")
    lines = [line("매일")]
    assert correct_lines(lines, {"source": "whisper", "sentences": []}, {}, []) == "llm"
    assert (lines[0].words[0].text, lines[0].words[0].raw_text) == ("매일", None)
