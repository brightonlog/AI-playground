from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.health import redis_ok

router = APIRouter()


@router.get("/health")
def health(db: Annotated[Session, Depends(get_db)]) -> dict[str, object]:
    db.execute(text("SELECT 1"))
    redis = redis_ok()
    return {"status": "ok" if redis else "degraded", "db": True, "redis": redis}
