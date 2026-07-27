from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import output_dir
from .index import build_index
from .model import Claim, Surface, TriangulationRow
from .scanner import scan_claims


_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")


def _is_well_formed_hash(value: str) -> bool:
    return bool(_SHA256_HEX.match(value))


def _real_content_hashes(surfaces: list[Surface]) -> set[str]:
    """Hashes actually computed by sha256_file/sha256_text from real, present
    bytes - as opposed to raw_source_hash, which is copied verbatim from a
    file's own frontmatter and never independently recomputed. Used to tell
    a genuinely corroborated raw-source anchor from two files that simply
    declare the same arbitrary, self-typed string."""
    hashes: set[str] = set()
    for surface in surfaces:
        if surface.content_hash:
            hashes.add(surface.content_hash.lower())
        if surface.normalized_content_hash:
            hashes.add(surface.normalized_content_hash.lower())
    return hashes


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


def _best_source(
    claim: Claim, surfaces: list[Surface], config: dict[str, Any], real_hashes: set[str] | None = None
) -> tuple[Surface | None, str]:
    declared_hash = claim.metadata.get("source_hash", "").lower()
    stem = Path(claim.file).stem.lower()
    candidates = _source_candidates(surfaces, config)
    real_hashes = real_hashes if real_hashes is not None else _real_content_hashes(surfaces)
    if declared_hash:
        hash_matches = [surface for surface in surfaces if surface.can_anchor_claim and declared_hash in _surface_hashes(surface)]
        for surface in candidates:
            if declared_hash == surface.raw_source_hash.lower():
                # raw_source_hash is copied verbatim from frontmatter, never
                # independently recomputed - two files can declare matching
                # arbitrary strings with no real bytes behind them. Only
                # trust it as strongly as source_hash/normalized_source_hash
                # (which ARE always real, recomputed hashes) if it also
                # matches some file's actually-computed content hash.
                if _is_well_formed_hash(declared_hash) and declared_hash in real_hashes:
                    return surface, "raw_source_hash"
                return surface, "raw_source_hash_unverified"
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


def classify_claim(
    claim: Claim, surfaces: list[Surface], config: dict[str, Any] | None = None, real_hashes: set[str] | None = None
) -> TriangulationRow:
    config = config or {}
    intake_kind = claim.metadata.get("intake_kind", "").lower()
    extraction_status = claim.metadata.get("extraction_status", "complete").lower()
    if intake_kind == "self_indexed":
        reason = "self_indexed_intake"
        if extraction_status == "failed":
            reason = "self_indexed_intake; extraction_failed"
        elif extraction_status == "truncated":
            reason = "self_indexed_intake; extraction_truncated"
        return TriangulationRow(
            claim.file,
            "indexed_unverified",
            "",
            "",
            reason,
            "",
            claim.claim_kind,
            "review the original file and attach an independent source before relying on it",
        )
    source, source_status = _best_source(claim, surfaces, config, real_hashes)
    if claim.blocked:
        source_hash = _reported_source_hash(claim, source) if source else ""
        return TriangulationRow(claim.file, "refuted_or_blocked", source.file if source else "", source.authority if source else "", "blocked marker", source_hash, claim.claim_kind, "repair or retire")
    verified_hash_statuses = {"source_hash", "raw_source_hash", "normalized_source_hash"}
    if source and claim.has_corroboration and source_status != "raw_source_hash_unverified":
        source_hash = _reported_source_hash(claim, source)
        reason = "claim + raw_source_hash + corroboration" if source_status in verified_hash_statuses and source.raw_source else "claim + source + corroboration"
        return TriangulationRow(claim.file, "triangulated", source.file, source.authority, reason, source_hash, claim.claim_kind, "")
    if source:
        source_hash = _reported_source_hash(claim, source)
        if source_status == "raw_source_hash_unverified":
            reason = "claim + unverified_raw_source_hash"
            needs = "raw_source_hash does not match any independently computed content hash in this corpus - verify the external source and re-anchor with a real hash"
        elif source_status in verified_hash_statuses and source.raw_source:
            reason = "claim + raw_source_hash"
            needs = "independent corroboration"
        else:
            reason = "claim + source"
            needs = "independent corroboration"
        return TriangulationRow(claim.file, "source_backed", source.file, source.authority, reason, source_hash, claim.claim_kind, needs)
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
    real_hashes = _real_content_hashes(surfaces)
    return [classify_claim(claim, surfaces, config, real_hashes) for claim in claims]


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
    for tier in ["triangulated", "source_backed", "indexed_unverified", "corroborated_no_source", "ledger_supported", "graph_only", "refuted_or_blocked"]:
        md.append(f"- `{tier}`: {counts.get(tier, 0)}")
    md += ["", "## Rows", "", "| file | tier | kind | reason | needs |", "|---|---|---|---|---|"]
    for row in rows:
        md.append(f"| `{row.file}` | `{row.tier}` | `{row.claim_kind}` | `{row.reason}` | {row.needs or '-'} |")
    (out / "TRIANGULATION_GATE.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return payload
