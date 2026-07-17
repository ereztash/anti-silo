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


def write_preflight_artifacts(report: dict[str, Any], output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "PREFLIGHT_SUMMARY.json"
    remediation_path = output_dir / "REMEDIATION_QUEUE.csv"
    manifest_path = output_dir / "CLIENT_SOURCE_MANIFEST.json"
    pack_path = output_dir / "ANTI_SILO_PREFLIGHT_PACK.zip"

    public_summary = {
        "generated_at": report.get("generated_at"),
        "project": report.get("project", {}),
        "verdict": report.get("verdict", {}),
        "scope_impact": report.get("scope_impact", {}),
        "diagnostics": report.get("diagnostics", {}),
        "delta": report.get("delta", {}),
        "trust_boundary": report.get("trust_boundary", ""),
    }
    summary_path.write_text(json.dumps(public_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest_path.write_text(
        json.dumps(report.get("client_manifest", {}), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with remediation_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["priority", "severity", "file", "finding", "action"])
        writer.writeheader()
        writer.writerows(report.get("remediation", []))

    artifacts = [output_dir / "ANTI_SILO_REPORT.html", summary_path, remediation_path, manifest_path]
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
        "client_manifest": manifest_path,
    }
