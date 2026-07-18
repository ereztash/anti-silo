from __future__ import annotations

import math
from typing import Any


_TIER_WEIGHTS = {
    "ready": 1.0,
    "backed": 0.75,
    "indexed": 0.40,
    "synthesis": 0.30,
    "unsupported": 0.0,
    "contradiction": 0.0,
}

_RISK_CATEGORIES = {
    "unsupported_format": "Unsupported Format",
    "empty_file": "Empty File",
    "extraction_failed": "Extraction Failure",
    "extraction_truncated": "Partial Extraction",
    "exact_duplicate": "Duplicate Content",
    "contradiction": "Contradiction",
    "unsupported": "Missing Provenance",
    "indexed": "Unverified Source",
    "synthesis": "Missing Source Spine",
    "backed": "Corroboration Gap",
}


def build_readiness_score(counts: dict[str, int], diagnostics: dict[str, Any]) -> dict[str, Any]:
    total = int(diagnostics.get("total_files", 0))
    if total <= 0:
        return {
            "score": 0,
            "band": "no_corpus",
            "label": "No corpus",
            "label_he": "אין קבצים לבדיקה",
            "grounding_eligible_pct": 0,
            "source_backed_pct": 0,
            "intake_coverage_pct": 0,
            "components": {"weighted_base": 0, "duplicate_penalty": 0, "stop_cap_applied": False},
            "methodology": "No files were found in scope.",
        }

    weighted_files = sum(int(counts.get(tier, 0)) * weight for tier, weight in _TIER_WEIGHTS.items())
    weighted_base = min(100, round(100 * weighted_files / total))
    diagnostic_counts = dict(diagnostics.get("counts", {}))
    duplicate_penalty = min(15, int(diagnostic_counts.get("duplicate_files", 0)) * 2)
    raw_score = max(0, weighted_base - duplicate_penalty)
    stop_findings = (
        int(counts.get("unsupported", 0))
        + int(counts.get("contradiction", 0))
        + int(diagnostic_counts.get("empty_files", 0))
        + int(diagnostic_counts.get("extraction_failed", 0))
        + int(diagnostic_counts.get("extraction_truncated", 0))
    )
    score = min(raw_score, 49) if stop_findings else raw_score
    if score >= 85:
        band, label, label_he = "ready", "Ready", "מוכן"
    elif score >= 65:
        band, label, label_he = "targeted_remediation", "Targeted remediation", "דורש תיקון ממוקד"
    elif score >= 40:
        band, label, label_he = "material_remediation", "Material remediation", "דורש טיפול מהותי"
    else:
        band, label, label_he = "not_ready", "Not ready", "לא מוכן"

    pct = lambda value: round(100 * int(value) / total)
    return {
        "score": score,
        "band": band,
        "label": label,
        "label_he": label_he,
        "grounding_eligible_pct": pct(counts.get("ready", 0)),
        "source_backed_pct": pct(int(counts.get("ready", 0)) + int(counts.get("backed", 0))),
        "intake_coverage_pct": pct(diagnostics.get("ingested_files", 0)),
        "components": {
            "weighted_base": weighted_base,
            "duplicate_penalty": duplicate_penalty,
            "stop_cap_applied": bool(stop_findings and raw_score > 49),
            "stop_findings": stop_findings,
        },
        "methodology": (
            "Weighted source-policy points per file in scope: ready=100, source-backed=75, "
            "indexed=40, synthesis=30, blocked=0; exact duplicates deduct 2 points each "
            "up to 15; any STOP finding caps the score at 49."
        ),
    }


def build_risk_register(remediation: list[dict[str, Any]]) -> list[dict[str, Any]]:
    severity_labels = {"block": "High", "review": "Medium", "cleanup": "Low"}
    risks = []
    for index, row in enumerate(remediation, start=1):
        category = str(row.get("category", "source_policy"))
        risks.append(
            {
                "risk_id": f"R{index:03d}",
                "category": _RISK_CATEGORIES.get(category, category.replace("_", " ").title()),
                "file": str(row.get("file", "")),
                "description": str(row.get("finding", "")),
                "severity": severity_labels.get(str(row.get("severity", "review")), "Medium"),
                "recommendation": str(row.get("action", "")),
                "impact": str(row.get("impact", "")),
            }
        )
    return risks


def estimate_cleanup_effort(risks: list[dict[str, Any]]) -> dict[str, Any]:
    weights = {"High": 1.5, "Medium": 0.75, "Low": 0.25}
    counts = {severity: sum(1 for risk in risks if risk.get("severity") == severity) for severity in weights}
    baseline = sum(counts[severity] * weight for severity, weight in weights.items())
    if baseline == 0:
        minimum = maximum = 0
    else:
        minimum = max(1, math.ceil(baseline * 0.75))
        maximum = max(minimum, math.ceil(baseline * 1.5))
    return {
        "minimum_hours": minimum,
        "maximum_hours": maximum,
        "risk_counts": counts,
        "assumption": (
            "Planning estimate only: High=1.5h, Medium=0.75h, Low=0.25h per finding, "
            "shown as a 0.75x-1.5x range. Validate against file complexity before quoting."
        ),
    }


def build_executive_summary(
    scope: dict[str, int],
    readiness: dict[str, Any],
    verdict: dict[str, str],
    risks: list[dict[str, Any]],
    effort: dict[str, Any],
) -> dict[str, str]:
    total = int(scope.get("total", 0))
    eligible = int(readiness.get("grounding_eligible_pct", 0))
    high = sum(1 for risk in risks if risk.get("severity") == "High")
    medium = sum(1 for risk in risks if risk.get("severity") == "Medium")
    hours = f"{effort['minimum_hours']}-{effort['maximum_hours']}"
    english = (
        f"The client corpus contains {total} files and has a readiness score of {readiness['score']}/100. "
        f"{eligible}% currently pass the production grounding policy. The audit identified {high} high and "
        f"{medium} medium risks. Recommendation: {verdict.get('label', 'CONDITIONAL GO')}. "
        f"The planning estimate for the listed remediation is {hours} hours, subject to file complexity review."
    )
    hebrew = (
        f"קורפוס הלקוח כולל {total} קבצים וציון המוכנות שלו הוא {readiness['score']} מתוך 100. "
        f"{eligible}% עוברים כעת את מדיניות ה-grounding לייצור. נמצאו {high} סיכונים ברמת חומרה גבוהה "
        f"וכן {medium} סיכונים ברמת חומרה בינונית. ההמלצה היא {verdict.get('label', 'CONDITIONAL GO')}. "
        f"הערכת התכנון לתיקונים המפורטים היא {hours} שעות, בכפוף לבדיקת מורכבות הקבצים."
    )
    return {"en": english, "he": hebrew}


def build_consultant_analysis(
    counts: dict[str, int],
    diagnostics: dict[str, Any],
    remediation: list[dict[str, Any]],
    verdict: dict[str, str],
    scope: dict[str, int],
) -> dict[str, Any]:
    readiness = build_readiness_score(counts, diagnostics)
    risks = build_risk_register(remediation)
    effort = estimate_cleanup_effort(risks)
    return {
        "readiness_score": readiness,
        "risk_register": risks,
        "effort_estimate": effort,
        "executive_summary": build_executive_summary(scope, readiness, verdict, risks, effort),
    }
