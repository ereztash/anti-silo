from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_projects_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".anti-silo"))
    return base / "AntiSilo" / "projects.json"


def _clean(value: Any, fallback: str = "") -> str:
    return " ".join(str(value or fallback).strip().split())[:160]


def scan_summary(report: dict[str, Any]) -> dict[str, Any]:
    counts = {key: int(value) for key, value in dict(report.get("counts", {})).items()}
    diagnostic_counts = {
        key: int(value)
        for key, value in dict(report.get("diagnostics", {}).get("counts", {})).items()
    }
    return {
        "scanned_at": str(report.get("generated_at", _now())),
        "verdict": str(report.get("verdict", {}).get("status", "conditional_go")),
        "files": int(report.get("files", 0)),
        "counts": counts,
        "diagnostic_counts": diagnostic_counts,
    }


def compare_scans(previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, Any]:
    if not previous:
        return {"has_previous": False}

    previous_counts = dict(previous.get("counts", {}))
    current_counts = dict(current.get("counts", {}))
    previous_diagnostics = dict(previous.get("diagnostic_counts", {}))
    current_diagnostics = dict(current.get("diagnostic_counts", {}))

    def delta(key: str) -> int:
        return int(current_counts.get(key, 0)) - int(previous_counts.get(key, 0))

    previous_blocked = int(previous_counts.get("unsupported", 0)) + int(previous_counts.get("contradiction", 0))
    current_blocked = int(current_counts.get("unsupported", 0)) + int(current_counts.get("contradiction", 0))
    previous_review = sum(int(previous_counts.get(key, 0)) for key in ("backed", "indexed", "synthesis"))
    current_review = sum(int(current_counts.get(key, 0)) for key in ("backed", "indexed", "synthesis"))
    previous_corpus_issues = sum(int(value) for value in previous_diagnostics.values())
    current_corpus_issues = sum(int(value) for value in current_diagnostics.values())
    return {
        "has_previous": True,
        "previous_scanned_at": str(previous.get("scanned_at", "")),
        "ready": delta("ready"),
        "review": current_review - previous_review,
        "blocked": current_blocked - previous_blocked,
        "corpus_issues": current_corpus_issues - previous_corpus_issues,
    }


class ProjectStore:
    """Local project metadata and summary-only scan history for consultant work."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = (path or default_projects_path()).resolve()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema_version": 1, "projects": []}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def upsert(self, metadata: dict[str, Any], source_root: Path) -> dict[str, Any]:
        source_root = source_root.expanduser().resolve()
        project_name = _clean(metadata.get("project_name"), source_root.name or "RAG Preflight")
        client_name = _clean(metadata.get("client_name"), "לקוח")
        consultant_name = _clean(metadata.get("consultant_name"))
        key = "|".join((client_name.casefold(), project_name.casefold(), str(source_root).casefold()))
        project_id = f"project-{hashlib.sha256(key.encode('utf-8')).hexdigest()[:12]}"

        data = self._load()
        projects = data.setdefault("projects", [])
        project = next((row for row in projects if row.get("id") == project_id), None)
        if project is None:
            project = {
                "id": project_id,
                "created_at": _now(),
                "scans": [],
            }
            projects.append(project)
        project.update(
            {
                "client_name": client_name,
                "project_name": project_name,
                "consultant_name": consultant_name,
                "source_root": str(source_root),
                "updated_at": _now(),
            }
        )
        self._save(data)
        return {key: value for key, value in project.items() if key != "scans"}

    def latest_scan(self, project_id: str) -> dict[str, Any] | None:
        project = next((row for row in self._load().get("projects", []) if row.get("id") == project_id), None)
        scans = list(project.get("scans", [])) if project else []
        return dict(scans[-1]) if scans else None

    def record_scan(self, project_id: str, report: dict[str, Any]) -> dict[str, Any]:
        data = self._load()
        project = next((row for row in data.get("projects", []) if row.get("id") == project_id), None)
        if project is None:
            raise ValueError("unknown local project")
        summary = scan_summary(report)
        scans = project.setdefault("scans", [])
        scans.append(summary)
        project["scans"] = scans[-50:]
        project["updated_at"] = _now()
        self._save(data)
        return summary

    def list_projects(self) -> list[dict[str, Any]]:
        projects = []
        for row in self._load().get("projects", []):
            item = {key: value for key, value in row.items() if key != "scans"}
            scans = list(row.get("scans", []))
            item["scan_count"] = len(scans)
            item["last_scan"] = scans[-1] if scans else None
            projects.append(item)
        return sorted(projects, key=lambda row: str(row.get("updated_at", "")), reverse=True)
