from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "contracts" / "default_config.json"


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(config_path) if config_path else DEFAULT_CONFIG
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def apply_profile(config: dict[str, Any], profile: str | None = None) -> dict[str, Any]:
    if not profile or profile == "default":
        return dict(config)
    profiles = config.get("profiles", {})
    if profile not in profiles:
        known = ", ".join(sorted(profiles)) or "default"
        raise ValueError(f"Unknown profile `{profile}`. Known profiles: {known}")
    merged = dict(config)
    selected = profiles[profile]
    for key, value in selected.items():
        if key == "exclude_dirs":
            merged[key] = sorted(set(config.get(key, [])) | set(value))
        else:
            merged[key] = value
    merged["active_profile"] = profile
    return merged


def output_dir(vault: Path, config: dict[str, Any]) -> Path:
    out = vault / str(config.get("output_dir", "anti_silo_out"))
    out.mkdir(parents=True, exist_ok=True)
    return out


def rel(vault: Path, path: Path) -> str:
    return path.relative_to(vault).as_posix()
