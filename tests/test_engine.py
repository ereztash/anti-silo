from __future__ import annotations

import hashlib
import tomllib
from pathlib import Path

import anti_silo
from anti_silo.brain import BrainStore
from anti_silo.config import load_config
from anti_silo.contradiction import build_contradiction_penalties
from anti_silo.evidence_queue import build_queue
from anti_silo.eligible import build_eligible_sources, build_internal_grounding_candidates
from anti_silo.gui import HTML, build_human_report
from anti_silo.ingest import write_ingest
from anti_silo.index import build_index
from anti_silo.pulse import write_pulse
from anti_silo.promotion import build_enforcement
from anti_silo.quick_scan import discard_quick_scan, run_quick_scan
from anti_silo.repair import RepairStore
from anti_silo.report_labels import tier_label
from anti_silo.telemetry import LocalTelemetry
from anti_silo.spine import build_source_spine_todos
from anti_silo.triangulation import build_triangulation
from anti_silo.scanner import scan_claims
from anti_silo.watch import WatchStore


ROOT = Path(__file__).resolve().parents[1]
VAULT = ROOT / "examples" / "mini_vault"


def test_runtime_version_matches_project_version() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert anti_silo.__version__ == project["project"]["version"]


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
    assert "raw_source_hash" in pricing.reason


def test_raw_source_only_blocks_hash_to_derived_surface(tmp_path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    ledger = vault / "corroboration-ledger.md"
    ledger.write_text("corroboration ledger\nclaim: derived support\nledger: true\n", encoding="utf-8")
    digest = hashlib.sha256(ledger.read_bytes()).hexdigest()
    (vault / "claim.md").write_text(f"claim: local claim\nsource_hash: {digest}\n", encoding="utf-8")

    rows = build_triangulation(vault, load_config())
    claim = next(row for row in rows if row.file == "claim.md")
    assert claim.tier == "graph_only"
    assert claim.source == ""
    assert claim.reason == "claim only; source_hash_matches_non_raw_surface"


def test_raw_source_registry_hash_can_anchor_claim(tmp_path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    raw_hash = "a" * 64
    (vault / "raw-source-pointer.md").write_text(
        f"source_of_truth: true\nraw_source_hash: {raw_hash}\nsource_anchor: BZ/source-001\n",
        encoding="utf-8",
    )
    (vault / "claim.md").write_text(f"claim: local claim\nsource_hash: {raw_hash}\n", encoding="utf-8")

    rows = build_triangulation(vault, load_config())
    claim = next(row for row in rows if row.file == "claim.md")
    assert claim.tier == "source_backed"
    assert claim.source == "raw-source-pointer.md"
    assert claim.source_hash == raw_hash
    assert claim.reason == "claim + raw_source_hash"


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


def test_pulse_declares_trust_boundary(tmp_path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "source.md").write_text("source_of_truth: true\ncorroborated\n", encoding="utf-8")
    (vault / "claim.md").write_text("claim: local claim\nsource_hash: missing\ncorroborated\n", encoding="utf-8")

    config = {**load_config(), "output_dir": "out"}
    payload = write_pulse(vault, config)
    pulse_md = (vault / "out" / "PULSE.md").read_text(encoding="utf-8")
    eligible_json = (vault / "out" / "eligible_sources.json").read_text(encoding="utf-8")

    assert "trust_boundary" in payload
    assert "does not measure product usage" in pulse_md
    assert "user value" in eligible_json


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


def test_blocked_marker_ignores_relation_names_like_cites_refuted(tmp_path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "claim.md").write_text("claim: local claim\nrelation: cites_refuted\nstatus: active\n", encoding="utf-8")

    rows = build_triangulation(vault, load_config())
    claim = next(row for row in rows if row.file == "claim.md")
    assert claim.tier != "refuted_or_blocked"


def test_blocked_marker_still_honors_status_field(tmp_path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "claim.md").write_text("claim: local claim\nstatus: refuted\n", encoding="utf-8")

    rows = build_triangulation(vault, load_config())
    claim = next(row for row in rows if row.file == "claim.md")
    assert claim.tier == "refuted_or_blocked"


def test_ingest_stages_source_documents_as_unverified_intake(tmp_path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "note.txt").write_text("source_hash: stale\nlocal source note", encoding="utf-8")
    staged = tmp_path / "staged"

    payload = write_ingest(source, load_config(), staged)
    staged_note = staged / "note.md"
    assert payload["files"] == 1
    assert staged_note.exists()
    text = staged_note.read_text(encoding="utf-8")
    assert "intake_kind: self_indexed" in text
    assert "raw_source_hash:" not in text
    assert "claim: extracted document content" in text
    assert (staged / "SOURCE_MANIFEST.json").exists()
    row = next(row for row in build_triangulation(staged, load_config()) if row.file == "note.md")
    assert row.tier == "indexed_unverified"


def test_pulse_names_source_backed_only_block_as_pending_corroboration(tmp_path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    source = vault / "source.md"
    source.write_text("source_of_truth: true\nraw source bytes\n", encoding="utf-8")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    (vault / "claim.md").write_text(f"claim: local claim\nsource_hash: {digest}\n", encoding="utf-8")

    config = {**load_config(), "output_dir": "out"}
    payload = write_pulse(vault, config)
    assert payload["decision"] == "source_backed_pending_corroboration"


def test_gui_human_report_translates_tiers_for_nontechnical_users(tmp_path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "note.txt").write_text("local source note", encoding="utf-8")
    staged = tmp_path / "staged"

    report = build_human_report(source, load_config(), output_vault=staged)
    assert report["files"] == 1
    assert report["counts"]["indexed"] == 1
    assert report["rows"][0]["status"] == "נסרק, טרם אומת"
    assert report["rows"][0]["technical_tier"] == "indexed_unverified"
    assert report["rows"][0]["action"]
    assert report["temporary"] is False
    assert "html_report" in report["downloads"]
    assert "manifest" in report["downloads"]
    assert Path(report["downloads"]["html_report"]).exists()


def test_gui_quick_scan_preserves_structured_vault_provenance() -> None:
    report = build_human_report(VAULT, load_config())
    try:
        assert report["input_mode"] == "structured_vault"
        assert report["counts"]["ready"] == 1
        pricing = next(row for row in report["rows"] if row["file"].endswith("pricing.md"))
        assert pricing["technical_tier"] == "triangulated"
    finally:
        discard_quick_scan(report["staged_vault"])


def test_gui_repair_link_changes_document_from_indexed_to_source_backed(tmp_path) -> None:
    source = tmp_path / "documents"
    source.mkdir()
    (source / "note.txt").write_text("local claim", encoding="utf-8")
    independent_source = tmp_path / "independent-source.md"
    independent_source.write_text("independent source material", encoding="utf-8")
    repairs = RepairStore(tmp_path / "repairs.json")
    repairs.add(source, "note.txt", independent_source)

    report = build_human_report(source, load_config(), repair_store=repairs)
    try:
        assert report["input_mode"] == "document_folder"
        assert report["counts"]["indexed"] == 0
        assert report["counts"]["backed"] == 1
        assert report["rows"][0]["technical_tier"] == "source_backed"
    finally:
        discard_quick_scan(report["staged_vault"])


def test_gui_html_exposes_shelf_product_controls() -> None:
    assert "dropzone" in HTML
    assert "שמור דוח HTML" in HTML
    assert "הפעולה הבאה" in HTML
    assert "הצג פרטים למתקדמים" in HTML
    assert "__CSRF_TOKEN__" in HTML
    assert "attachSource" in HTML
    assert "exitApp" in HTML
    assert "escapeHtml(row.file)" in HTML
    assert "גבול אמון" in HTML


def test_ingest_extraction_failure_and_truncation_create_hard_blocks(tmp_path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "large.csv").write_text("\n".join(f"{index},value" for index in range(250)), encoding="utf-8")
    staged = tmp_path / "staged"

    write_ingest(source, load_config(), staged)
    payload = write_pulse(staged, {**load_config(), "output_dir": "out"})
    assert payload["triangulation"]["indexed_unverified"] == 1
    assert payload["contradiction_penalty"]["hard_blocks"] == 1
    assert payload["contradiction_penalty"]["by_rule"]["extraction_truncated"] == 1
    assert payload["decision"] == "blocked"


def test_quick_scan_uses_temporary_staging_and_localized_outputs(tmp_path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "note.txt").write_text("local source note", encoding="utf-8")

    payload = run_quick_scan(source, load_config(), lang="he")
    staged = Path(payload["staged_vault"])
    try:
        assert payload["temporary"] is True
        assert staged.exists()
        assert "pulse_he_json" in payload["localized_outputs"]
        assert tier_label("graph_only", "he") == "ללא_תימוכין"
    finally:
        discard_quick_scan(staged)
    assert not staged.exists()


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


def test_cor_sys_profile_marks_source_backed_as_review_candidate(tmp_path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    source = vault / "source.md"
    source.write_text("source_of_truth: true\nraw source bytes\n", encoding="utf-8")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    (vault / "claim.md").write_text(f"claim: local claim\nsource_hash: {digest}\n", encoding="utf-8")

    config = load_config()
    config["candidate_tiers"] = ["source_backed"]
    config["promotion_policy"] = {
        "blocked_tiers": ["graph_only", "corroborated_no_source", "ledger_supported", "refuted_or_blocked"],
        "review_tiers": ["source_backed"],
    }
    rows = build_enforcement(vault, config)
    assert any(row.decision == "review" and row.tier == "source_backed" for row in rows)


def test_internal_grounding_candidates_are_separate_from_eligible_sources(tmp_path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    eligible_source = vault / "eligible-source.md"
    eligible_source.write_text("source_of_truth: true\neligible raw source\n", encoding="utf-8")
    eligible_digest = hashlib.sha256(eligible_source.read_bytes()).hexdigest()
    candidate_source = vault / "candidate-source.md"
    candidate_source.write_text("source_of_truth: true\ncandidate raw source\n", encoding="utf-8")
    candidate_digest = hashlib.sha256(candidate_source.read_bytes()).hexdigest()
    (vault / "eligible-claim.md").write_text(
        f"claim: triangulated claim\nsource_hash: {eligible_digest}\ncorroborated\n",
        encoding="utf-8",
    )
    (vault / "candidate-claim.md").write_text(
        f"claim: source backed claim\nsource_hash: {candidate_digest}\n",
        encoding="utf-8",
    )

    config = load_config()
    config["candidate_tiers"] = ["source_backed"]
    eligible = build_eligible_sources(vault, config)
    candidates = build_internal_grounding_candidates(vault, config)
    assert eligible
    assert candidates
    assert all(row["eligible_for"] == "internal_grounding_candidate" for row in candidates)


def test_contradiction_penalty_flags_outcome_without_raw_source(tmp_path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "claim.md").write_text(
        "claim: local outcome claim\noutcome: value_realized\n",
        encoding="utf-8",
    )

    rows = build_contradiction_penalties(vault, load_config())
    claim = next(row for row in rows if row["file"] == "claim.md")
    assert claim["penalty_score"] >= 4
    assert "outcome_without_raw_source" in claim["rules"]
    assert claim["decision"] == "review_required"


def test_contradiction_hard_block_overrides_review_tier(tmp_path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "claim.md").write_text(
        "claim: local claim\ndecision_changed: yes\noutcome: value_realized\n",
        encoding="utf-8",
    )

    config = load_config()
    config["candidate_tiers"] = ["graph_only"]
    config["promotion_policy"] = {
        "blocked_tiers": [],
        "review_tiers": ["graph_only"],
    }
    config["contradiction_penalty"] = {
        "enabled": True,
        "hard_block_threshold": 6,
        "weights": {
            "outcome_without_raw_source": 4,
            "decision_without_raw_source": 5,
            "graph_only_no_lineage": 1,
            "temporal_without_lineage": 1,
            "lineage_without_raw_source": 2,
            "corroborated_without_raw_source": 3,
            "usage_without_raw_source": 5,
            "refuted_or_blocked": 8,
        },
    }

    rows = build_enforcement(vault, config)
    claim = next(row for row in rows if row.file == "claim.md")
    assert claim.decision == "block"
    assert "contradiction penalty hard block" in claim.reason


def test_brain_preserves_source_trust_and_reviews_unsupported_decisions(tmp_path) -> None:
    store = BrainStore(tmp_path / "brain")
    report = {
        "source_root": str(tmp_path / "sources"),
        "rows": [
            {
                "file": "verified.md",
                "technical_tier": "triangulated",
                "status": "verified",
                "action": "ready",
                "explanation": "raw source and corroboration",
            },
            {
                "file": "draft.md",
                "technical_tier": "indexed_unverified",
                "status": "indexed only",
                "action": "review",
                "explanation": "missing source evidence",
            },
        ],
    }

    assert store.import_scan_report(report) == {"added": 2, "skipped": 0}
    assert store.import_scan_report(report) == {"added": 0, "skipped": 2}
    dashboard = store.dashboard()
    assert dashboard["counts"]["sources"] == 2
    assert dashboard["counts"]["trusted_sources"] == 1

    unsupported = store.add_entry(kind="decision", title="unsupported decision")
    assert unsupported["decision_status"] == "draft_requires_sources"
    trusted_source = next(entry for entry in store.entries() if entry.get("trust_tier") == "triangulated")
    supported = store.add_entry(kind="decision", title="supported decision", source_ids=[trusted_source["id"]])
    missing_link = store.add_entry(
        kind="decision",
        title="decision with a missing source",
        source_ids=[trusted_source["id"], "entry-missing"],
    )

    queued_ids = {item["id"] for item in store.review_queue()}
    assert any(item["title"] == "unsupported decision" for item in store.review_queue())
    assert supported["decision_status"] == "supported"
    assert supported["id"] not in queued_ids
    assert missing_link["decision_status"] == "needs_source_review"
    assert missing_link["id"] in queued_ids


def test_watch_store_detects_local_change_and_records_scan_result(tmp_path) -> None:
    watched = tmp_path / "watched"
    watched.mkdir()
    (watched / "first.txt").write_text("first", encoding="utf-8")
    store = WatchStore(tmp_path / "watchlist.json")
    store.add(watched)

    assert store.check() == []
    (watched / "second.txt").write_text("second", encoding="utf-8")
    events = store.check(lambda path: {"files": 2, "counts": {"indexed": 2}})

    assert len(events) == 1
    assert events[0]["kind"] == "changed"
    assert events[0]["report"]["files"] == 2
    assert store.dashboard()["events"][0]["path"] == str(watched.resolve())


def test_local_telemetry_never_records_file_paths_or_titles(tmp_path) -> None:
    telemetry = LocalTelemetry(tmp_path / "events.jsonl")
    telemetry.record("first_scan_completed", files=3, path="C:/private", title="private note")
    telemetry.record("scan_completed", files=3)
    telemetry.record("scan_completed", files=4)

    record = telemetry.events()[0]
    assert record["event"] == "first_scan_completed"
    assert record["properties"] == {"files": 3}
    assert telemetry.has_event("first_scan_completed")
    assert telemetry.summary() == {"first_scan_completed": 1, "scan_completed": 2}
