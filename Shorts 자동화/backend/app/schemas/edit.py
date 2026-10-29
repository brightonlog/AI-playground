"""edit.json (spec 6). Times are source-video seconds."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


class Word(BaseModel):
    id: str
    text: str
    raw_text: str | None = None  # speech-to-text output before correction
    start_sec: float
    end_sec: float
    deleted: bool = False
    trim_gap_after: bool = False
    emphasis: bool = False


class SpeechLine(BaseModel):
    id: str
    kind: Literal["speech"] = "speech"
    deleted: bool = False
    text: str
    display_text: str | None = None
    words: list[Word]


class NarrationLine(BaseModel):
    id: str
    kind: Literal["narration"] = "narration"
    text: str
    anchor_line_id: str
    audio_path: str
    audio_sec: float
    voice_id: str = "default"


class Title(BaseModel):
    text: str
    visible: bool = True


class Style(BaseModel):
    preset_id: str
    overrides: dict[str, Any] = {}


class Suggestion(BaseModel):
    id: str
    type: str
    word_ids: list[str]
    reason: str


class EditDoc(BaseModel):
    version: int = 1
    title: Title
    lines: list[Annotated[SpeechLine | NarrationLine, Field(discriminator="kind")]]
    style: Style
    pending_suggestions: list[Suggestion] = []


# PATCH /edit operations (spec 6 편집 연산). Text limits match config.
class DeleteWords(BaseModel):
    op: Literal["delete_words", "restore_words"]
    word_ids: list[str] = Field(min_length=1)


class LineOp(BaseModel):
    op: Literal["delete_line", "restore_line", "delete_narration"]
    line_id: str


class RestoreAll(BaseModel):
    op: Literal["restore_all"]


class SetDisplayText(BaseModel):
    op: Literal["set_display_text"]
    line_id: str
    text: str | None = Field(default=None, max_length=100)  # empty or null clears it


class SplitLine(BaseModel):
    op: Literal["split_line"]
    line_id: str
    word_id: str  # first word of the new line


class SetWordText(BaseModel):
    op: Literal["set_word_text"]
    word_id: str
    text: str = Field(min_length=1, max_length=20)


class SetTitle(BaseModel):
    op: Literal["set_title"]
    text: str = Field(max_length=30)
    visible: bool = True


class SetNarration(BaseModel):
    op: Literal["set_narration"]
    line_id: str
    text: str = Field(min_length=1, max_length=40)
    anchor_line_id: str | None = None


class AddNarration(BaseModel):
    op: Literal["add_narration"]
    text: str = Field(min_length=1, max_length=40)
    anchor_line_id: str


class ApplySuggestions(BaseModel):
    op: Literal["apply_suggestions"]
    suggestion_ids: list[str] = Field(min_length=1)


class SetStyle(BaseModel):
    op: Literal["set_style"]
    preset_id: str
    overrides: dict[str, Any] = {}


EditOp = Annotated[
    DeleteWords | LineOp | RestoreAll | SetDisplayText | SplitLine | SetWordText | SetTitle
    | SetNarration | AddNarration | ApplySuggestions | SetStyle,
    Field(discriminator="op"),
]  # fmt: skip


class EditPatch(BaseModel):
    base_version: int
    ops: list[EditOp] = Field(min_length=1, max_length=200)


class EditOut(BaseModel):
    edit: EditDoc
    duration_sec: float
    out_start_sec: float  # source time where the output starts


class EditResult(BaseModel):
    version: int
    duration_sec: float
    preview_status: str


class SilenceRequest(BaseModel):
    type: Literal["silence"]
    min_gap_sec: float = Field(default=0.5, ge=0.2, le=5)


class FillerRequest(BaseModel):
    type: Literal["filler"]


CutRequest = Annotated[SilenceRequest | FillerRequest, Field(discriminator="type")]


class CutResult(BaseModel):
    version: int
    suggestions: list[Suggestion]
