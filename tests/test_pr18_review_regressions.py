from __future__ import annotations

import hashlib

from anti_silo.model import Claim, Surface
from anti_silo.triangulation import _best_source, classify_claim


def _raw_surface(file: str, content: str, *, declared_raw_hash: str = "") -> Surface:
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return Surface(
        file=file,
        surfaces=("source_truth_marker",),
        authority="source_of_truth",
        can_anchor_claim=True,
        content_hash=content_hash,
        raw_source=True,
        raw_source_hash=declared_raw_hash,
    )


def test_misplaced_hash_requires_a_computed_hash_match() -> None:
    """A repeated self-declared raw_source_hash is not proof a real source exists."""
    arbitrary = "a" * 64
    source = _raw_surface("source.md", "real bytes", declared_raw_hash=arbitrary)
    claim = Claim(file="claim.md", text="claim: x", metadata={"raw_source_hash": arbitrary})

    _, reason = _best_source(claim, [source], {"raw_source_only": True})

    assert reason == "source_hash_required_for_raw_source_only"


def test_misplaced_hash_is_diagnosed_when_it_matches_real_content() -> None:
    source = _raw_surface("source.md", "real bytes")
    claim = Claim(
        file="claim.md",
        text="claim: x",
        metadata={"raw_source_hash": source.content_hash},
    )

    matched, reason = _best_source(claim, [source], {"raw_source_only": True})

    assert matched is None
    assert reason == "misplaced_source_hash_use_source_hash_key"


def test_synthesis_keeps_routing_key_and_surfaces_the_one_field_repair() -> None:
    """The actionable diagnosis must not mutate synthesis' canonical routing key."""
    source = _raw_surface("source.md", "real bytes")
    claim = Claim(
        file="summary.md",
        text="synthesis",
        claim_kind="synthesis",
        has_source_spine=False,
        metadata={"raw_source_hash": source.content_hash},
    )

    row = classify_claim(claim, [source], {"raw_source_only": True})

    assert row.tier == "graph_only"
    assert row.reason == "synthesis_without_source_spine"
    assert "raw_source_hash" in row.needs
    assert "source_hash" in row.needs
    assert "תיקון שם-שדה" in row.needs
    assert "misplaced_source_hash_use_source_hash_key" not in row.reason
