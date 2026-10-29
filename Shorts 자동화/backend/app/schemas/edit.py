"""edit.json (spec 6). Times are source-video seconds."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


class Word(BaseModel):
    id: str
    text: str
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
