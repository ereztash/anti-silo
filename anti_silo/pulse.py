from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import output_dir
from .evidence_queue import write_queue
from .eligible import write_eligible_sources
from .index import write_index
from .promotion import write_enforcement
from .spine import write_source_spine_todos
from .triangulation import write_triangulation


def write_pulse(vault: Path, config: dict[str, Any]) -> dict[str, Any]:
    out = output_dir(vault, config)
    index = write_index(vault, config)
    triangulation = write_triangulation(vault, config)
    queue = write_queue(vault, config)
    enforcement = write_enforcement(vault, config)
    eligible = write_eligible_sources(vault, config)
    spine = write_source_spine_todos(vault, config)
    decision = "proceed"
    if enforcement["blocked"]:
        decision = "blocked"
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "truth_surfaces": index["total"],
        "claims": triangulation["total"],
        "triangulation": triangulation["by_tier"],
        "queue_size": queue["selected"],
        "eligible_sources": eligible["selected"],
        "source_spine_todos": spine["selected"],
        "promotion_gate": {"blocked": enforcement["blocked"], "allowed": enforcement["allowed"]},
    }
    (out / "pulse.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md = [
        "# Anti-Silo Pulse",
        "",
        f"- decision: **`{decision}`**",
        f"- truth surfaces: **{payload['truth_surfaces']}**",
        f"- claims: **{payload['claims']}**",
        f"- evidence queue: **{payload['queue_size']}**",
        f"- eligible sources: **{payload['eligible_sources']}**",
        f"- source spine todos: **{payload['source_spine_todos']}**",
        f"- promotion blocked: **{enforcement['blocked']}**",
        "",
        "## Triangulation",
    ]
    for tier, count in sorted(payload["triangulation"].items()):
        md.append(f"- `{tier}`: {count}")
    (out / "PULSE.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return payload
