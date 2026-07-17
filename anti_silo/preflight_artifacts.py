from __future__ import annotations

import csv
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def client_manifest(ingest_payload: dict[str, Any]) -> dict[str, Any]:
    rows = [
        {
            "file": row.get("source_file", ""),
            "extension": row.get("extension", ""),
            "sha256": row.get("raw_source_hash", ""),
            "bytes": row.get("bytes", 0),
            "extraction_status": row.get("extraction_status", "not_applicable"),
            "extraction_note": row.get("extraction_note", ""),
            "linked_source": row.get("linked_source", ""),
        }
        for row in ingest_payload.get("rows", [])
    ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files": len(rows),
        "by_extension": ingest_payload.get("by_extension", {}),
        "rows": rows,
    }


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _markdown_cell(value: Any) -> str:
    return " ".join(str(value or "").replace("|", "\\|").split())


def _sow_ready_markdown(report: dict[str, Any]) -> str:
    project = dict(report.get("project", {}))
    readiness = dict(report.get("readiness_score", {}))
    scope = dict(report.get("scope_impact", {}))
    effort = dict(report.get("effort_estimate", {}))
    executive = dict(report.get("executive_summary", {}))
    risks = [risk for risk in report.get("risk_register", []) if risk.get("severity") in {"High", "Medium"}]
    risk_rows = [
        f"| {_markdown_cell(risk.get('risk_id'))} | {_markdown_cell(risk.get('category'))} | "
        f"{_markdown_cell(risk.get('file'))} | {_markdown_cell(risk.get('severity'))} | "
        f"{_markdown_cell(risk.get('recommendation'))} |"
        for risk in risks
    ] or ["| - | No material risks | - | - | No remediation line item required |"]
    return "\n".join(
        [
            f"# RAG Preflight Scope Input: {_markdown_cell(project.get('project_name', 'Client Project'))}",
            "",
            f"**Client:** {_markdown_cell(project.get('client_name', 'Client'))}",
            f"**Prepared by:** {_markdown_cell(project.get('consultant_name', 'AI Consultant'))}",
            f"**Generated:** {_markdown_cell(str(report.get('generated_at', ''))[:10])}",
            "",
            "> Planning input generated from a deterministic local source audit. Validate complexity and commercial terms before quoting.",
            "",
            "## Executive Summary",
            "",
            str(executive.get("en", "")),
            "",
            "## Readiness and Scope",
            "",
            f"- Readiness Score: **{int(readiness.get('score', 0))}/100** ({_markdown_cell(readiness.get('label'))})",
            f"- Preflight Verdict: **{_markdown_cell(report.get('verdict', {}).get('label'))}**",
            f"- Files in scope: **{int(scope.get('total', 0))}**",
            f"- Grounding eligible now: **{int(readiness.get('grounding_eligible_pct', 0))}%**",
            f"- Files requiring review: **{int(scope.get('review', 0))}**",
            f"- Blocked files: **{int(scope.get('blocked', 0))}**",
            "",
            "## Material Risk Register",
            "",
            "| Risk ID | Category | File | Severity | Recommendation |",
            "|---|---|---|---|---|",
            *risk_rows,
            "",
            "## Remediation Planning Range",
            "",
            f"**{int(effort.get('minimum_hours', 0))}-{int(effort.get('maximum_hours', 0))} hours**",
            "",
            str(effort.get("assumption", "")),
            "",
            "## Recommended SOW Language",
            "",
            "The implementation scope should begin with the remediation items above, followed by a repeat Anti-Silo Preflight. "
            "Only sources that pass the agreed grounding policy should proceed to chunking, indexing, and retrieval evaluation.",
            "",
        ]
    )


def write_preflight_artifacts(report: dict[str, Any], output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "PREFLIGHT_SUMMARY.json"
    remediation_path = output_dir / "REMEDIATION_QUEUE.csv"
    risk_path = output_dir / "RISK_REGISTER.csv"
    delta_path = output_dir / "SCAN_DELTA.json"
    sow_path = output_dir / "SOW_READY.md"
    manifest_path = output_dir / "CLIENT_SOURCE_MANIFEST.json"
    pack_path = output_dir / "ANTI_SILO_PREFLIGHT_PACK.zip"

    public_summary = {
        "generated_at": report.get("generated_at"),
        "project": report.get("project", {}),
        "verdict": report.get("verdict", {}),
        "scope_impact": report.get("scope_impact", {}),
        "readiness_score": report.get("readiness_score", {}),
        "risk_register": report.get("risk_register", []),
        "effort_estimate": report.get("effort_estimate", {}),
        "executive_summary": report.get("executive_summary", {}),
        "diagnostics": report.get("diagnostics", {}),
        "delta": report.get("delta", {}),
        "trust_boundary": report.get("trust_boundary", ""),
    }
    summary_path.write_text(json.dumps(public_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest_path.write_text(
        json.dumps(report.get("client_manifest", {}), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_csv(
        remediation_path,
        ["priority", "severity", "category", "file", "finding", "action"],
        list(report.get("remediation", [])),
    )
    _write_csv(
        risk_path,
        ["risk_id", "category", "file", "description", "severity", "recommendation"],
        list(report.get("risk_register", [])),
    )
    delta_path.write_text(json.dumps(report.get("delta", {}), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sow_path.write_text(_sow_ready_markdown(report), encoding="utf-8")

    artifacts = [
        output_dir / "ANTI_SILO_REPORT.html",
        summary_path,
        remediation_path,
        risk_path,
        delta_path,
        sow_path,
        manifest_path,
    ]
    eligible = output_dir / "eligible_sources.csv"
    if eligible.exists():
        artifacts.append(eligible)
    with zipfile.ZipFile(pack_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in artifacts:
            if path.exists():
                archive.write(path, arcname=path.name)
    return {
        "audit_pack": pack_path,
        "preflight_summary": summary_path,
        "remediation_queue": remediation_path,
        "risk_register": risk_path,
        "scan_delta": delta_path,
        "sow_ready": sow_path,
        "client_manifest": manifest_path,
    }
