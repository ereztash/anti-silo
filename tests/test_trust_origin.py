from __future__ import annotations

import hashlib

from anti_silo.config import load_config
from anti_silo.gui import build_human_report
from anti_silo.index import build_index
from anti_silo.model import OPERATOR_ATTESTED, SELF_DECLARED
from anti_silo.triangulation import build_triangulation


def test_in_corpus_source_marker_is_reported_as_self_declared(tmp_path) -> None:
    # The corpus vouching for itself: a fabricated document, plus a source
    # marker the same author wrote. This reaches source_backed - the tier is
    # about whether an anchor exists - but must never read as verified.
    vault = tmp_path / "vault"
    vault.mkdir()
    junk = vault / "made-up.md"
    junk.write_text("The moon is made of cheese. All figures verified.\n", encoding="utf-8")
    digest = hashlib.sha256(junk.read_bytes()).hexdigest()
    (vault / "my-source.md").write_text(
        f"source_of_truth: true\nraw_source_hash: {digest}\n", encoding="utf-8"
    )
    (vault / "claim.md").write_text(
        f"claim: the moon is made of cheese\nsource_hash: {digest}\ncorroborated: true\n",
        encoding="utf-8",
    )

    claim = next(r for r in build_triangulation(vault, load_config()) if r.file == "claim.md")
    assert claim.trust_origin == SELF_DECLARED


def test_repair_flow_pointer_is_reported_as_operator_attested(tmp_path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "picked-source.md").write_text(
        "type: user_selected_source\nsource_of_truth: true\n"
        f"raw_source_hash: {'a' * 64}\n",
        encoding="utf-8",
    )

    surface = next(r for r in build_index(vault, load_config()) if r.file == "picked-source.md")
    assert surface.trust_origin == OPERATOR_ATTESTED


def test_report_states_who_vouched_next_to_the_tier(tmp_path) -> None:
    source = tmp_path / "corpus"
    source.mkdir()
    (source / "src.md").write_text(
        f"source_of_truth: true\nraw_source_hash: {'b' * 64}\n", encoding="utf-8"
    )
    (source / "claim.md").write_text(
        f"claim: local claim\nsource_hash: {'b' * 64}\n", encoding="utf-8"
    )

    report = build_human_report(source, load_config())
    backed = [r for r in report["rows"] if r["technical_tier"] in {"source_backed", "triangulated"}]
    assert backed, "expected at least one anchored row to carry an origin"
    for row in backed:
        assert row["trust_origin"] == SELF_DECLARED
        # The caveat must travel with the tier, not live only in the README.
        assert row["trust_origin_note"]
