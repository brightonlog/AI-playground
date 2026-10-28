from fastapi import FastAPI

from app.api import health
from app.core.errors import register_error_handlers

app = FastAPI(title="Shorts Editor API")
register_error_handlers(app)
app.include_router(health.router, prefix="/api/v1")
