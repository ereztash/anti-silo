from __future__ import annotations

from pathlib import Path

from anti_silo.config import load_config
from anti_silo.gui import build_human_report
from anti_silo.near_duplicate import (
    build_issues,
    content_sketch,
    figure_fingerprint,
    find_near_duplicate_groups,
    similarity,
)


SOW = """Statement of Work — Analytics Platform Migration

1. Background
The client operates a legacy reporting stack that has grown organically over
six years. Reports are generated nightly and distributed by email. Business
users have requested self-service access and faster refresh cycles.

2. Scope
Phase one covers data schema migration from the legacy warehouse into the new
model, including validation of historical records and reconciliation against
finance-approved totals. Phase two covers the client-facing dashboard and user
acceptance testing. Phase three covers training and documentation handover.

3. Commercials
Estimated cost: {PRICE} over eight weeks, invoiced monthly in arrears.
"""

HANDBOOK = """Employee Handbook

Working hours are nine to five, Monday through Friday. Remote work is
permitted up to three days per week with manager approval. All expenses over
fifty dollars require pre-approval, with receipts submitted within thirty days.
"""


def _rows(**files: str) -> list[dict[str, object]]:
    return [
        {
            "source_file": name,
            "content_sketch": content_sketch(text),
            "figures": figure_fingerprint(text),
        }
        for name, text in files.items()
    ]


def test_sketch_is_deterministic_and_ignores_case() -> None:
    assert content_sketch(SOW) == content_sketch(SOW)
    assert content_sketch("Alpha Beta Gamma Delta") == content_sketch("alpha beta gamma delta")


def test_sketch_is_empty_for_text_too_short_to_shingle() -> None:
    assert content_sketch("two words") == []
    # An empty sketch must read as "not comparable", never as "identical".
    assert similarity([], []) == 0.0
    assert similarity(content_sketch(SOW), []) == 0.0


def test_similarity_extremes() -> None:
    assert similarity(content_sketch(SOW), content_sketch(SOW)) == 1.0
    assert similarity(content_sketch(SOW), content_sketch(HANDBOOK)) < 0.1


def test_figure_fingerprint_normalizes_and_skips_noise() -> None:
    figures = figure_fingerprint("Cost is $45,000 and 12 weeks. Phase 1 and Phase 2.")
    assert "45000" in figures
    assert "12" in figures
    # Single digits are list markers far more often than facts.
    assert "1" not in figures and "2" not in figures


def test_reworded_drafts_are_grouped_though_hashes_differ() -> None:
    rows = _rows(
        **{
            "sow.md": SOW.replace("{PRICE}", "$45,000"),
            "sow-v2.md": SOW.replace("{PRICE}", "$52,000"),
        }
    )
    sketches = {str(r["source_file"]): list(r["content_sketch"]) for r in rows}  # type: ignore[arg-type]
    groups = find_near_duplicate_groups(sketches)
    assert len(groups) == 1
    assert groups[0]["files"] == ["sow-v2.md", "sow.md"]


def test_drafts_disagreeing_on_figures_escalate_to_conflict() -> None:
    issues = build_issues(
        _rows(
            **{
                "sow.md": SOW.replace("{PRICE}", "$45,000"),
                "sow-v2.md": SOW.replace("{PRICE}", "$52,000"),
                "sow-FINAL.md": SOW.replace("{PRICE}", "$61,500"),
            }
        )
    )
    assert len(issues) == 1
    issue = issues[0]
    assert issue["kind"] == "near_duplicate_conflict"
    assert issue["severity"] == "review"
    assert set(issue["conflicting_values"]) >= {"45000", "52000", "61500"}  # type: ignore[operator]


def test_identical_figures_stay_cleanup_not_conflict() -> None:
    same = SOW.replace("{PRICE}", "$45,000")
    issues = build_issues(_rows(**{"sow.md": same, "sow-copy.md": same + "\n"}))
    assert len(issues) == 1
    assert issues[0]["kind"] == "near_duplicate"
    assert issues[0]["severity"] == "cleanup"


def test_different_documents_sharing_a_template_are_not_flagged() -> None:
    # The real false-positive risk for a consultancy: one boilerplate, two
    # genuinely separate engagements. These must not be called duplicates.
    template = """Statement of Work
Prepared by Acme Consulting. This document sets out scope, deliverables,
assumptions and commercial terms. All work is subject to the standard terms of
business attached as Appendix A. The client provides timely access to source
systems and a named business owner for sign-off. Change requests follow the
agreed process.

Scope: {SCOPE}
Deliverables: {DELIV}
Estimated cost: {PRICE}
"""
    issues = build_issues(
        _rows(
            **{
                "sow-analytics.md": template.replace("{SCOPE}", "migrate the analytics warehouse and rebuild nightly reporting pipelines")
                .replace("{DELIV}", "migration runbook, validated schema, dashboard")
                .replace("{PRICE}", "$45,000"),
                "sow-portal.md": template.replace("{SCOPE}", "design a customer onboarding portal with identity provider integration")
                .replace("{DELIV}", "wireframes, portal build, single sign on, launch plan")
                .replace("{PRICE}", "$78,000"),
            }
        )
    )
    assert issues == []


def test_exact_duplicates_are_not_reported_twice() -> None:
    same = SOW.replace("{PRICE}", "$45,000")
    rows = _rows(**{"a.md": same, "b.md": same})
    assert build_issues(rows, exclude={"a.md", "b.md"}) == []


def test_end_to_end_report_surfaces_the_conflict(tmp_path) -> None:
    source = tmp_path / "client-corpus"
    source.mkdir()
    (source / "sow.md").write_text(SOW.replace("{PRICE}", "$45,000"), encoding="utf-8")
    (source / "sow-v2.md").write_text(SOW.replace("{PRICE}", "$52,000"), encoding="utf-8")

    report = build_human_report(source, load_config())

    counts = report["diagnostics"]["counts"]
    assert counts["near_duplicate_conflicts"] == 1
    # Exact-duplicate detection alone would have reported nothing here.
    assert counts["duplicate_groups"] == 0
    conflict = next(i for i in report["diagnostics"]["issues"] if i["kind"] == "near_duplicate_conflict")
    assert conflict["impact"]
