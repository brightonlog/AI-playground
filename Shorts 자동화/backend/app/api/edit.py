from fastapi import APIRouter

from app.db.session import DbSession
from app.schemas.edit import CutRequest, CutResult, EditOut, EditPatch, EditResult
from app.services import edit

router = APIRouter(prefix="/shorts", tags=["edit"])


@router.get("/{short_id}/edit")
def get_edit(short_id: str, db: DbSession) -> EditOut:
    return edit.get_edit(db, short_id)


@router.patch("/{short_id}/edit")
def patch_edit(short_id: str, body: EditPatch, db: DbSession) -> EditResult:
    return edit.patch_edit(db, short_id, body)


@router.post("/{short_id}/cut-suggestions")
def cut_suggestions(short_id: str, body: CutRequest, db: DbSession) -> CutResult:
    return edit.cut_suggestions(db, short_id, body)
