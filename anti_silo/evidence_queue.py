from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import output_dir
from .triangulation import build_triangulation


REPAIR_RULES = {
    "graph_only": ("source_and_corroboration_backfill", "add source anchor and independent corroboration"),
    "source_backed": ("corroboration_backfill", "add independent field or methodological corroboration"),
    "corroborated_no_source": ("source_anchor_backfill", "add explicit source anchor"),
    "ledger_supported": ("ledger_validation", "upgrade ledger support into source/corroboration evidence"),
    "refuted_or_blocked": ("repair_or_retire", "repair, demote, or retire before promotion"),
}


def build_queue(vault: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in build_triangulation(vault, config):
        if row.tier == "triangulated":
            continue
        path, required = REPAIR_RULES.get(row.tier, ("review", "manual review"))
        priority = {
            "graph_only": 25,
            "corroborated_no_source": 24,
            "source_backed": 20,
            "ledger_supported": 16,
            "refuted_or_blocked": 10,
        }.get(row.tier, 5)
        rows.append({"priority": priority, "file": row.file, "tier": row.tier, "upgrade_path": path, "required_evidence": required})
    return sorted(rows, key=lambda item: (-item["priority"], item["file"]))


def write_queue(vault: Path, config: dict[str, Any]) -> dict[str, Any]:
    out = output_dir(vault, config)
    rows = build_queue(vault, config)
    payload = {"generated": datetime.now(timezone.utc).isoformat(), "selected": len(rows), "rows": rows}
    (out / "evidence_upgrade_queue.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    with (out / "evidence_upgrade_queue.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["priority", "file", "tier", "upgrade_path", "required_evidence"])
        writer.writeheader()
        writer.writerows(rows)
    md = ["# Evidence Upgrade Queue", "", f"- selected: **{len(rows)}**", ""]
    for row in rows:
        md.append(f"- P{row['priority']} `{row['tier']}` `{row['file']}` — {row['required_evidence']}")
    (out / "EVIDENCE_UPGRADE_QUEUE.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return payload
