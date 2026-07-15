from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "contracts" / "default_config.json"


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(config_path) if config_path else DEFAULT_CONFIG
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def output_dir(vault: Path, config: dict[str, Any]) -> Path:
    out = vault / str(config.get("output_dir", "anti_silo_out"))
    out.mkdir(parents=True, exist_ok=True)
    return out


def rel(vault: Path, path: Path) -> str:
    return path.relative_to(vault).as_posix()
