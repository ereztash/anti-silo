from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import output_dir
from .contradiction import write_contradiction_penalties
from .evidence_queue import write_queue
from .eligible import write_eligible_sources
from .index import write_index
from .promotion import write_enforcement
from .spine import write_source_spine_todos
from .triangulation import write_triangulation


def pulse_decision(enforcement: dict[str, Any], contradiction: dict[str, Any]) -> str:
    if not enforcement["blocked"]:
        return "proceed"
    if contradiction["hard_blocks"]:
        return "blocked"
    blocked_rows = [row for row in enforcement.get("rows", []) if row.get("decision") == "block"]
    if blocked_rows and all(row.get("tier") == "source_backed" for row in blocked_rows):
        return "source_backed_pending_corroboration"
    return "blocked"


def write_pulse(vault: Path, config: dict[str, Any]) -> dict[str, Any]:
    out = output_dir(vault, config)
    index = write_index(vault, config)
    triangulation = write_triangulation(vault, config)
    contradiction = write_contradiction_penalties(vault, config)
    queue = write_queue(vault, config)
    enforcement = write_enforcement(vault, config)
    eligible = write_eligible_sources(vault, config)
    spine = write_source_spine_todos(vault, config)
    decision = pulse_decision(enforcement, contradiction)
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "truth_surfaces": index["total"],
        "claims": triangulation["total"],
        "triangulation": triangulation["by_tier"],
        "contradiction_penalty": {
            "claims_with_penalty": contradiction["claims_with_penalty"],
            "hard_blocks": contradiction["hard_blocks"],
            "total_penalty_score": contradiction["total_penalty_score"],
            "max_penalty_score": contradiction["max_penalty_score"],
            "by_rule": contradiction["by_rule"],
        },
        "queue_size": queue["selected"],
        "eligible_sources": eligible["selected"],
        "internal_grounding_candidates": eligible["internal_candidates"],
        "trust_boundary": eligible["trust_boundary"],
        "source_spine_todos": spine["selected"],
        "promotion_gate": {"blocked": enforcement["blocked"], "review": enforcement["review"], "allowed": enforcement["allowed"]},
    }
    (out / "pulse.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md = [
        "# Anti-Silo Pulse",
        "",
        f"- decision: **`{decision}`**",
        f"- truth surfaces: **{payload['truth_surfaces']}**",
        f"- claims: **{payload['claims']}**",
        f"- contradiction hard blocks: **{contradiction['hard_blocks']}**",
        f"- contradiction penalty score: **{contradiction['total_penalty_score']}**",
        f"- evidence queue: **{payload['queue_size']}**",
        f"- eligible sources: **{payload['eligible_sources']}**",
        f"- internal grounding candidates: **{payload['internal_grounding_candidates']}**",
        f"- source spine todos: **{payload['source_spine_todos']}**",
        f"- promotion blocked: **{enforcement['blocked']}**",
        f"- promotion review: **{enforcement['review']}**",
        "",
        "## Trust Boundary",
        "",
        "- Anti-Silo measures source/provenance eligibility for grounding.",
        "- Anti-Silo does not measure product usage, user value, field adoption, semantic truth, or business validation.",
        "",
        "## Triangulation",
    ]
    for tier, count in sorted(payload["triangulation"].items()):
        md.append(f"- `{tier}`: {count}")
    md += ["", "## Contradiction Penalty", ""]
    for rule, count in sorted(contradiction["by_rule"].items()):
        md.append(f"- `{rule}`: {count}")
    (out / "PULSE.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return payload
