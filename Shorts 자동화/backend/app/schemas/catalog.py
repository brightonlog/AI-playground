from typing import Any

from pydantic import BaseModel


class Template(BaseModel):
    id: str
    name: str
    description: str
    available: bool


class StylePreset(BaseModel):
    id: str
    values: dict[str, Any]
