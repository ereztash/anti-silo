from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import output_dir
from .triangulation import build_triangulation


def _build_sources_for_tiers(vault: Path, config: dict[str, Any], tiers: set[str], eligible_for: str) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    claims_by_source: dict[str, list[str]] = defaultdict(list)

    for row in build_triangulation(vault, config):
        if row.tier not in tiers or not row.source:
            continue
        key = row.source_hash or row.source
        claims_by_source[key].append(row.file)
        grouped[key] = {
            "source": row.source,
            "source_hash": row.source_hash,
            "authority": row.authority,
            "eligible_for": eligible_for,
            "granting_tiers": sorted(tiers),
        }

    rows = []
    for key, row in grouped.items():
        row["granted_by_claims"] = sorted(claims_by_source[key])
        rows.append(row)
    return sorted(rows, key=lambda item: item["source"])


def build_eligible_sources(vault: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    eligible_tiers = set(config.get("eligible_tiers", ["triangulated"]))
    return _build_sources_for_tiers(vault, config, eligible_tiers, "grounding")


def build_internal_grounding_candidates(vault: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    candidate_tiers = set(config.get("candidate_tiers", []))
    return _build_sources_for_tiers(vault, config, candidate_tiers, "internal_grounding_candidate")


def _write_sources(out: Path, rows: list[dict[str, Any]], stem: str, title: str, empty_message: str) -> None:
    (out / f"{stem}.json").write_text(
        json.dumps({"selected": len(rows), "rows": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with (out / f"{stem}.csv").open("w", encoding="utf-8", newline="") as f:
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
    md = [f"# {title}", "", f"- selected: **{len(rows)}**", ""]
    for row in rows:
        md.append(f"- `{row['source']}` `{row['eligible_for']}` `{row['authority']}` `{row['source_hash']}`")
    if not rows:
        md.append(empty_message)
    (out / f"{stem.upper()}.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def write_eligible_sources(vault: Path, config: dict[str, Any]) -> dict[str, Any]:
    out = output_dir(vault, config)
    rows = build_eligible_sources(vault, config)
    candidates = build_internal_grounding_candidates(vault, config)
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "selected": len(rows),
        "internal_candidates": len(candidates),
        "eligible_tiers": config.get("eligible_tiers", ["triangulated"]),
        "candidate_tiers": config.get("candidate_tiers", []),
        "rows": rows,
        "candidate_rows": candidates,
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
    _write_sources(
        out,
        candidates,
        "internal_grounding_candidates",
        "Internal Grounding Candidates",
        "- No source is currently marked as an internal grounding candidate.",
    )
    return payload
