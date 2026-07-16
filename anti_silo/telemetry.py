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

    def events(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return rows

    def has_event(self, event: str) -> bool:
        return any(row.get("event") == event for row in self.events())

    def summary(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in self.events():
            name = str(row.get("event", ""))
            if name:
                counts[name] = counts.get(name, 0) + 1
        return counts
