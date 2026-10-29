from fastapi import FastAPI

from app.api import analyses, catalog, edit, health, shorts
from app.core.errors import register_error_handlers

app = FastAPI(title="Shorts Editor API")
register_error_handlers(app)
app.include_router(health.router, prefix="/api/v1")
app.include_router(analyses.router, prefix="/api/v1")
app.include_router(catalog.router, prefix="/api/v1")
app.include_router(shorts.router, prefix="/api/v1")
app.include_router(edit.router, prefix="/api/v1")
