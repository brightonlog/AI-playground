import json
import os
import shutil
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.ids import is_valid_id


def analysis_dir(analysis_id: str) -> Path:
    # Ids come from the DB, but check anyway so a bad value can never escape data_dir.
    if not is_valid_id(analysis_id) or not analysis_id.startswith("an_"):
        raise ValueError("invalid analysis id")
    path = get_settings().data_dir / "analyses" / analysis_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def remove_analysis_dir(analysis_id: str) -> None:
    shutil.rmtree(analysis_dir(analysis_id), ignore_errors=True)


def write_json(path: Path, data: Any) -> None:
    # Write then rename, so an existing file is always complete (pipeline skips existing files).
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))
