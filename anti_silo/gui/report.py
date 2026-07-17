from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import output_dir
from ..ingest import write_ingest
from ..preflight import build_corpus_diagnostics, build_remediation, build_verdict
from ..preflight_artifacts import client_manifest, write_preflight_artifacts
from ..projects import compare_scans
from ..pulse import write_pulse
from ..quick_scan import discard_quick_scan, run_quick_scan
from ..repair import RepairStore
from ..report_labels import action_label
from .client_report import render_report_html
from .labels import CATEGORY_LABELS, HUMAN_TIERS


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _source_lookup(ingest_payload: dict[str, Any]) -> dict[str, str]:
    return {str(row["staged_file"]): str(row["source_file"]) for row in ingest_payload.get("rows", [])}


def _penalty_lookup(penalty_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row["file"]): row for row in penalty_payload.get("rows", [])}


def _human_row(row: dict[str, Any], sources: dict[str, str], penalties: dict[str, dict[str, Any]]) -> dict[str, Any]:
    tier = str(row.get("tier", "graph_only"))
    reason = str(row.get("reason", ""))
    category, label, explanation = HUMAN_TIERS.get(tier, ("unsupported", tier, "דורש בדיקה ידנית."))
    if tier == "graph_only" and reason == "synthesis_without_source_spine":
        category = "synthesis"
        label = "סיכום, לא מקור ראשוני"
        explanation = "זה נראה כמו סיכום או מסגרת חשיבה, אבל חסרה רשימת מקורות מסודרת."

    penalty = penalties.get(str(row.get("file", "")), {})
    if penalty.get("hard_block") is True:
        category = "contradiction"
        label = "חסם אמון"
        explanation = "נמצאה בעיית אמון שמונעת הסתמכות לפני תיקון."

    return {
        "file": sources.get(str(row.get("file", "")), row.get("file", "")),
        "staged_file": row.get("file", ""),
        "category": category,
        "category_label": CATEGORY_LABELS.get(category, category),
        "status": label,
        "action": action_label(category, "he"),
        "explanation": explanation,
        "technical_tier": tier,
        "technical_reason": reason,
        "needs": row.get("needs", ""),
        "penalty_rules": penalty.get("rules", []),
    }


def build_human_report(
    source_root: Path,
    config: dict[str, Any],
    output_vault: Path | None = None,
    repair_store: RepairStore | None = None,
    project: dict[str, Any] | None = None,
    previous_scan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    quick_payload: dict[str, Any] | None = None
    if output_vault is None:
        quick_payload = run_quick_scan(source_root, config, lang="he", repair_store=repair_store)
        ingest_payload = quick_payload["ingest"]
        staged_vault = Path(str(quick_payload["staged_vault"]))
        pulse_payload = quick_payload["pulse"]
    else:
        ingest_payload = write_ingest(source_root, config, output_vault=output_vault)
        staged_vault = Path(str(ingest_payload["output_vault"]))
        pulse_payload = write_pulse(staged_vault, config)
    out = output_dir(staged_vault, config)
    triangulation = _read_json(out / "triangulation_gate.json")
    penalties = _read_json(out / "contradiction_penalty.json")

    sources = _source_lookup(ingest_payload)
    penalty_by_file = _penalty_lookup(penalties)
    rows = [_human_row(row, sources, penalty_by_file) for row in triangulation.get("rows", [])]
    counts = {key: 0 for key in CATEGORY_LABELS}
    for row in rows:
        counts[row["category"]] = counts.get(row["category"], 0) + 1

    diagnostics = build_corpus_diagnostics(source_root, ingest_payload, config)
    verdict = build_verdict(counts, diagnostics)
    remediation = build_remediation(rows, diagnostics)
    review_count = sum(int(counts.get(key, 0)) for key in ("backed", "indexed", "synthesis"))
    review_count += int(diagnostics.get("counts", {}).get("unsupported_files", 0))
    review_count += int(diagnostics.get("counts", {}).get("duplicate_groups", 0))
    blocked_count = int(counts.get("unsupported", 0)) + int(counts.get("contradiction", 0))
    current_summary = {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "counts": counts,
        "diagnostic_counts": diagnostics.get("counts", {}),
    }

    report: dict[str, Any] = {
        "generated_at": current_summary["scanned_at"],
        "project": dict(project or {}),
        "source_root": str(Path(source_root).resolve()),
        "staged_vault": str(staged_vault),
        "output_dir": str(out),
        "decision": pulse_payload["decision"],
        "trust_boundary": "הבדיקה בוחנת שרשרת מקורות ושלמות חילוץ. היא אינה קובעת שהטקסט נכון מבחינה מקצועית או עובדתית.",
        "files": ingest_payload["files"],
        "counts": counts,
        "rows": rows,
        "verdict": verdict,
        "scope_impact": {
            "total": int(diagnostics.get("total_files", ingest_payload["files"])),
            "ready": int(counts.get("ready", 0)),
            "review": review_count,
            "blocked": blocked_count,
        },
        "diagnostics": diagnostics,
        "remediation": remediation,
        "delta": compare_scans(previous_scan, current_summary),
        "client_manifest": client_manifest(ingest_payload),
        "temporary": quick_payload is not None,
        "input_mode": quick_payload.get("input_mode", "structured_vault") if quick_payload else "structured_vault",
    }
    report_path = out / "ANTI_SILO_REPORT.html"
    report_path.write_text(render_report_html(report), encoding="utf-8")
    downloads = {
        "html_report": report_path,
        "allowed_sources": out / "eligible_sources.csv",
        "source_todo": out / "source_spine_todo.csv",
        "pulse_markdown": out / "PULSE.md",
        "manifest": staged_vault / "SOURCE_MANIFEST.json",
        **write_preflight_artifacts(report, out),
    }
    if quick_payload:
        for key, value in quick_payload.get("localized_outputs", {}).items():
            downloads[key] = Path(value)
    report["downloads"] = {name: str(path) for name, path in downloads.items() if path.exists()}
    report["repair_todo_count"] = int(_read_json(out / "source_spine_todo.json").get("selected", 0))
    return report


def _watch_scan(root: Path, config: dict[str, Any], repair_store: RepairStore | None = None) -> dict[str, Any]:
    report = build_human_report(root, config, repair_store=repair_store)
    try:
        return {"files": report["files"], "counts": report["counts"]}
    finally:
        if report.get("temporary"):
            discard_quick_scan(str(report["staged_vault"]))
