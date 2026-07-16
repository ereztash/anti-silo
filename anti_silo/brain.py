from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ENTRY_KINDS = {"note", "decision", "question", "task"}
SOURCE_TIERS = {"triangulated", "source_backed", "indexed_unverified", "graph_only", "ledger_supported", "corroborated_no_source", "refuted_or_blocked"}


def default_brain_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".anti-silo"))
    return base / "AntiSilo" / "Brain"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class BrainStore:
    """A local, append-friendly knowledge store layered over Anti-Silo trust tiers."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or default_brain_dir()).resolve()
        self.path = self.root / "brain.json"

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema_version": 1, "created_at": _now(), "entries": []}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, data: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def entries(self) -> list[dict[str, Any]]:
        return list(self._load().get("entries", []))

    def add_entry(
        self,
        *,
        kind: str,
        title: str,
        body: str = "",
        source_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        if kind not in ENTRY_KINDS:
            raise ValueError(f"unknown brain entry kind: {kind}")
        title = title.strip()
        if not title:
            raise ValueError("title is required")
        data = self._load()
        entries = data.setdefault("entries", [])
        entry = {
            "id": f"entry-{len(entries) + 1:06d}",
            "kind": kind,
            "title": title,
            "body": body.strip(),
            "source_ids": list(dict.fromkeys(source_ids or [])),
            "created_at": _now(),
            "updated_at": _now(),
        }
        if kind == "decision":
            by_id = {str(row.get("id")): row for row in entries}
            linked_sources = [by_id[source_id] for source_id in entry["source_ids"] if source_id in by_id]
            if not linked_sources:
                entry["decision_status"] = "draft_requires_sources"
            elif len(linked_sources) == len(entry["source_ids"]) and all(
                source.get("kind") == "source" and source.get("trust_tier") == "triangulated"
                for source in linked_sources
            ):
                entry["decision_status"] = "supported"
            else:
                entry["decision_status"] = "needs_source_review"
        entries.append(entry)
        self._save(data)
        return entry

    def import_scan_report(self, report: dict[str, Any]) -> dict[str, int]:
        """Persist scan rows as source memories without upgrading their trust tier."""
        data = self._load()
        entries = data.setdefault("entries", [])
        existing = {str(row.get("source_key", "")) for row in entries if row.get("kind") == "source"}
        added = 0
        skipped = 0
        source_root = str(report.get("source_root", ""))
        for row in report.get("rows", []):
            source_file = str(row.get("file", ""))
            source_key = f"{source_root}|{source_file}"
            if not source_file or source_key in existing:
                skipped += 1
                continue
            technical_tier = str(row.get("technical_tier", "indexed_unverified"))
            entries.append(
                {
                    "id": f"entry-{len(entries) + 1:06d}",
                    "kind": "source",
                    "title": source_file,
                    "body": str(row.get("explanation", "")),
                    "source_ids": [],
                    "source_key": source_key,
                    "trust_tier": technical_tier if technical_tier in SOURCE_TIERS else "indexed_unverified",
                    "trust_status": str(row.get("status", "")),
                    "trust_action": str(row.get("action", "")),
                    "created_at": _now(),
                    "updated_at": _now(),
                }
            )
            existing.add(source_key)
            added += 1
        self._save(data)
        return {"added": added, "skipped": skipped}

    def review_queue(self) -> list[dict[str, str]]:
        entries = self.entries()
        by_id = {str(row["id"]): row for row in entries}
        queue: list[dict[str, str]] = []
        for entry in entries:
            if entry.get("kind") == "source" and entry.get("trust_tier") != "triangulated":
                queue.append({"id": str(entry["id"]), "title": str(entry["title"]), "reason": "המקור טרם הגיע לדרגת אמון מלאה"})
            if entry.get("kind") == "decision":
                source_ids = entry.get("source_ids", [])
                sources = [by_id[source_id] for source_id in source_ids if source_id in by_id]
                if not sources:
                    queue.append({"id": str(entry["id"]), "title": str(entry["title"]), "reason": "החלטה ללא מקורות מקושרים"})
                elif len(sources) != len(source_ids) or any(
                    source.get("kind") != "source" or source.get("trust_tier") != "triangulated" for source in sources
                ):
                    queue.append({"id": str(entry["id"]), "title": str(entry["title"]), "reason": "החלטה נשענת על מקור שעדיין דורש אימות"})
        return queue

    def dashboard(self) -> dict[str, Any]:
        entries = self.entries()
        source_rows = [row for row in entries if row.get("kind") == "source"]
        return {
            "root": str(self.root),
            "counts": {
                "sources": len(source_rows),
                "trusted_sources": sum(1 for row in source_rows if row.get("trust_tier") == "triangulated"),
                "notes": sum(1 for row in entries if row.get("kind") == "note"),
                "decisions": sum(1 for row in entries if row.get("kind") == "decision"),
                "questions": sum(1 for row in entries if row.get("kind") == "question"),
            },
            "entries": list(reversed(entries)),
            "review_queue": self.review_queue(),
        }
