from fastapi import APIRouter

from app.schemas.catalog import Template
from app.services import catalog

router = APIRouter(tags=["catalog"])


@router.get("/templates")
def list_templates() -> list[Template]:
    return catalog.list_templates()
