"""ASS subtitles: title on top, speech lines at the bottom (spec 6: 16 chars x 2 lines)."""

from collections.abc import Callable
from typing import Any, TypeVar

from app.core.config import get_settings
from app.media.timeline import Kept, speech_lines
from app.schemas.edit import EditDoc

T = TypeVar("T")

_STYLE_FORMAT = (
    "Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
    "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
    "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding"
)


def wrap(items: list[T], text: Callable[[T], str]) -> list[list[list[T]]]:
    """Greedy word wrap into events of at most `subtitle_max_lines` lines of
    `subtitle_line_chars` characters. A word longer than a line gets a line of its own."""
    s = get_settings()
    events: list[list[list[T]]] = []
    lines: list[list[T]] = []
    cur: list[T] = []
    for item in items:
        if cur and len(" ".join(text(x) for x in [*cur, item])) > s.subtitle_line_chars:
            lines.append(cur)
            cur = []
            if len(lines) == s.subtitle_max_lines:
                events.append(lines)
                lines = []
        cur.append(item)
    if cur:
        lines.append(cur)
    if lines:
        events.append(lines)
    return events


def _ts(sec: float) -> str:
    cs = max(0, round(sec * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def _escape(text: str) -> str:
    return text.replace("\\", "＼").replace("{", "｛").replace("}", "｝").replace("\n", " ")


def _override(color: str) -> str:
    return f"&H{color[-6:]}&"  # style colors carry alpha; inline overrides do not


def _end(k: Kept) -> float:
    return k.out_start + (k.end - k.start)


def _speech_events(doc: EditDoc, kept: list[Kept], style: dict[str, Any]) -> list[str]:
    emphasis = _override(style["emphasis_color"])
    events = []
    for line in speech_lines(doc):
        words = [k for k in kept if k.line_id == line.id]
        if not words:
            continue
        if line.display_text:  # hand-edited text: no per-word timing, show it over the line
            chunks = wrap(line.display_text.split(), lambda x: x)
            step = (_end(words[-1]) - words[0].out_start) / len(chunks)
            for i, text_chunk in enumerate(chunks):
                body = r"\N".join(_escape(" ".join(ln)) for ln in text_chunk)
                start = words[0].out_start + step * i
                events.append(f"Dialogue: 0,{_ts(start)},{_ts(start + step)},Sub,,0,0,0,,{body}")
            continue
        for chunk in wrap(words, lambda k: k.word.text):
            body = r"\N".join(
                " ".join(
                    f"{{\\1c{emphasis}}}{_escape(k.word.text)}{{\\r}}"
                    if k.word.emphasis
                    else _escape(k.word.text)
                    for k in ln
                )
                for ln in chunk
            )
            start, end = chunk[0][0].out_start, _end(chunk[-1][-1])
            events.append(f"Dialogue: 0,{_ts(start)},{_ts(end)},Sub,,0,0,0,,{body}")
    return events


def build_ass(doc: EditDoc, kept: list[Kept], duration: float, style: dict[str, Any]) -> str:
    width, height = get_settings().final_size
    st = style
    styles = [
        f"Style: Title,{st['font']},{st['title_size']},{st['title_color']},&H000000FF,"
        f"{st['title_box']},&H00000000,1,0,0,0,100,100,0,0,3,16,0,8,60,60,{st['title_margin_v']},1",
        f"Style: Sub,{st['font']},{st['sub_size']},{st['sub_color']},&H000000FF,"
        f"{st['sub_outline']},&H00000000,1,0,0,0,100,100,0,0,1,{st['sub_outline_px']},0,2,"
        f"60,60,{st['sub_margin_v']},1",
    ]
    events = []
    if doc.title.visible and doc.title.text:
        lines = [ln for ev in wrap(doc.title.text.split(), lambda x: x) for ln in ev]
        title = r"\N".join(_escape(" ".join(ln)) for ln in lines)
        events.append(f"Dialogue: 1,{_ts(0)},{_ts(duration)},Title,,0,0,0,,{title}")
    events += _speech_events(doc, kept, style)
    return "\n".join(
        [
            "[Script Info]",
            "ScriptType: v4.00+",
            f"PlayResX: {width}",
            f"PlayResY: {height}",
            "WrapStyle: 2",
            "",
            "[V4+ Styles]",
            f"Format: {_STYLE_FORMAT}",
            *styles,
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
            *events,
            "",
        ]
    )
