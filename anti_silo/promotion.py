from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import output_dir
from .model import EnforcementRow
from .triangulation import build_triangulation


DEFAULT_BLOCKED_TIERS = {"graph_only", "source_backed", "corroborated_no_source", "ledger_supported", "refuted_or_blocked"}


def blocked_tiers(config: dict[str, Any]) -> set[str]:
    policy = config.get("promotion_policy", {})
    return set(policy.get("blocked_tiers", sorted(DEFAULT_BLOCKED_TIERS)))


def review_tiers(config: dict[str, Any]) -> set[str]:
    policy = config.get("promotion_policy", {})
    return set(policy.get("review_tiers", []))


def build_enforcement(vault: Path, config: dict[str, Any]) -> list[EnforcementRow]:
    blocked = blocked_tiers(config)
    review = review_tiers(config)
    rows: list[EnforcementRow] = []
    for row in build_triangulation(vault, config):
        if row.tier in blocked:
            rows.append(
                EnforcementRow(
                    file=row.file,
                    tier=row.tier,
                    decision="block",
                    reason=f"tier `{row.tier}` is not eligible for promotion",
                    action="do_not_promote",
                )
            )
        elif row.tier in review:
            rows.append(
                EnforcementRow(
                    file=row.file,
                    tier=row.tier,
                    decision="review",
                    reason=f"tier `{row.tier}` is an internal grounding candidate, not promotion-ready",
                    action="review_before_promotion",
                )
            )
        else:
            rows.append(
                EnforcementRow(
                    file=row.file,
                    tier=row.tier,
                    decision="allow",
                    reason=f"tier `{row.tier}` satisfies promotion policy",
                    action="promotion_allowed",
                )
            )
    return rows


def write_enforcement(vault: Path, config: dict[str, Any]) -> dict[str, Any]:
    out = output_dir(vault, config)
    rows = build_enforcement(vault, config)
    counts = Counter(row.decision for row in rows)
    decision = "block" if counts.get("block", 0) else "review" if counts.get("review", 0) else "allow"
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "blocked": counts.get("block", 0),
        "review": counts.get("review", 0),
        "allowed": counts.get("allow", 0),
        "rows": [row.__dict__ for row in rows],
    }
    (out / "promotion_gate.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    with (out / "promotion_gate.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "tier", "decision", "reason", "action"])
        writer.writeheader()
        writer.writerows(row.__dict__ for row in rows)
    md = [
        "# Promotion Gate",
        "",
        f"- decision: **`{payload['decision']}`**",
        f"- blocked: **{payload['blocked']}**",
        f"- review: **{payload['review']}**",
        f"- allowed: **{payload['allowed']}**",
        "",
    ]
    for row in rows:
        md.append(f"- `{row.decision}` `{row.tier}` `{row.file}` — {row.reason}")
    (out / "PROMOTION_GATE.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return payload
