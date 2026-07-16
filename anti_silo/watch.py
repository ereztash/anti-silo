from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .brain import default_brain_dir


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_watch_path() -> Path:
    return default_brain_dir().parent / "watchlist.json"


def folder_fingerprint(root: Path) -> str:
    """Create a deterministic metadata fingerprint without reading file content."""
    parts: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        parts.append(f"{path.relative_to(root).as_posix()}:{stat.st_size}:{stat.st_mtime_ns}")
    return "\n".join(parts)


class WatchStore:
    """Persistent local watch list with metadata-only change detection."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = (path or default_watch_path()).resolve()
        self._lock = threading.Lock()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema_version": 1, "watches": [], "events": []}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def add(self, root: Path) -> dict[str, Any]:
        root = root.expanduser().resolve()
        if not root.is_dir():
            raise ValueError("watch path must be an existing folder")
        with self._lock:
            data = self._load()
            path = str(root)
            existing = next((item for item in data["watches"] if item["path"] == path), None)
            if existing:
                return existing
            watch = {"path": path, "fingerprint": folder_fingerprint(root), "added_at": _now(), "last_checked_at": _now()}
            data["watches"].append(watch)
            self._save(data)
            return watch

    def dashboard(self) -> dict[str, Any]:
        with self._lock:
            data = self._load()
        return {"watches": data.get("watches", []), "events": list(reversed(data.get("events", [])))[:12]}

    def check(self, on_change: Callable[[Path], dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        changed: list[dict[str, Any]] = []
        with self._lock:
            data = self._load()
            for watch in data.get("watches", []):
                root = Path(str(watch["path"]))
                if not root.is_dir():
                    event = {"path": str(root), "kind": "missing", "at": _now(), "message": "The watched folder is no longer available."}
                    data.setdefault("events", []).append(event)
                    changed.append(event)
                    continue
                fingerprint = folder_fingerprint(root)
                watch["last_checked_at"] = _now()
                if fingerprint == watch.get("fingerprint"):
                    continue
                watch["fingerprint"] = fingerprint
                event = {"path": str(root), "kind": "changed", "at": _now(), "message": "Files changed and need a fresh trust check."}
                if on_change:
                    try:
                        event["report"] = on_change(root)
                    except Exception as exc:
                        event["kind"] = "scan_error"
                        event["message"] = str(exc)
                data.setdefault("events", []).append(event)
                changed.append(event)
            data["events"] = data.get("events", [])[-100:]
            self._save(data)
        return changed


class WatchService:
    """A local polling watcher. It deliberately uses no cloud or telemetry service."""

    def __init__(self, store: WatchStore, on_change: Callable[[Path], dict[str, Any]], interval_seconds: float = 30.0) -> None:
        self.store = store
        self.on_change = on_change
        self.interval_seconds = interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="anti-silo-watch", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=self.interval_seconds + 1)

    def _run(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            self.store.check(self.on_change)
