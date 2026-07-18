from __future__ import annotations

from anti_silo.consultant import (
    build_consultant_analysis,
    build_readiness_score,
    build_risk_register,
    estimate_cleanup_effort,
)


def test_readiness_score_is_explainable_and_rewards_grounding_eligibility() -> None:
    diagnostics = {"total_files": 4, "ingested_files": 4, "counts": {}}

    score = build_readiness_score({"ready": 4}, diagnostics)

    assert score["score"] == 100
    assert score["grounding_eligible_pct"] == 100
    assert score["components"] == {
        "weighted_base": 100,
        "duplicate_penalty": 0,
        "stop_cap_applied": False,
        "stop_findings": 0,
    }
    assert "ready=100" in score["methodology"]


def test_custom_go_threshold_shifts_ready_band_and_is_clamped() -> None:
    # A corpus scoring 90 is "ready" at the default 85, but a consultant in a
    # regulated domain can raise the bar to 95 and the same corpus drops out.
    diagnostics = {"total_files": 10, "ingested_files": 10, "counts": {}}
    counts = {"ready": 9, "backed": 1}  # 9*100 + 1*75 = 975 / 10 -> 98

    default_band = build_readiness_score(counts, diagnostics)
    assert default_band["go_threshold"] == 85
    assert default_band["band"] == "ready"

    strict = build_readiness_score(counts, diagnostics, go_threshold=99)
    assert strict["go_threshold"] == 99
    assert strict["band"] != "ready"

    # Out-of-range values are clamped to a sane [60, 100] band.
    assert build_readiness_score(counts, diagnostics, go_threshold=500)["go_threshold"] == 100
    assert build_readiness_score(counts, diagnostics, go_threshold=5)["go_threshold"] == 60
    assert build_readiness_score(counts, diagnostics, go_threshold="oops")["go_threshold"] == 85


def test_stop_finding_caps_readiness_and_creates_high_risk() -> None:
    counts = {"ready": 4, "contradiction": 1}
    diagnostics = {
        "total_files": 5,
        "ingested_files": 5,
        "counts": {"extraction_failed": 1},
    }
    remediation = [
        {
            "severity": "block",
            "category": "extraction_failed",
            "file": "archive.pdf",
            "finding": "Extraction failed",
            "action": "Replace with an extractable source",
        }
    ]

    analysis = build_consultant_analysis(
        counts,
        diagnostics,
        remediation,
        {"label": "STOP"},
        {"total": 5, "ready": 4, "review": 0, "blocked": 1},
    )

    assert analysis["readiness_score"]["score"] <= 49
    assert analysis["risk_register"][0] == {
        "risk_id": "R001",
        "category": "Extraction Failure",
        "file": "archive.pdf",
        "description": "Extraction failed",
        "severity": "High",
        "recommendation": "Replace with an extractable source",
        "impact": "",
    }
    assert analysis["effort_estimate"]["minimum_hours"] >= 1
    assert "5 files" in analysis["executive_summary"]["en"]


def test_risk_ids_and_effort_range_are_deterministic() -> None:
    risks = build_risk_register(
        [
            {"severity": "block", "category": "empty_file", "file": "a.txt"},
            {"severity": "review", "category": "unsupported_format", "file": "b.pptx"},
            {"severity": "cleanup", "category": "exact_duplicate", "file": "c.txt"},
        ]
    )

    effort = estimate_cleanup_effort(risks)

    assert [risk["risk_id"] for risk in risks] == ["R001", "R002", "R003"]
    assert effort["risk_counts"] == {"High": 1, "Medium": 1, "Low": 1}
    assert effort["minimum_hours"] <= effort["maximum_hours"]
