from __future__ import annotations

import csv
import html
import json
import re
from dataclasses import dataclass
from pathlib import Path

from .scanner import read_text


@dataclass(frozen=True)
class ExtractionResult:
    text: str
    status: str = "complete"
    note: str = ""


def _extract_csv(path: Path) -> ExtractionResult:
    rows: list[str] = []
    try:
        with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as f:
            reader = csv.reader(f)
            for idx, row in enumerate(reader):
                if idx >= 200:
                    return ExtractionResult("\n".join(rows), "truncated", "CSV limited to the first 200 rows")
                rows.append(" | ".join(cell.strip() for cell in row))
    except (csv.Error, OSError, ValueError) as exc:
        return ExtractionResult("", "failed", f"CSV could not be read: {exc}")
    return ExtractionResult("\n".join(rows))


def _extract_json(path: Path) -> ExtractionResult:
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace") as f:
            data = json.load(f)
    except (ValueError, OSError) as exc:
        return ExtractionResult("", "failed", f"JSON could not be parsed: {exc}")
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if len(text) > 20000:
        return ExtractionResult(text[:20000], "truncated", "JSON limited to the first 20,000 characters")
    return ExtractionResult(text)


def _strip_html(text: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _extract_docx(path: Path) -> ExtractionResult:
    try:
        import docx  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - depends on optional package
        return ExtractionResult("", "failed", f"DOCX extraction unavailable: {exc}")
    try:
        document = docx.Document(str(path))
    except Exception as exc:
        return ExtractionResult("", "failed", f"DOCX could not be read (corrupt or not a real .docx): {exc}")
    return ExtractionResult("\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()))


def _extract_xlsx(path: Path) -> ExtractionResult:
    try:
        import openpyxl  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - depends on optional package
        return ExtractionResult("", "failed", f"XLSX extraction unavailable: {exc}")
    try:
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception as exc:
        return ExtractionResult("", "failed", f"XLSX could not be read (corrupt or not a real .xlsx): {exc}")
    chunks: list[str] = []
    truncated = False
    for sheet in workbook.worksheets:
        chunks.append(f"## Sheet: {sheet.title}")
        for idx, row in enumerate(sheet.iter_rows(values_only=True)):
            if idx >= 200:
                truncated = True
                break
            values = ["" if value is None else str(value) for value in row]
            if any(value.strip() for value in values):
                chunks.append(" | ".join(values))
    workbook.close()
    return ExtractionResult(
        "\n".join(chunks),
        "truncated" if truncated else "complete",
        "XLSX sheets limited to the first 200 rows" if truncated else "",
    )


def _extract_pdf(path: Path) -> ExtractionResult:
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - depends on optional package
        return ExtractionResult("", "failed", f"PDF extraction unavailable: {exc}")
    try:
        reader = PdfReader(str(path))
        pages: list[str] = []
        for page in reader.pages[:20]:
            pages.append(page.extract_text() or "")
        page_count = len(reader.pages)
    except Exception as exc:
        return ExtractionResult("", "failed", f"PDF could not be read (corrupt, encrypted, or scanned without OCR): {exc}")
    return ExtractionResult(
        "\n".join(pages),
        "truncated" if page_count > 20 else "complete",
        "PDF limited to the first 20 pages" if page_count > 20 else "",
    )


def extract_text(path: Path) -> ExtractionResult:
    ext = path.suffix.lower()
    if ext in {".md", ".txt"}:
        return ExtractionResult(read_text(path))
    if ext == ".csv":
        return _extract_csv(path)
    if ext == ".json":
        return _extract_json(path)
    if ext in {".html", ".htm"}:
        return ExtractionResult(_strip_html(read_text(path)))
    if ext == ".docx":
        return _extract_docx(path)
    if ext == ".xlsx":
        return _extract_xlsx(path)
    if ext == ".pdf":
        return _extract_pdf(path)
    return ExtractionResult("", "failed", "Unsupported file type")
