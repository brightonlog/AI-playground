"""Apply PATCH /edit operations to a copy of an edit (spec 6 편집 연산)."""

import hashlib
from pathlib import Path

from app.generate import tts
from app.media import styles
from app.media.probe import duration_sec
from app.schemas.edit import (
    AddNarration,
    ApplySuggestions,
    DeleteWords,
    EditDoc,
    EditOp,
    LineOp,
    NarrationLine,
    RestoreAll,
    SetDisplayText,
    SetNarration,
    SetStyle,
    SetTitle,
    SetWordText,
    SpeechLine,
    SplitLine,
    Word,
)


class OpError(ValueError):
    """An operation refers to something that does not exist or is not allowed."""


def _retext(line: SpeechLine) -> None:
    line.text = " ".join(w.text for w in line.words)


def _next_id(doc: EditDoc, prefix: str) -> str:
    nums = [int(x.id[1:]) for x in doc.lines if x.id[0] == prefix and x.id[1:].isdigit()]
    return f"{prefix}{max(nums, default=0) + 1}"


class Editor:
    def __init__(self, doc: EditDoc, folder: Path) -> None:
        self.doc = doc.model_copy(deep=True)
        self.folder = folder

    def speech(self, line_id: str) -> SpeechLine:
        for x in self.doc.lines:
            if x.id == line_id and isinstance(x, SpeechLine):
                return x
        raise OpError(f"없는 문장입니다: {line_id}")

    def narration(self, line_id: str) -> NarrationLine:
        for x in self.doc.lines:
            if x.id == line_id and isinstance(x, NarrationLine):
                return x
        raise OpError(f"없는 나레이션입니다: {line_id}")

    def word(self, word_id: str) -> Word:
        for x in self.doc.lines:
            for w in x.words if isinstance(x, SpeechLine) else []:
                if w.id == word_id:
                    return w
        raise OpError(f"없는 단어입니다: {word_id}")

    def _speak(self, line_id: str, text: str) -> tuple[str, float]:
        # Name by content so a failed patch never changes audio the saved edit points to.
        digest = hashlib.sha256(text.encode()).hexdigest()[:8]
        path = f"narration/{line_id}_{digest}.mp3"
        tts.speak(text, "default", self.folder / path)
        return path, duration_sec(self.folder / path)

    def _place_before(self, narration: NarrationLine, anchor_id: str) -> None:
        anchor = self.speech(anchor_id)
        lines = [x for x in self.doc.lines if x is not narration]
        lines.insert(lines.index(anchor), narration)
        self.doc.lines = lines

    def apply(self, op: EditOp) -> None:
        match op:
            case DeleteWords():
                for wid in op.word_ids:
                    self.word(wid).deleted = op.op == "delete_words"
            case LineOp(op="delete_line" | "restore_line"):
                self.speech(op.line_id).deleted = op.op == "delete_line"
            case LineOp(op="delete_narration"):
                narration = self.narration(op.line_id)
                self.doc.lines = [x for x in self.doc.lines if x is not narration]
            case RestoreAll():
                for line in self.doc.lines:
                    if isinstance(line, SpeechLine):
                        line.deleted = False
                        for w in line.words:
                            w.deleted = False
            case SetDisplayText():
                self.speech(op.line_id).display_text = (op.text or "").strip() or None
            case SplitLine():
                self._split(op)
            case SetWordText():
                self._set_word_text(op)
            case SetTitle():
                self.doc.title.text, self.doc.title.visible = op.text.strip(), op.visible
            case SetNarration():
                narration = self.narration(op.line_id)
                if op.text.strip() != narration.text:
                    narration.text = op.text.strip()
                    narration.audio_path, narration.audio_sec = self._speak(
                        narration.id, narration.text
                    )
                if op.anchor_line_id:
                    narration.anchor_line_id = op.anchor_line_id
                    self._place_before(narration, op.anchor_line_id)
            case AddNarration():
                self.speech(op.anchor_line_id)
                nid = _next_id(self.doc, "n")
                path, sec = self._speak(nid, op.text.strip())
                narration = NarrationLine(id=nid, text=op.text.strip(),
                                          anchor_line_id=op.anchor_line_id,
                                          audio_path=path, audio_sec=sec)  # fmt: skip
                self._place_before(narration, op.anchor_line_id)
            case ApplySuggestions():
                self._apply_suggestions(op)
            case SetStyle():
                try:
                    overrides = styles.clean_overrides(op.preset_id, op.overrides)
                except ValueError as exc:
                    raise OpError(str(exc)) from exc
                self.doc.style.preset_id, self.doc.style.overrides = op.preset_id, overrides

    def _split(self, op: SplitLine) -> None:
        line = self.speech(op.line_id)
        index = next((i for i, w in enumerate(line.words) if w.id == op.word_id), 0)
        if index == 0:
            raise OpError("문장의 두 번째 단어부터 나눌 수 있습니다")
        new = SpeechLine(id=_next_id(self.doc, "l"), text="", deleted=line.deleted,
                         words=line.words[index:])  # fmt: skip
        line.words, line.display_text = line.words[:index], None
        _retext(line)
        _retext(new)
        self.doc.lines.insert(self.doc.lines.index(line) + 1, new)

    def _set_word_text(self, op: SetWordText) -> None:
        word, text = self.word(op.word_id), op.text.strip()
        if not text:
            raise OpError("단어를 비울 수 없습니다. 지우려면 단어 삭제를 쓰세요")
        if word.raw_text is None and text != word.text:
            word.raw_text = word.text
        word.text = text
        if word.raw_text == text:  # back to what speech-to-text heard
            word.raw_text = None
        for line in self.doc.lines:
            if isinstance(line, SpeechLine) and any(w is word for w in line.words):
                _retext(line)

    def _apply_suggestions(self, op: ApplySuggestions) -> None:
        pending = {s.id: s for s in self.doc.pending_suggestions}
        for sid in op.suggestion_ids:
            if sid not in pending:
                raise OpError(f"없는 추천입니다: {sid}")
            suggestion = pending.pop(sid)
            for wid in suggestion.word_ids:
                if suggestion.type == "silence":  # cut the pause after the word
                    self.word(wid).trim_gap_after = True
                else:
                    self.word(wid).deleted = True
        self.doc.pending_suggestions = list(pending.values())
