from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def default_telemetry_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".anti-silo"))
    return base / "AntiSilo" / "usage-events.jsonl"


class LocalTelemetry:
    """Minimal local product analytics with no file contents or paths."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_telemetry_path()

    def record(self, event: str, **properties: Any) -> None:
        safe = {
            "event": event,
            "at": datetime.now(timezone.utc).isoformat(),
            "properties": {key: value for key, value in properties.items() if key not in {"path", "file", "title", "body"}},
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(safe, ensure_ascii=False) + "\n")
