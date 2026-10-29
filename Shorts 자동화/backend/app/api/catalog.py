from fastapi import APIRouter

from app.media import styles
from app.schemas.catalog import StylePreset, Template
from app.services import catalog

router = APIRouter(tags=["catalog"])


@router.get("/templates")
def list_templates() -> list[Template]:
    return catalog.list_templates()


@router.get("/styles")
def list_styles() -> list[StylePreset]:
    return [StylePreset(id=k, values=v) for k, v in styles.PRESETS.items()]
