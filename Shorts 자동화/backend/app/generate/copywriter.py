"""Draft title and narration (spec 8 문구 생성): one LLM call, video title on failure."""

import logging
from typing import Any

from pydantic import BaseModel

from app.core.config import get_settings
from app.generate import load_prompt
from app.llm import client as llm

log = logging.getLogger(__name__)


class NarrationDraft(BaseModel):
    anchor_line_id: str
    text: str


class DraftCopy(BaseModel):
    title: str
    narrations: list[NarrationDraft]


def _system() -> str:
    s = get_settings()
    return load_prompt("draft_copy").format(
        title_max=s.title_max_chars,
        narration_max=s.narration_max_count,
        narration_chars=s.narration_max_chars,
    )


def _user_message(source: dict[str, Any], products: list[str], lines: list[dict[str, Any]]) -> str:
    head = [
        f"원본 제목: {source.get('title', '')}",
        f"채널: {source.get('channel', '')}",
        f"제품: {', '.join(products) or '없음'}",
    ]
    return "\n".join(head) + "\n\n## 대사\n" + "\n".join(f"{x['id']}\t{x['text']}" for x in lines)


def _clean(raw: DraftCopy, line_ids: list[str]) -> dict[str, Any]:
    s = get_settings()
    narrations: list[dict[str, str]] = []
    for n in raw.narrations:
        text = n.text.strip()[: s.narration_max_chars]
        used = {x["anchor_line_id"] for x in narrations}
        if text and n.anchor_line_id in line_ids and n.anchor_line_id not in used:
            narrations.append({"anchor_line_id": n.anchor_line_id, "text": text})
    return {
        "title": raw.title.strip()[: s.title_max_chars],
        "narrations": narrations[: s.narration_max_count],
    }


def draft_copy(
    source: dict[str, Any], products: list[str], lines: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """`{title, narrations: [{anchor_line_id, text}]}`, or None when the LLM call failed."""
    try:
        result = llm.get_llm().parse(_system(), _user_message(source, products, lines), DraftCopy)
    except llm.LLMError as exc:
        log.warning("draft copy fell back to the video title: %s", exc)
        return None
    copy = _clean(result, [x["id"] for x in lines])
    return copy if copy["title"] else None


def fallback_copy(source: dict[str, Any]) -> dict[str, Any]:
    title = str(source.get("title") or "")[: get_settings().title_max_chars]
    return {"title": title, "narrations": []}
