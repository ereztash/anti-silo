from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import output_dir
from .evidence_queue import build_queue
from .index import build_index


def _candidate_sources(vault: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    rows_by_hash: dict[str, dict[str, Any]] = {}
    for surface in build_index(vault, config):
        existing = rows_by_hash.get(surface.content_hash)
        row = {
            "file": surface.file,
            "source_hash": surface.content_hash,
            "authority": surface.authority,
            "can_anchor_claim": surface.can_anchor_claim,
            "surfaces": list(surface.surfaces),
        }
        if existing is None or (surface.can_anchor_claim and not existing["can_anchor_claim"]):
            rows_by_hash[surface.content_hash] = row
    rows = list(rows_by_hash.values())
    return sorted(rows, key=lambda item: (not item["can_anchor_claim"], item["file"]))


def build_source_spine_todos(vault: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = _candidate_sources(vault, config)
    anchorable = [row for row in candidates if row["can_anchor_claim"]]
    fallback = candidates[:5]
    rows = []
    for item in build_queue(vault, config):
        if item["upgrade_path"] != "source_spine_backfill":
            continue
        suggestions = anchorable[:5] if anchorable else fallback
        rows.append(
            {
                "file": item["file"],
                "claim_kind": item["claim_kind"],
                "reason": item["reason"],
                "required_metadata": ["source_hash", "source_spine"],
                "candidate_sources": suggestions,
                "template": [
                    "source_spine:",
                    "  - source_hash: <sha256 from truth_surface_index.json>",
                    "    source_file: <relative path>",
                    "    role: primary_source | corroboration | bibliography",
                ],
            }
        )
    return rows


def write_source_spine_todos(vault: Path, config: dict[str, Any]) -> dict[str, Any]:
    out = output_dir(vault, config)
    rows = build_source_spine_todos(vault, config)
    payload = {"generated": datetime.now(timezone.utc).isoformat(), "selected": len(rows), "rows": rows}
    (out / "source_spine_todo.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    with (out / "source_spine_todo.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "claim_kind", "reason", "required_metadata", "candidate_sources"])
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "file": row["file"],
                    "claim_kind": row["claim_kind"],
                    "reason": row["reason"],
                    "required_metadata": ";".join(row["required_metadata"]),
                    "candidate_sources": ";".join(candidate["file"] for candidate in row["candidate_sources"]),
                }
            )
    md = ["# Source Spine TODO", "", f"- selected: **{len(rows)}**", ""]
    for row in rows:
        md.append(f"## `{row['file']}`")
        md.append("")
        md.append("```yaml")
        md.extend(row["template"])
        md.append("```")
        md.append("")
        if row["candidate_sources"]:
            md.append("Candidate local surfaces:")
            for candidate in row["candidate_sources"]:
                anchor = "anchorable" if candidate["can_anchor_claim"] else "candidate_only"
                md.append(f"- `{candidate['file']}` `{anchor}` `{candidate['source_hash']}`")
        else:
            md.append("No local candidate surface found. Add source files under `sources/` or mark explicit source metadata.")
        md.append("")
    if not rows:
        md.append("- No synthesis claim currently needs a source spine.")
    (out / "SOURCE_SPINE_TODO.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return payload
