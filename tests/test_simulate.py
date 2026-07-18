from __future__ import annotations

from anti_silo.simulate import simulate_readiness


def _report() -> dict:
    # 10 files: 4 ready, 2 unsupported (no source), 1 contradiction, plus diagnostics.
    return {
        "counts": {"ready": 4, "backed": 0, "indexed": 0, "synthesis": 0, "unsupported": 2, "contradiction": 1},
        "readiness_score": {"score": 40, "go_threshold": 85},
        "diagnostics": {
            "total_files": 10,
            "ingested_files": 10,
            "counts": {"duplicate_files": 2, "extraction_failed": 1},
            "issues": [
                {"kind": "exact_duplicate", "severity": "cleanup", "file": "a.md", "related_files": ["b.md"]},
                {"kind": "extraction_failed", "severity": "block", "file": "scan.pdf"},
            ],
        },
    }


def test_no_resolutions_reproduces_the_baseline_deterministically() -> None:
    base = simulate_readiness(_report(), [])
    again = simulate_readiness(_report(), [])
    assert base == again
    assert base["readiness_score"]["go_threshold"] == 85


def test_add_source_is_realistic_backed_not_ready() -> None:
    # Marking an unsupported file "add_source" moves it to source-backed (75), not
    # ready (100) — a projected GO must not over-promise.
    projected = simulate_readiness(_report(), [{"category": "unsupported", "action": "add_source"}])
    assert projected["readiness_score"]["score"] > 40  # improved
    # explicit full verification lands higher than adding a source alone
    verified = simulate_readiness(_report(), [{"category": "unsupported", "action": "verify"}])
    assert verified["readiness_score"]["score"] > projected["readiness_score"]["score"]


def test_resolving_all_blocks_can_lift_the_verdict_off_stop() -> None:
    base = simulate_readiness(_report(), [])
    assert base["verdict"]["status"] == "stop"
    projected = simulate_readiness(
        _report(),
        [
            {"category": "unsupported", "action": "verify"},
            {"category": "unsupported", "action": "verify"},
            {"category": "contradiction", "action": "resolve"},
            {"category": "extraction_failed", "action": "replace"},
        ],
    )
    assert projected["verdict"]["status"] != "stop"


def test_duplicate_group_removes_all_extra_copies_from_penalty() -> None:
    projected = simulate_readiness(_report(), [{"category": "exact_duplicate", "action": "dedupe"}])
    # the duplicate penalty is gone -> score at least as high as baseline
    assert projected["readiness_score"]["score"] >= simulate_readiness(_report(), [])["readiness_score"]["score"]


def test_unknown_category_or_action_is_ignored_or_defaulted() -> None:
    # unknown category is a no-op; unknown action falls back to the category default
    noop = simulate_readiness(_report(), [{"category": "not_a_thing", "action": "x"}])
    assert noop == simulate_readiness(_report(), [])
    defaulted = simulate_readiness(_report(), [{"category": "unsupported", "action": "bogus"}])
    assert defaulted == simulate_readiness(_report(), [{"category": "unsupported", "action": "add_source"}])
