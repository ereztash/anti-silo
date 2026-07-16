from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_repair_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".anti-silo"))
    return base / "AntiSilo" / "repairs.json"


class RepairStore:
    """Local, user-authored links between a reviewed file and an independent source."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = (path or default_repair_path()).resolve()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema_version": 1, "links": []}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def add(self, root: Path, target_file: str, source: Path) -> dict[str, str]:
        root = root.expanduser().resolve()
        target = (root / target_file).resolve()
        source = source.expanduser().resolve()
        if not root.is_dir() or not target.is_file() or not target.is_relative_to(root):
            raise ValueError("קובץ היעד אינו חלק מהתיקייה שנסרקה")
        if not source.is_file():
            raise ValueError("קובץ המקור אינו קיים")
        if source == target:
            raise ValueError("קובץ אינו יכול לשמש כמקור עצמאי של עצמו")

        row = {
            "root": str(root),
            "target_file": target.relative_to(root).as_posix(),
            "source": str(source),
            "added_at": _now(),
        }
        data = self._load()
        links = data.setdefault("links", [])
        links[:] = [
            item
            for item in links
            if not (item.get("root") == row["root"] and item.get("target_file") == row["target_file"])
        ]
        links.append(row)
        self._save(data)
        return row

    def links_for(self, root: Path) -> dict[str, Path]:
        root_text = str(root.expanduser().resolve())
        links: dict[str, Path] = {}
        for row in self._load().get("links", []):
            if row.get("root") != root_text:
                continue
            source = Path(str(row.get("source", ""))).expanduser().resolve()
            if source.is_file():
                links[str(row.get("target_file", ""))] = source
        return links
