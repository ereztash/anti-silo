from __future__ import annotations

from pathlib import Path

from anti_silo.config import load_config
from anti_silo.evidence_queue import build_queue
from anti_silo.index import build_index
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
