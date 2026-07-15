from __future__ import annotations

from pathlib import Path

from anti_silo.config import load_config
from anti_silo.evidence_queue import build_queue
from anti_silo.eligible import build_eligible_sources
from anti_silo.index import build_index
from anti_silo.promotion import build_enforcement
from anti_silo.spine import build_source_spine_todos
from anti_silo.triangulation import build_triangulation


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
