import json
import os
import shutil
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.ids import is_valid_id


def _job_dir(job_id: str, prefix: str, folder: str) -> Path:
    # Ids come from the DB, but check anyway so a bad value can never escape data_dir.
    if not is_valid_id(job_id) or not job_id.startswith(prefix):
        raise ValueError(f"invalid {folder} id")
    path = get_settings().data_dir / folder / job_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def analysis_dir(analysis_id: str) -> Path:
    return _job_dir(analysis_id, "an_", "analyses")


def short_dir(short_id: str) -> Path:
    return _job_dir(short_id, "sh_", "shorts")


def remove_dir(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


def write_json(path: Path, data: Any) -> None:
    # Write then rename, so an existing file is always complete (pipeline skips existing files).
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))
