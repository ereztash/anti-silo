from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import output_dir, rel
from .model import Surface
from .scanner import iter_markdown, read_text


def classify_surface(rel_path: str, text: str, config: dict[str, Any]) -> Surface | None:
    blob = text.lower()
    path_blob = rel_path.lower()
    found: list[str] = []
    authorities: list[str] = []
    anchor = False

    for name, rule in config.get("surfaces", {}).items():
        path_hits = any(token.lower() in path_blob for token in rule.get("path_contains", []))
        text_hits = any(token.lower() in blob for token in rule.get("text_contains", []))
        if path_hits or text_hits:
            found.append(name)
            authorities.append(str(rule.get("authority", "unknown")))
            anchor = anchor or bool(rule.get("can_anchor_claim", False))

    if not found:
        return None
    return Surface(rel_path, tuple(found), authorities[0], anchor)


def build_index(vault: Path, config: dict[str, Any]) -> list[Surface]:
    rows: list[Surface] = []
    for path in iter_markdown(vault, config):
        surface = classify_surface(rel(vault, path), read_text(path), config)
        if surface:
            rows.append(surface)
    return rows


def write_index(vault: Path, config: dict[str, Any]) -> dict[str, Any]:
    out = output_dir(vault, config)
    rows = build_index(vault, config)
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "total": len(rows),
        "anchorable": sum(1 for row in rows if row.can_anchor_claim),
        "by_surface": dict(Counter(s for row in rows for s in row.surfaces)),
        "rows": [row.__dict__ for row in rows],
    }
    (out / "truth_surface_index.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    with (out / "truth_surface_index.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "surfaces", "authority", "can_anchor_claim"])
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "file": row.file,
                    "surfaces": ";".join(row.surfaces),
                    "authority": row.authority,
                    "can_anchor_claim": row.can_anchor_claim,
                }
            )
    md = ["# Truth Surface Index", "", f"- total: **{payload['total']}**", f"- anchorable: **{payload['anchorable']}**", ""]
    for name, count in sorted(payload["by_surface"].items()):
        md.append(f"- `{name}`: {count}")
    (out / "TRUTH_SURFACE_INDEX.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return payload
