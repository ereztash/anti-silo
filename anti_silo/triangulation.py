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


def _raw_source_only(config: dict[str, Any]) -> bool:
    return bool(config.get("raw_source_only", True))


def _source_candidates(surfaces: list[Surface], config: dict[str, Any]) -> list[Surface]:
    raw_only = _raw_source_only(config)
    return [row for row in surfaces if row.can_anchor_claim and (not raw_only or row.raw_source)]


def _surface_hashes(surface: Surface) -> set[str]:
    hashes = {surface.content_hash.lower()}
    if surface.raw_source_hash:
        hashes.add(surface.raw_source_hash.lower())
    if surface.normalized_content_hash:
        hashes.add(surface.normalized_content_hash.lower())
    return hashes


def _best_source(claim: Claim, surfaces: list[Surface], config: dict[str, Any]) -> tuple[Surface | None, str]:
    declared_hash = claim.metadata.get("source_hash", "").lower()
    stem = Path(claim.file).stem.lower()
    candidates = _source_candidates(surfaces, config)
    if declared_hash:
        hash_matches = [surface for surface in surfaces if surface.can_anchor_claim and declared_hash in _surface_hashes(surface)]
        for surface in candidates:
            if declared_hash == surface.raw_source_hash.lower():
                return surface, "raw_source_hash"
            if declared_hash == surface.content_hash.lower():
                return surface, "source_hash"
            if declared_hash == surface.normalized_content_hash.lower():
                return surface, "normalized_source_hash"
        if hash_matches:
            return None, "source_hash_matches_non_raw_surface"
        return None, "source_hash_not_found"
    if _raw_source_only(config):
        return None, "source_hash_required_for_raw_source_only"
    for surface in candidates:
        surface_text = surface.file.lower()
        if stem and stem in surface_text:
            return surface, "filename_match"
    for surface in candidates:
        if surface.file == claim.file:
            return surface, "same_file_match"
    return None, "source_not_found"


def _missing_source_reason(base: str, source_status: str) -> str:
    if source_status in {"source_hash_matches_non_raw_surface", "source_hash_not_found", "source_hash_required_for_raw_source_only"}:
        return f"{base}; {source_status}"
    return base


def _reported_source_hash(claim: Claim, source: Surface) -> str:
    declared_hash = claim.metadata.get("source_hash", "").lower()
    if declared_hash and declared_hash in _surface_hashes(source):
        return declared_hash
    return source.raw_source_hash or source.content_hash


def classify_claim(claim: Claim, surfaces: list[Surface], config: dict[str, Any] | None = None) -> TriangulationRow:
    config = config or {}
    source, source_status = _best_source(claim, surfaces, config)
    if claim.blocked:
        source_hash = _reported_source_hash(claim, source) if source else ""
        return TriangulationRow(claim.file, "refuted_or_blocked", source.file if source else "", source.authority if source else "", "blocked marker", source_hash, claim.claim_kind, "repair or retire")
    if source and claim.has_corroboration:
        source_hash = _reported_source_hash(claim, source)
        reason = "claim + raw_source_hash + corroboration" if source_status in {"source_hash", "raw_source_hash", "normalized_source_hash"} and source.raw_source else "claim + source + corroboration"
        return TriangulationRow(claim.file, "triangulated", source.file, source.authority, reason, source_hash, claim.claim_kind, "")
    if source:
        source_hash = _reported_source_hash(claim, source)
        reason = "claim + raw_source_hash" if source_status in {"source_hash", "raw_source_hash", "normalized_source_hash"} and source.raw_source else "claim + source"
        return TriangulationRow(claim.file, "source_backed", source.file, source.authority, reason, source_hash, claim.claim_kind, "independent corroboration")
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
        return TriangulationRow(claim.file, "corroborated_no_source", "", "", _missing_source_reason("claim + corroboration", source_status), "", claim.claim_kind, "raw external source_hash")
    if claim.has_ledger:
        return TriangulationRow(claim.file, "ledger_supported", "", "", _missing_source_reason("claim + ledger", source_status), "", claim.claim_kind, "raw external source_hash and corroboration evidence")
    return TriangulationRow(claim.file, "graph_only", "", "", _missing_source_reason("claim only", source_status), "", claim.claim_kind, "raw external source_hash and independent corroboration")


def build_triangulation(vault: Path, config: dict[str, Any]) -> list[TriangulationRow]:
    surfaces = build_index(vault, config)
    claims = scan_claims(vault, config)
    return [classify_claim(claim, surfaces, config) for claim in claims]


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
