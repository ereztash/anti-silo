from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import output_dir
from .triangulation import build_triangulation


def build_eligible_sources(vault: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    eligible_tiers = set(config.get("eligible_tiers", ["triangulated"]))
    grouped: dict[str, dict[str, Any]] = {}
    claims_by_source: dict[str, list[str]] = defaultdict(list)

    for row in build_triangulation(vault, config):
        if row.tier not in eligible_tiers or not row.source:
            continue
        key = row.source_hash or row.source
        claims_by_source[key].append(row.file)
        grouped[key] = {
            "source": row.source,
            "source_hash": row.source_hash,
            "authority": row.authority,
            "eligible_for": "grounding",
            "granting_tiers": sorted(eligible_tiers),
        }

    rows = []
    for key, row in grouped.items():
        row["granted_by_claims"] = sorted(claims_by_source[key])
        rows.append(row)
    return sorted(rows, key=lambda item: item["source"])


def write_eligible_sources(vault: Path, config: dict[str, Any]) -> dict[str, Any]:
    out = output_dir(vault, config)
    rows = build_eligible_sources(vault, config)
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "selected": len(rows),
        "eligible_tiers": config.get("eligible_tiers", ["triangulated"]),
        "rows": rows,
    }
    (out / "eligible_sources.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    with (out / "eligible_sources.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["source", "source_hash", "authority", "eligible_for", "granting_tiers", "granted_by_claims"])
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    **row,
                    "granting_tiers": ";".join(row["granting_tiers"]),
                    "granted_by_claims": ";".join(row["granted_by_claims"]),
                }
            )
    md = ["# Eligible Sources", "", f"- selected: **{len(rows)}**", ""]
    for row in rows:
        md.append(f"- `{row['source']}` `{row['authority']}` `{row['source_hash']}`")
    if not rows:
        md.append("- No source is currently eligible for grounding.")
    (out / "ELIGIBLE_SOURCES.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return payload
