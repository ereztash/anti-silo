from __future__ import annotations

import json
import zipfile
from pathlib import Path

from anti_silo.config import load_config
from anti_silo.gui import build_human_report
from anti_silo.preflight import build_corpus_diagnostics
from anti_silo.projects import ProjectStore, compare_scans, scan_summary
from anti_silo.quick_scan import discard_quick_scan


def test_corpus_diagnostics_finds_duplicates_and_unsupported_files(tmp_path) -> None:
    source = tmp_path / "client-corpus"
    source.mkdir()
    (source / "policy.txt").write_text("same source content", encoding="utf-8")
    (source / "policy-copy.txt").write_text("same source content", encoding="utf-8")
    (source / "slides.pptx").write_bytes(b"not scanned by the current policy")
    ingest_payload = {
        "rows": [
            {"source_file": "policy.txt", "raw_source_hash": "same", "bytes": 19, "extraction_status": "complete"},
            {"source_file": "policy-copy.txt", "raw_source_hash": "same", "bytes": 19, "extraction_status": "complete"},
        ],
        "by_extension": {".txt": 2},
    }

    diagnostics = build_corpus_diagnostics(source, ingest_payload, load_config())

    assert diagnostics["total_files"] == 3
    assert diagnostics["counts"]["unsupported_files"] == 1
    assert diagnostics["counts"]["duplicate_groups"] == 1
    assert diagnostics["counts"]["duplicate_files"] == 1
    assert {row["kind"] for row in diagnostics["issues"]} == {"unsupported_format", "exact_duplicate"}


def test_preflight_report_builds_client_pack_without_local_root_in_client_html(tmp_path) -> None:
    source = tmp_path / "client-corpus"
    source.mkdir()
    (source / "note.txt").write_text("client source note", encoding="utf-8")
    (source / "archive.zip").write_bytes(b"unsupported")
    project = {
        "id": "project-demo",
        "client_name": "Demo Client",
        "project_name": "Knowledge Assistant",
        "consultant_name": "Demo Studio",
    }

    report = build_human_report(source, load_config(), project=project)
    try:
        assert report["verdict"]["status"] == "conditional_go"
        assert report["diagnostics"]["counts"]["unsupported_files"] == 1
        assert report["remediation"]
        assert 0 <= report["readiness_score"]["score"] <= 100
        assert report["risk_register"]
        assert report["executive_summary"]["en"]
        for key in (
            "audit_pack",
            "preflight_summary",
            "remediation_queue",
            "risk_register",
            "scan_delta",
            "sow_ready",
            "client_manifest",
        ):
            assert key in report["downloads"]
            assert Path(report["downloads"][key]).exists()

        client_html = Path(report["downloads"]["html_report"]).read_text(encoding="utf-8")
        assert "Demo Client" in client_html
        assert "Knowledge Assistant" in client_html
        assert str(source.resolve()) not in client_html
        sow_ready = Path(report["downloads"]["sow_ready"]).read_text(encoding="utf-8")
        assert "Readiness Score" in sow_ready
        assert str(source.resolve()) not in sow_ready

        with zipfile.ZipFile(report["downloads"]["audit_pack"]) as archive:
            assert set(archive.namelist()) >= {
                "ANTI_SILO_REPORT.html",
                "PREFLIGHT_SUMMARY.json",
                "REMEDIATION_QUEUE.csv",
                "RISK_REGISTER.csv",
                "SCAN_DELTA.json",
                "SOW_READY.md",
                "CLIENT_SOURCE_MANIFEST.json",
            }
    finally:
        discard_quick_scan(report["staged_vault"])


def test_upsert_defaults_empty_names_for_quick_preflight(tmp_path) -> None:
    # A quick scan (dragged folder, no form input) sends an empty project payload.
    # The store must default the names instead of failing, so no project creation
    # is required for a first verdict.
    source = tmp_path / "portal-docs"
    source.mkdir()
    store = ProjectStore(tmp_path / "projects.json")
    project = store.upsert({}, source)
    assert project["client_name"] == "לקוח"
    assert project["project_name"] == "portal-docs"
    assert project["id"]


def test_project_store_records_summary_and_produces_scan_delta(tmp_path) -> None:
    source = tmp_path / "client"
    source.mkdir()
    store = ProjectStore(tmp_path / "projects.json")
    project = store.upsert(
        {"client_name": "Client", "project_name": "RAG", "consultant_name": "Studio"},
        source,
    )
    first_report = {
        "generated_at": "2026-07-17T10:00:00+00:00",
        "verdict": {"status": "conditional_go"},
        "files": 3,
        "counts": {"ready": 1, "indexed": 2, "unsupported": 0, "contradiction": 0},
        "diagnostics": {"counts": {"duplicate_files": 1}},
        "readiness_score": {"score": 41},
        "scope_impact": {"total": 3, "ready": 1, "review": 2, "blocked": 0},
    }
    store.record_scan(project["id"], first_report)
    previous = store.latest_scan(project["id"])
    current_report = {
        "generated_at": "2026-07-17T11:00:00+00:00",
        "verdict": {"status": "go"},
        "files": 3,
        "counts": {"ready": 3, "indexed": 0, "unsupported": 0, "contradiction": 0},
        "diagnostics": {"counts": {"duplicate_files": 0}},
        "readiness_score": {"score": 78},
        "scope_impact": {"total": 3, "ready": 3, "review": 0, "blocked": 0},
    }
    delta = compare_scans(previous, scan_summary(current_report))

    assert delta == {
        "has_previous": True,
        "previous_scanned_at": "2026-07-17T10:00:00+00:00",
        "ready": 2,
        "review": -2,
        "blocked": 0,
        "corpus_issues": -1,
        "readiness_score": 37,
        "previous": {
            "readiness_score": 41,
            "ready": 1,
            "review": 2,
            "blocked": 0,
            "corpus_issues": 1,
        },
        "current": {
            "readiness_score": 78,
            "ready": 3,
            "review": 0,
            "blocked": 0,
            "corpus_issues": 0,
        },
    }
    assert store.list_projects()[0]["scan_count"] == 1
    saved = json.loads((tmp_path / "projects.json").read_text(encoding="utf-8"))
    assert saved["projects"][0]["source_root"] == str(source.resolve())


def test_project_store_accepts_windows_utf8_bom(tmp_path) -> None:
    path = tmp_path / "projects.json"
    path.write_text('{"schema_version": 1, "projects": []}\n', encoding="utf-8-sig")

    assert ProjectStore(path).list_projects() == []
