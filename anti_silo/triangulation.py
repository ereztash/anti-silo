from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import output_dir
from .index import build_index
from .model import Claim, Surface, TriangulationRow
from .scanner import scan_claims


def _best_source(claim: Claim, surfaces: list[Surface]) -> Surface | None:
    declared_hash = claim.metadata.get("source_hash", "").lower()
    stem = Path(claim.file).stem.lower()
    candidates = [row for row in surfaces if row.can_anchor_claim]
    if declared_hash:
        for surface in candidates:
            if surface.content_hash.lower() == declared_hash:
                return surface
    for surface in candidates:
        surface_text = surface.file.lower()
        if stem and stem in surface_text:
            return surface
    for surface in candidates:
        if surface.file == claim.file:
            return surface
    return None


def classify_claim(claim: Claim, surfaces: list[Surface]) -> TriangulationRow:
    source = _best_source(claim, surfaces)
    if claim.blocked:
        return TriangulationRow(claim.file, "refuted_or_blocked", source.file if source else "", source.authority if source else "", "blocked marker", source.content_hash if source else "", claim.claim_kind, "repair or retire")
    if source and claim.has_corroboration:
        reason = "claim + source_hash + corroboration" if claim.metadata.get("source_hash") else "claim + source + corroboration"
        return TriangulationRow(claim.file, "triangulated", source.file, source.authority, reason, source.content_hash, claim.claim_kind, "")
    if source:
        reason = "claim + source_hash" if claim.metadata.get("source_hash") else "claim + source"
        return TriangulationRow(claim.file, "source_backed", source.file, source.authority, reason, source.content_hash, claim.claim_kind, "independent corroboration")
    if claim.claim_kind == "synthesis" and not claim.has_source_spine:
        return TriangulationRow(
            claim.file,
            "graph_only",
            "",
            "",
            "synthesis_without_source_spine",
            "",
            claim.claim_kind,
            "source spine: source_hash, source_spine, bibliography, references, paper list, or SLR artifact",
        )
    if claim.has_corroboration:
        return TriangulationRow(claim.file, "corroborated_no_source", "", "", "claim + corroboration", "", claim.claim_kind, "explicit source anchor")
    if claim.has_ledger:
        return TriangulationRow(claim.file, "ledger_supported", "", "", "claim + ledger", "", claim.claim_kind, "source/corroboration evidence")
    return TriangulationRow(claim.file, "graph_only", "", "", "claim only", "", claim.claim_kind, "source anchor and independent corroboration")


def build_triangulation(vault: Path, config: dict[str, Any]) -> list[TriangulationRow]:
    surfaces = build_index(vault, config)
    claims = scan_claims(vault, config)
    return [classify_claim(claim, surfaces) for claim in claims]


def write_triangulation(vault: Path, config: dict[str, Any]) -> dict[str, Any]:
    out = output_dir(vault, config)
    rows = build_triangulation(vault, config)
    counts = Counter(row.tier for row in rows)
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "total": len(rows),
        "by_tier": dict(counts),
        "rows": [row.__dict__ for row in rows],
    }
    (out / "triangulation_gate.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    with (out / "triangulation_gate.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "tier", "source", "authority", "reason", "source_hash", "claim_kind", "needs"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)
    md = ["# Triangulation Gate", "", f"- total claims: **{payload['total']}**", ""]
    for tier in ["triangulated", "source_backed", "corroborated_no_source", "ledger_supported", "graph_only", "refuted_or_blocked"]:
        md.append(f"- `{tier}`: {counts.get(tier, 0)}")
    md += ["", "## Rows", "", "| file | tier | kind | reason | needs |", "|---|---|---|---|---|"]
    for row in rows:
        md.append(f"| `{row.file}` | `{row.tier}` | `{row.claim_kind}` | `{row.reason}` | {row.needs or '-'} |")
    (out / "TRIANGULATION_GATE.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return payload
