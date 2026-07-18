"""Deterministic What-If projection.

Recomputes the readiness score and verdict from adjusted counts when a consultant
marks problem files as fixed — without re-scanning the files. All scoring stays in
the one engine (`build_readiness_score` / `build_verdict`); this module only
translates a consultant's marked fixes into adjusted tier and diagnostic counts.

The projection is deliberately realistic, not optimistic: adding a source moves a
file to *source-backed* (still awaiting corroboration), not straight to *ready*.
Only an explicit "verify" claims full grounding. This keeps a projected GO honest.
"""
from __future__ import annotations

from typing import Any

from .consultant import DEFAULT_GO_THRESHOLD, build_readiness_score
from .preflight import build_verdict


# Tier categories a remediation item can carry (from the triangulation rows).
TIER_CATEGORIES = {"unsupported", "indexed", "synthesis", "backed", "contradiction"}

# Which target tier each "fix" action moves a file to. "exclude" drops it from scope.
_ACTION_TARGET = {
    "add_source": "backed",
    "add_spine": "backed",
    "corroborate": "ready",
    "verify": "ready",
    "resolve": "ready",
}

# Diagnostic issue kind -> the diagnostics.counts key that drives score and verdict.
_DIAG_COUNT_KEY = {
    "exact_duplicate": "duplicate_files",
    "extraction_failed": "extraction_failed",
    "extraction_truncated": "extraction_truncated",
    "empty_file": "empty_files",
    "unsupported_format": "unsupported_files",
}

# category -> default action + the actions the UI may offer. Labels live in the UI;
# the effect of each action id is authoritative here.
SIM_MODEL: dict[str, dict[str, Any]] = {
    "unsupported": {"default": "add_source", "options": ["add_source", "verify", "exclude"]},
    "indexed": {"default": "add_source", "options": ["add_source", "verify", "exclude"]},
    "synthesis": {"default": "add_spine", "options": ["add_spine", "verify", "exclude"]},
    "backed": {"default": "corroborate", "options": ["corroborate", "exclude"]},
    "contradiction": {"default": "resolve", "options": ["resolve", "exclude"]},
    "exact_duplicate": {"default": "dedupe", "options": ["dedupe"]},
    "extraction_failed": {"default": "replace", "options": ["replace", "exclude"]},
    "extraction_truncated": {"default": "replace", "options": ["replace", "exclude"]},
    "empty_file": {"default": "replace", "options": ["replace", "exclude"]},
    "unsupported_format": {"default": "convert", "options": ["convert", "exclude"]},
}


def _resolve_action(category: str, action: Any) -> str | None:
    model = SIM_MODEL.get(category)
    if not model:
        return None
    action = str(action or model["default"])
    return action if action in model["options"] else model["default"]


def simulate_readiness(report: dict[str, Any], resolutions: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {key: int(value) for key, value in dict(report.get("counts", {})).items()}
    diagnostics = dict(report.get("diagnostics", {}))
    diag_counts = {key: int(value) for key, value in dict(diagnostics.get("counts", {})).items()}
    issues = [dict(issue) for issue in diagnostics.get("issues", [])]
    total = int(diagnostics.get("total_files", 0))
    go_threshold = int((report.get("readiness_score") or {}).get("go_threshold", DEFAULT_GO_THRESHOLD))

    for resolution in resolutions or []:
        category = str(resolution.get("category", ""))
        action = _resolve_action(category, resolution.get("action"))
        if action is None:
            continue
        if category in TIER_CATEGORIES:
            if counts.get(category, 0) <= 0:
                continue
            counts[category] -= 1
            if action == "exclude":
                total = max(0, total - 1)
            else:
                target = _ACTION_TARGET.get(action, "ready")
                counts[target] = counts.get(target, 0) + 1
            continue
        key = _DIAG_COUNT_KEY.get(category)
        matched = None
        for index, issue in enumerate(issues):
            if str(issue.get("kind")) == category:
                matched = issues.pop(index)
                break
        # A duplicate group removes all its extra copies from the penalty, not one.
        decrement = max(1, len(matched.get("related_files", []))) if (matched and category == "exact_duplicate") else 1
        if key:
            diag_counts[key] = max(0, diag_counts.get(key, 0) - decrement)
        if action == "exclude":
            total = max(0, total - 1)

    adjusted = {**diagnostics, "counts": diag_counts, "issues": issues, "total_files": max(0, total)}
    return {
        "readiness_score": build_readiness_score(counts, adjusted, go_threshold),
        "verdict": build_verdict(counts, adjusted),
    }
