from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import output_dir
from .scanner import scan_claims
from .triangulation import build_triangulation


DEFAULT_WEIGHTS = {
    "graph_only_no_lineage": 1,
    "temporal_without_lineage": 1,
    "lineage_without_raw_source": 2,
    "corroborated_without_raw_source": 3,
    "outcome_without_raw_source": 4,
    "decision_without_raw_source": 5,
    "usage_without_raw_source": 5,
    "refuted_or_blocked": 8,
    "extraction_failed": 8,
    "extraction_truncated": 6,
}

TEMPORAL_MARKERS = (
    "prereg",
    "preprereg",
    "prospective",
    "evidence_cutoff",
    "pre_registered",
    "pre-registered",
)
OUTCOME_MARKERS = (
    "outcome:",
    "outcome_id",
    "paid_engagement",
    "value_realized",
    "decision_changed",
    "conversion_event",
    "buyer_signal:",
)
DECISION_MARKERS = (
    "decision_changed",
    "decision_used",
    "promotion decision",
    "go/no-go",
    "pricing decision",
)


def weights(config: dict[str, Any]) -> dict[str, int]:
    policy = config.get("contradiction_penalty", {})
    merged = dict(DEFAULT_WEIGHTS)
    merged.update({str(k): int(v) for k, v in policy.get("weights", {}).items()})
    return merged


def enabled(config: dict[str, Any]) -> bool:
    return bool(config.get("contradiction_penalty", {}).get("enabled", True))


def hard_block_threshold(config: dict[str, Any]) -> int:
    return int(config.get("contradiction_penalty", {}).get("hard_block_threshold", 6))


def _marker_in(blob: str, markers: tuple[str, ...]) -> bool:
    return any(marker.lower() in blob for marker in markers)


def _has_lineage(blob: str) -> bool:
    return "lineage_sources:" in blob and "source_digest:" in blob


def _raw_source_backed(row_reason: str, row_source_hash: str) -> bool:
    return bool(row_source_hash) and "raw_source_hash" in row_reason


def _severity(score: int) -> str:
    if score >= 10:
        return "critical"
    if score >= 6:
        return "high"
    if score >= 3:
        return "medium"
    if score >= 1:
        return "low"
    return "none"


def _add(
    items: list[dict[str, Any]],
    rule: str,
    rule_weights: dict[str, int],
    reason: str,
    repair: str,
) -> None:
    items.append({"rule": rule, "weight": rule_weights[rule], "reason": reason, "repair": repair})


def _penalties_for(
    *,
    file: str,
    tier: str,
    reason: str,
    source_hash: str,
    text: str,
    has_corroboration: bool,
    metadata: dict[str, str],
    rule_weights: dict[str, int],
) -> list[dict[str, Any]]:
    blob = f"{file}\n{text}".lower()
    has_lineage = _has_lineage(blob)
    has_raw = _raw_source_backed(reason, source_hash)
    has_temporal = _marker_in(blob, TEMPORAL_MARKERS)
    has_outcome = _marker_in(blob, OUTCOME_MARKERS)
    has_decision = _marker_in(blob, DECISION_MARKERS)
    items: list[dict[str, Any]] = []

    extraction_status = metadata.get("extraction_status", "complete").lower()
    if extraction_status == "failed":
        _add(
            items,
            "extraction_failed",
            rule_weights,
            "the original file could not be extracted for review",
            "install the local extractor or review and transcribe the original file manually",
        )
    elif extraction_status == "truncated":
        _add(
            items,
            "extraction_truncated",
            rule_weights,
            "only part of the original file was inspected",
            "review the omitted content or raise the extraction limit before relying on this file",
        )

    if tier == "refuted_or_blocked":
        _add(
            items,
            "refuted_or_blocked",
            rule_weights,
            "claim is explicitly refuted or blocked",
            "repair or retire the claim before any promotion review",
        )
    if tier == "graph_only" and not has_lineage and not has_raw:
        _add(
            items,
            "graph_only_no_lineage",
            rule_weights,
            "claim exists only as a graph assertion",
            "add non-promoting lineage_sources or a reviewed raw source_hash",
        )
    if has_temporal and not has_lineage and not has_raw:
        _add(
            items,
            "temporal_without_lineage",
            rule_weights,
            "temporal/prereg marker exists without a raw-source path",
            "link the prereg/cutoff claim to raw source evidence",
        )
    if has_lineage and not has_raw:
        _add(
            items,
            "lineage_without_raw_source",
            rule_weights,
            "lineage_sources/source_digest exists, but no reviewed raw source_hash was accepted",
            "manual source review; add source_hash only if the raw source supports the specific claim",
        )
    if has_corroboration and not has_raw:
        _add(
            items,
            "corroborated_without_raw_source",
            rule_weights,
            "corroboration exists without raw source backing",
            "connect the corroborated claim to a raw source",
        )
    if has_outcome and not has_raw:
        _add(
            items,
            "outcome_without_raw_source",
            rule_weights,
            "outcome/value/conversion marker exists without raw source backing",
            "attach raw-source support for the specific outcome claim",
        )
    if has_decision and not has_raw:
        _add(
            items,
            "decision_without_raw_source",
            rule_weights,
            "claim appears decision/action-linked without raw source backing",
            "record decision evidence and raw source hash before promotion",
        )
    return items


def _decision(score: int, rules: set[str], threshold: int) -> str:
    if "refuted_or_blocked" in rules:
        return "blocked_refuted"
    if score >= threshold:
        return "blocked_contradiction_debt"
    if score > 0:
        return "review_required"
    return "no_penalty"


def build_contradiction_penalties(vault: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    if not enabled(config):
        return []
    claim_by_file = {claim.file: claim for claim in scan_claims(vault, config)}
    threshold = hard_block_threshold(config)
    rule_weights = weights(config)
    rows: list[dict[str, Any]] = []
    for row in build_triangulation(vault, config):
        claim = claim_by_file.get(row.file)
        text = claim.text if claim else ""
        has_corroboration = bool(claim.has_corroboration if claim else False)
        penalties = _penalties_for(
            file=row.file,
            tier=row.tier,
            reason=row.reason,
            source_hash=row.source_hash,
            text=text,
            has_corroboration=has_corroboration,
            metadata=claim.metadata if claim else {},
            rule_weights=rule_weights,
        )
        score = sum(int(item["weight"]) for item in penalties)
        rules = [str(item["rule"]) for item in penalties]
        decision = _decision(score, set(rules), threshold)
        rows.append(
            {
                "file": row.file,
                "tier": row.tier,
                "penalty_score": score,
                "severity": _severity(score),
                "decision": decision,
                "hard_block": decision in {"blocked_refuted", "blocked_contradiction_debt"},
                "rules": rules,
                "penalties": penalties,
                "next_repair": penalties[0]["repair"] if penalties else "",
            }
        )
    return rows


def penalty_by_file(vault: Path, config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["file"]: row for row in build_contradiction_penalties(vault, config)}


def write_contradiction_penalties(vault: Path, config: dict[str, Any]) -> dict[str, Any]:
    out = output_dir(vault, config)
    rows = build_contradiction_penalties(vault, config)
    severity_counts = Counter(str(row["severity"]) for row in rows)
    decision_counts = Counter(str(row["decision"]) for row in rows)
    rule_counts: Counter[str] = Counter()
    for row in rows:
        rule_counts.update(row["rules"])
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "total": len(rows),
        "claims_with_penalty": sum(1 for row in rows if int(row["penalty_score"]) > 0),
        "hard_blocks": sum(1 for row in rows if row["hard_block"] is True),
        "total_penalty_score": sum(int(row["penalty_score"]) for row in rows),
        "max_penalty_score": max((int(row["penalty_score"]) for row in rows), default=0),
        "by_severity": dict(severity_counts),
        "by_decision": dict(decision_counts),
        "by_rule": dict(rule_counts),
        "rows": rows,
    }
    (out / "contradiction_penalty.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    with (out / "contradiction_penalty.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["file", "tier", "penalty_score", "severity", "decision", "hard_block", "rules", "next_repair"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "file": row["file"],
                    "tier": row["tier"],
                    "penalty_score": row["penalty_score"],
                    "severity": row["severity"],
                    "decision": row["decision"],
                    "hard_block": row["hard_block"],
                    "rules": ";".join(row["rules"]),
                    "next_repair": row["next_repair"],
                }
            )
    md = [
        "# Contradiction Penalty",
        "",
        f"- claims checked: **{payload['total']}**",
        f"- claims with penalty: **{payload['claims_with_penalty']}**",
        f"- hard blocks: **{payload['hard_blocks']}**",
        f"- total penalty score: **{payload['total_penalty_score']}**",
        f"- max penalty score: **{payload['max_penalty_score']}**",
        "",
        "## Rules",
        "",
    ]
    for rule, count in sorted(payload["by_rule"].items()):
        md.append(f"- `{rule}`: {count}")
    md += ["", "## Highest Penalty Queue", "", "| penalty | decision | rules | file |", "|---:|---|---|---|"]
    for row in sorted(rows, key=lambda item: (-int(item["penalty_score"]), str(item["file"])))[:50]:
        rules = ", ".join(f"`{rule}`" for rule in row["rules"]) or "-"
        md.append(f"| {row['penalty_score']} | `{row['decision']}` | {rules} | `{row['file']}` |")
    (out / "CONTRADICTION_PENALTY.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return payload
