"""Print the OpenAPI schema without starting a server: `uv run python -m app.openapi_dump`."""

import json
import sys

from app.main import app

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
print(json.dumps(app.openapi(), ensure_ascii=False, indent=2))
