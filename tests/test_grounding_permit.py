from __future__ import annotations

from anti_silo.grounding_permit import corpus_evidence_rank, evaluate_grounding_permit
from anti_silo.provenance_opinion import apply_to_verdict, evaluate_provenance_opinion


def _diag(**counts) -> dict:
    return {"counts": counts}


def test_locate_internal_low_grants_at_indexed_tier() -> None:
    counts = {"indexed": 3}
    permit = evaluate_grounding_permit("locate", "internal", "low", counts, _diag())
    assert permit["permission"] == "granted"
    assert permit["granted_authority"] == "locate"


def test_draft_internal_low_grants_at_source_backed_tier() -> None:
    counts = {"backed": 4}
    permit = evaluate_grounding_permit("draft", "internal", "low", counts, _diag())
    assert permit["permission"] == "granted"
    assert permit["granted_authority"] == "draft"


def test_draft_client_requires_source_backed_plus_human_review() -> None:
    # Even fully granted, a client-facing draft always carries the human-review label —
    # the table treats that as part of what "granted" means for this audience.
    counts = {"backed": 2}
    permit = evaluate_grounding_permit("draft", "client", "financial", counts, _diag())
    assert permit["permission"] == "granted"
    assert permit["granted_authority"] == "draft_with_human_review"


def test_advise_client_financial_or_legal_requires_triangulated_only() -> None:
    # A corpus with even one weaker file fails "triangulated only".
    mixed = {"ready": 5, "backed": 1}
    permit = evaluate_grounding_permit("advise", "client", "legal", mixed, _diag())
    assert permit["permission"] != "granted"

    pure = {"ready": 5}
    permit = evaluate_grounding_permit("advise", "client", "legal", pure, _diag())
    assert permit["permission"] == "granted"
    assert permit["granted_authority"] == "advise"


def test_decide_is_never_fully_granted_even_at_perfect_evidence() -> None:
    # Owner/fallback are organizational facts Anti-Silo cannot verify from files.
    counts = {"ready": 10}
    permit = evaluate_grounding_permit("decide", "internal", "safety", counts, _diag())
    assert permit["permission"] == "conditional"
    assert permit["granted_authority"] == "advise"
    assert any("owner" in c or "בעלים" in c for c in permit["upgrade_conditions"])


def test_act_is_always_denied_regardless_of_evidence_or_audience() -> None:
    counts = {"ready": 100}
    permit = evaluate_grounding_permit("act", "external", "safety", counts, _diag())
    assert permit["permission"] == "denied"
    assert permit["granted_authority"] == "none"
    # Even a perfect corpus doesn't change the answer.
    permit_internal = evaluate_grounding_permit("act", "internal", "low", counts, _diag())
    assert permit_internal["permission"] == "denied"


def test_hard_block_denies_regardless_of_requested_authority() -> None:
    counts = {"ready": 10, "contradiction": 1}
    permit = evaluate_grounding_permit("locate", "internal", "low", counts, _diag())
    assert permit["permission"] == "denied"
    assert permit["granted_authority"] == "none"

    counts_no_contradiction = {"ready": 10}
    permit = evaluate_grounding_permit(
        "locate", "internal", "low", counts_no_contradiction, _diag(extraction_failed=1)
    )
    assert permit["permission"] == "denied"


def test_insufficient_evidence_downgrades_rather_than_denies_outright() -> None:
    # advise requires triangulated (rank 3); indexed-only (rank 1) is two below —
    # too far even for a conditional downgrade.
    counts = {"indexed": 5}
    permit = evaluate_grounding_permit("advise", "client", "low", counts, _diag())
    assert permit["permission"] == "denied"

    # one rank below the bar still earns a conditional, downgraded grant
    counts_close = {"backed": 5}
    permit_close = evaluate_grounding_permit("advise", "internal", "low", counts_close, _diag())
    assert permit_close["permission"] == "conditional"
    assert permit_close["granted_authority"] == "draft_with_human_review"


def test_no_evidence_at_all_is_denied() -> None:
    permit = evaluate_grounding_permit("locate", "internal", "low", {}, _diag())
    assert permit["permission"] == "denied"


def test_unknown_inputs_fall_back_to_safe_defaults_rather_than_raising() -> None:
    permit = evaluate_grounding_permit("nonsense", "nonsense", "nonsense", {"ready": 5}, _diag())
    assert permit["requested_authority"] == "locate"
    assert permit["audience"] == "internal"
    assert permit["failure_impact"] == "low"


def test_upgrade_conditions_reflect_actual_gaps_not_boilerplate() -> None:
    counts = {"indexed": 2, "unsupported": 1}
    permit = evaluate_grounding_permit("advise", "client", "low", counts, _diag())
    assert permit["permission"] != "granted"
    joined = " ".join(permit["upgrade_conditions"])
    assert "מקור ראשוני" in joined  # unsupported files need a primary source
    assert "לאמת מקור עצמאי" in joined  # indexed files need independent verification


def test_corpus_evidence_rank_is_the_weakest_link() -> None:
    assert corpus_evidence_rank({"ready": 10, "indexed": 1}, _diag()) == 1
    assert corpus_evidence_rank({"ready": 10}, _diag()) == 3
    assert corpus_evidence_rank({}, _diag()) == -1
    assert corpus_evidence_rank({"ready": 10}, _diag(empty_files=1)) == -1


def test_permit_abstains_when_every_source_is_self_declared() -> None:
    """A corpus that vouches for itself cannot earn a full grant.

    Measured before this guard existed: a fabricated, wholly self-referential
    corpus returned `permit: granted -> locate`. The engine held
    `trust_origin: self_declared` on every row and acted on none of it.
    """
    counts = {"ready": 4}
    self_declared = [{"trust_origin": "self_declared"} for _ in range(4)]

    granted = evaluate_grounding_permit("locate", "internal", "low", counts, _diag())
    assert granted["permission"] == "granted"
    assert granted["provenance_opinion"] == "expressed"

    provenance = evaluate_provenance_opinion(self_declared)
    assert provenance["opinion"] == "disclaimed"
    abstained = evaluate_grounding_permit("locate", "internal", "low", counts, _diag(), provenance)
    assert abstained["permission"] != "granted"
    assert abstained["provenance_opinion"] == "disclaimed"
    assert any("מקור עצמאי" in condition for condition in abstained["upgrade_conditions"])


def test_one_independent_source_restores_the_opinion() -> None:
    """The disclaimer is about having no footing at all, not about weak evidence."""
    mixed = [{"trust_origin": "self_declared"}, {"trust_origin": "operator_attested"}]
    assert evaluate_provenance_opinion(mixed)["opinion"] == "expressed"


def test_rows_without_any_backing_also_disclaim() -> None:
    """An empty trust_origin means no source to judge - not a passed check."""
    provenance = evaluate_provenance_opinion([{"trust_origin": ""}, {}])
    assert provenance["opinion"] == "disclaimed"
    assert provenance["basis"] == "no_backed_rows"


def test_disclaimer_is_carried_on_denied_outcomes_too() -> None:
    """Both early denials return before the disclaimer changes anything.

    They still have to carry the field: a consumer reading it conditionally
    would otherwise print "opinion expressed" on a corpus that earned none.
    """
    provenance = evaluate_provenance_opinion([{"trust_origin": "self_declared"}])
    act = evaluate_grounding_permit("act", "internal", "low", {"ready": 4}, _diag(), provenance)
    blocked = evaluate_grounding_permit("locate", "internal", "low", {"contradiction": 1}, _diag(), provenance)
    assert act["provenance_opinion"] == "disclaimed"
    assert blocked["provenance_opinion"] == "disclaimed"


def test_hygiene_only_verdict_replaces_a_bare_go() -> None:
    """GO must not silently also mean "the sources check out"."""
    clean = {"status": "go", "label": "GO", "title": "t", "summary": "s"}
    disclaimed = evaluate_provenance_opinion([{"trust_origin": "self_declared"}])
    assert apply_to_verdict(clean, disclaimed)["status"] == "go_hygiene_only"

    expressed = evaluate_provenance_opinion([{"trust_origin": "operator_attested"}])
    assert apply_to_verdict(clean, expressed)["status"] == "go"

    # A STOP is already the strictest headline; the disclaimer must not soften it.
    stop = {"status": "stop", "label": "STOP", "title": "t", "summary": "s"}
    assert apply_to_verdict(stop, disclaimed)["status"] == "stop"
