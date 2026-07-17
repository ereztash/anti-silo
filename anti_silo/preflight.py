from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


def _excluded(rel_path: Path, config: dict[str, Any]) -> bool:
    return bool(set(rel_path.parts) & set(config.get("exclude_dirs", [])))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _all_files(source_root: Path, config: dict[str, Any]) -> list[Path]:
    if source_root.is_file():
        return [source_root]
    files: list[Path] = []
    for path in source_root.rglob("*"):
        if not path.is_file() or path.name.startswith("~$"):
            continue
        if _excluded(path.relative_to(source_root), config):
            continue
        files.append(path)
    return sorted(files)


def build_corpus_diagnostics(
    source_root: Path,
    ingest_payload: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    source_root = source_root.expanduser().resolve()
    supported_extensions = {str(ext).lower() for ext in config.get("ingest_extensions", [])}
    all_files = _all_files(source_root, config)
    ingest_rows = list(ingest_payload.get("rows", []))
    issues: list[dict[str, Any]] = []

    ingest_by_file = {str(row.get("source_file", "")): row for row in ingest_rows}
    unsupported = []
    for path in all_files:
        relative = path.relative_to(source_root).as_posix() if source_root.is_dir() else path.name
        if path.suffix.lower() not in supported_extensions:
            unsupported.append(relative)
            issues.append(
                {
                    "kind": "unsupported_format",
                    "severity": "review",
                    "file": relative,
                    "finding": f"סוג הקובץ {path.suffix.lower() or '(ללא סיומת)'} אינו נכלל בסריקה.",
                    "action": "להמיר לפורמט נתמך או להחריג במפורש מהיקף ה-RAG.",
                }
            )

    for file_name, row in ingest_by_file.items():
        status = str(row.get("extraction_status", "complete"))
        if int(row.get("bytes", 1)) == 0:
            issues.append(
                {
                    "kind": "empty_file",
                    "severity": "block",
                    "file": file_name,
                    "finding": "הקובץ ריק.",
                    "action": "להחליף את הקובץ או להוציא אותו מהיקף ה-ingestion.",
                }
            )
        if status == "failed":
            issues.append(
                {
                    "kind": "extraction_failed",
                    "severity": "block",
                    "file": file_name,
                    "finding": "לא ניתן היה לחלץ תוכן מהקובץ.",
                    "action": "לבדוק הרשאות, הצפנה ותקינות או להמיר לפורמט נתמך.",
                }
            )
        elif status == "truncated":
            issues.append(
                {
                    "kind": "extraction_truncated",
                    "severity": "block",
                    "file": file_name,
                    "finding": "רק חלק מתוכן הקובץ נכלל בבדיקה.",
                    "action": "לפצל או להמיר את הקובץ ולסרוק מחדש לפני ingestion.",
                }
            )

    hashes: dict[str, list[str]] = {}
    for path in all_files:
        relative = path.relative_to(source_root).as_posix() if source_root.is_dir() else path.name
        if path.suffix.lower() not in supported_extensions:
            continue
        row = ingest_by_file.get(relative, {})
        digest = str(row.get("raw_source_hash", ""))
        if not digest:
            try:
                digest = _sha256(path)
            except OSError:
                continue
        hashes.setdefault(digest, []).append(relative)

    duplicate_groups = [sorted(files) for files in hashes.values() if len(files) > 1]
    for group in duplicate_groups:
        issues.append(
            {
                "kind": "exact_duplicate",
                "severity": "cleanup",
                "file": group[0],
                "related_files": group[1:],
                "finding": f"נמצאו {len(group)} עותקים זהים של אותו תוכן.",
                "action": "לבחור עותק קנוני אחד ולהחריג את השאר מהאינדקס.",
            }
        )

    counts = {
        "unsupported_files": len(unsupported),
        "empty_files": sum(1 for issue in issues if issue["kind"] == "empty_file"),
        "extraction_failed": sum(1 for issue in issues if issue["kind"] == "extraction_failed"),
        "extraction_truncated": sum(1 for issue in issues if issue["kind"] == "extraction_truncated"),
        "duplicate_groups": len(duplicate_groups),
        "duplicate_files": sum(len(group) - 1 for group in duplicate_groups),
    }
    return {
        "total_files": len(all_files),
        "ingested_files": len(ingest_rows),
        "by_extension": dict(sorted(dict(ingest_payload.get("by_extension", {})).items())),
        "counts": counts,
        "issues": issues,
    }


def build_verdict(counts: dict[str, int], diagnostics: dict[str, Any]) -> dict[str, str]:
    review = sum(int(counts.get(key, 0)) for key in ("backed", "indexed", "synthesis"))
    blocked = int(counts.get("unsupported", 0)) + int(counts.get("contradiction", 0))
    diagnostic_blocks = sum(1 for issue in diagnostics.get("issues", []) if issue.get("severity") == "block")
    diagnostic_review = sum(1 for issue in diagnostics.get("issues", []) if issue.get("severity") in {"review", "cleanup"})
    if blocked or diagnostic_blocks:
        return {
            "status": "stop",
            "label": "STOP",
            "title": "אין להעביר את התיקייה ל-ingestion עדיין",
            "summary": f"נמצאו {blocked + diagnostic_blocks} חסמים שדורשים תיקון לפני שימוש לפי מדיניות המקורות.",
        }
    if review or diagnostic_review:
        return {
            "status": "conditional_go",
            "label": "CONDITIONAL GO",
            "title": "אפשר להתקדם לאחר השלמת בדיקות המקור",
            "summary": f"נמצאו {review + diagnostic_review} פריטים לבדיקה, השלמת מקור או ניקוי corpus.",
        }
    return {
        "status": "go",
        "label": "GO",
        "title": "התיקייה עברה את מדיניות המקורות שנבחרה",
        "summary": "לא נמצאו חסמי מקור או חילוץ לפי המדיניות הנוכחית.",
    }


def build_remediation(rows: list[dict[str, Any]], diagnostics: dict[str, Any]) -> list[dict[str, Any]]:
    priority = {"block": 1, "review": 2, "cleanup": 3}
    queue: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for issue in diagnostics.get("issues", []):
        item = {
            "priority": priority.get(str(issue.get("severity")), 3),
            "severity": str(issue.get("severity", "review")),
            "category": str(issue.get("kind", "corpus_issue")),
            "file": str(issue.get("file", "")),
            "finding": str(issue.get("finding", "")),
            "action": str(issue.get("action", "")),
        }
        seen.add((item["file"], item["severity"]))
        queue.append(item)

    category_severity = {
        "contradiction": "block",
        "unsupported": "block",
        "indexed": "review",
        "synthesis": "review",
        "backed": "review",
    }
    for row in rows:
        category = str(row.get("category", "ready"))
        severity = category_severity.get(category)
        file_name = str(row.get("file", ""))
        if not severity or (file_name, severity) in seen:
            continue
        queue.append(
            {
                "priority": priority[severity],
                "severity": severity,
                "category": category,
                "file": file_name,
                "finding": str(row.get("explanation", "")),
                "action": str(row.get("action", "")),
            }
        )
    return sorted(queue, key=lambda row: (int(row["priority"]), str(row["file"]).casefold()))
