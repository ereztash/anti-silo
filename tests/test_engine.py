from __future__ import annotations

from pathlib import Path

from anti_silo.config import load_config
from anti_silo.evidence_queue import build_queue
from anti_silo.eligible import build_eligible_sources, build_internal_grounding_candidates
from anti_silo.index import build_index
from anti_silo.promotion import build_enforcement
from anti_silo.spine import build_source_spine_todos
from anti_silo.triangulation import build_triangulation
from anti_silo.scanner import scan_claims


ROOT = Path(__file__).resolve().parents[1]
VAULT = ROOT / "examples" / "mini_vault"


def test_truth_surface_index_finds_sources() -> None:
    rows = build_index(VAULT, load_config())
    assert len(rows) >= 2
    assert any(row.can_anchor_claim for row in rows)


def test_triangulation_has_multiple_tiers() -> None:
    rows = build_triangulation(VAULT, load_config())
    tiers = {row.tier for row in rows}
    assert "triangulated" in tiers
    assert "graph_only" in tiers or "ledger_supported" in tiers


def test_queue_skips_triangulated_claims() -> None:
    queue = build_queue(VAULT, load_config())
    assert queue
    assert all(row["tier"] != "triangulated" for row in queue)


def test_hash_source_link_is_recorded() -> None:
    rows = build_triangulation(VAULT, load_config())
    pricing = next(row for row in rows if row.file.endswith("pricing.md"))
    assert pricing.tier == "triangulated"
    assert pricing.source_hash == "633d46b681a1abe245cac00dd25206ca869f6ee5344f19f9021282bbedaffc8e"
    assert "source_hash" in pricing.reason


def test_promotion_gate_blocks_weak_tiers() -> None:
    rows = build_enforcement(VAULT, load_config())
    assert any(row.decision == "block" and row.tier == "graph_only" for row in rows)
    assert any(row.decision == "allow" and row.tier == "triangulated" for row in rows)


def test_synthesis_without_source_spine_gets_specific_reason() -> None:
    rows = build_triangulation(VAULT, load_config())
    synthesis = next(row for row in rows if row.file.endswith("research-synthesis.md"))
    assert synthesis.claim_kind == "synthesis"
    assert synthesis.tier == "graph_only"
    assert synthesis.reason == "synthesis_without_source_spine"
    assert "source spine" in synthesis.needs


def test_queue_routes_synthesis_to_source_spine_backfill() -> None:
    queue = build_queue(VAULT, load_config())
    synthesis = next(row for row in queue if row["file"].endswith("research-synthesis.md"))
    assert synthesis["upgrade_path"] == "source_spine_backfill"
    assert "bibliography" in synthesis["required_evidence"]


def test_eligible_sources_exports_only_allowed_grounding_sources() -> None:
    rows = build_eligible_sources(VAULT, load_config())
    assert rows
    assert any(row["source"].endswith("pricing-source.md") for row in rows)
    assert all(row["eligible_for"] == "grounding" for row in rows)


def test_source_spine_todo_contains_template_for_synthesis() -> None:
    rows = build_source_spine_todos(VAULT, load_config())
    synthesis = next(row for row in rows if row["file"].endswith("research-synthesis.md"))
    assert "source_hash" in synthesis["required_metadata"]
    assert synthesis["template"][0] == "source_spine:"


def test_include_profile_matches_vault_root_name(tmp_path) -> None:
    vault = tmp_path / "סוכנים"
    vault.mkdir()
    claim = vault / "agent.md"
    claim.write_text("claim: local agent rule\nstatus: draft\n", encoding="utf-8")
    config = {**load_config(), "include_dirs": ["סוכנים"]}
    rows = scan_claims(vault, config)
    assert [row.file for row in rows] == ["agent.md"]


def test_research_library_indexes_pdf_and_html_without_text_parsing(tmp_path) -> None:
    vault = tmp_path / "מאמרים מעניינים"
    vault.mkdir()
    (vault / "paper.pdf").write_bytes(b"%PDF-1.4\nlocal article bytes\n")
    (vault / "article.html").write_text("<html><body>article</body></html>", encoding="utf-8")
    rows = build_index(vault, load_config())
    by_file = {row.file: row for row in rows}
    assert {"paper.pdf", "article.html"} <= set(by_file)
    assert by_file["paper.pdf"].can_anchor_claim
    assert "research_library_source" in by_file["paper.pdf"].surfaces
    assert len(by_file["paper.pdf"].content_hash) == 64


def test_cor_sys_profile_marks_source_backed_as_review_candidate() -> None:
    config = load_config()
    config["candidate_tiers"] = ["source_backed"]
    config["promotion_policy"] = {
        "blocked_tiers": ["graph_only", "corroborated_no_source", "ledger_supported", "refuted_or_blocked"],
        "review_tiers": ["source_backed"],
    }
    rows = build_enforcement(VAULT, config)
    assert any(row.decision == "review" and row.tier == "source_backed" for row in rows)


def test_internal_grounding_candidates_are_separate_from_eligible_sources() -> None:
    config = load_config()
    config["candidate_tiers"] = ["source_backed"]
    eligible = build_eligible_sources(VAULT, config)
    candidates = build_internal_grounding_candidates(VAULT, config)
    assert eligible
    assert candidates
    assert all(row["eligible_for"] == "internal_grounding_candidate" for row in candidates)
