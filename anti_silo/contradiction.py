from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import output_dir
from .contradiction_rules import (
    _decision,
    _penalties_for,
    _severity,
    enabled,
    hard_block_threshold,
    weights,
)
from .scanner import scan_claims
from .triangulation import build_triangulation


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
