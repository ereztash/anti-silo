from __future__ import annotations

import base64
import binascii
import json
import tempfile
from http.server import BaseHTTPRequestHandler
from pathlib import Path, PurePosixPath
from typing import Any

from anti_silo.config import load_config
from anti_silo.gui.report import build_human_report
from anti_silo.quick_scan import discard_quick_scan


MAX_BODY_BYTES = 4_300_000
MAX_FILE_BYTES = 1_500_000
MAX_TOTAL_BYTES = 2_800_000
MAX_FILES = 150
MAX_TEXT_LENGTH = 120
CONTENT_EXTENSIONS = {
    ".csv",
    ".docx",
    ".htm",
    ".html",
    ".json",
    ".md",
    ".pdf",
    ".txt",
    ".xlsx",
}


class ScanRequestError(ValueError):
    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


def _safe_relative_path(value: object) -> Path:
    raw = str(value or "").replace("\\", "/").strip()
    candidate = PurePosixPath(raw)
    if (
        not raw
        or raw.startswith("/")
        or "\x00" in raw
        or any(part in {"", ".", ".."} for part in candidate.parts)
        or ":" in candidate.parts[0]
    ):
        raise ScanRequestError("One of the selected file paths is invalid.")
    return Path(*candidate.parts)


def _clean_text(value: object, fallback: str) -> str:
    cleaned = " ".join(str(value or "").split()).strip()
    return (cleaned or fallback)[:MAX_TEXT_LENGTH]


def _project_payload(value: object) -> dict[str, str]:
    project = value if isinstance(value, dict) else {}
    return {
        "client_name": _clean_text(project.get("client_name"), "Web client"),
        "project_name": _clean_text(project.get("project_name"), "RAG Preflight"),
        "consultant_name": _clean_text(project.get("consultant_name"), "Anti-Silo"),
    }


def _decode_content(row: dict[str, Any], extension: str) -> bytes:
    if extension not in CONTENT_EXTENSIONS:
        return b""
    encoded = row.get("content_base64")
    if not isinstance(encoded, str):
        raise ScanRequestError("A supported file is missing its content.")
    try:
        content = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ScanRequestError("A selected file could not be decoded.") from exc
    if len(content) > MAX_FILE_BYTES:
        raise ScanRequestError("A selected file exceeds the 1.5 MB per-file limit.", 413)
    return content


def _public_report(report: dict[str, Any]) -> dict[str, Any]:
    public = dict(report)
    for key in ("source_root", "staged_vault", "output_dir", "downloads"):
        public.pop(key, None)
    public["temporary"] = True
    public["input_mode"] = "web_upload"
    public["privacy"] = {
        "stored": False,
        "message": "Files are processed in a temporary serverless workspace and are not retained by Anti-Silo.",
    }
    return public


def build_web_report(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ScanRequestError("The request body must be a JSON object.")
    rows = payload.get("files")
    if not isinstance(rows, list) or not rows:
        raise ScanRequestError("Select at least one file before running the preflight.")
    if len(rows) > MAX_FILES:
        raise ScanRequestError(f"Select no more than {MAX_FILES} files per scan.", 413)

    total_bytes = 0
    quick_scan_path: str | None = None
    with tempfile.TemporaryDirectory(prefix="anti_silo_web_") as workspace:
        source_root = Path(workspace) / "source"
        source_root.mkdir()
        seen: set[str] = set()
        for value in rows:
            if not isinstance(value, dict):
                raise ScanRequestError("Each file entry must be an object.")
            relative = _safe_relative_path(value.get("path"))
            relative_key = relative.as_posix().casefold()
            if relative_key in seen:
                raise ScanRequestError("The selection contains duplicate file paths.")
            seen.add(relative_key)

            content = _decode_content(value, relative.suffix.lower())
            total_bytes += len(content)
            if total_bytes > MAX_TOTAL_BYTES:
                raise ScanRequestError("The selected files exceed the 2.8 MB scan limit.", 413)

            target = source_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)

        report = build_human_report(
            source_root,
            load_config(),
            project=_project_payload(payload.get("project")),
        )
        quick_scan_path = str(report.get("staged_vault", ""))
        result = _public_report(report)

    if quick_scan_path:
        discard_quick_scan(quick_scan_path)
    return result


class handler(BaseHTTPRequestHandler):
    server_version = "AntiSiloWeb/0.1"

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        self._send_json(
            200,
            {
                "service": "anti-silo-preflight",
                "status": "ready",
                "limits": {
                    "files": MAX_FILES,
                    "file_bytes": MAX_FILE_BYTES,
                    "total_bytes": MAX_TOTAL_BYTES,
                },
            },
        )

    def do_POST(self) -> None:  # noqa: N802
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length <= 0:
                raise ScanRequestError("The request body is empty.")
            if content_length > MAX_BODY_BYTES:
                raise ScanRequestError("The upload exceeds Vercel's request limit.", 413)
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
            self._send_json(200, build_web_report(payload))
        except ScanRequestError as exc:
            self._send_json(exc.status, {"error": str(exc)})
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(400, {"error": "The request body is not valid JSON."})
        except Exception:
            self._send_json(500, {"error": "The scan could not be completed. Please try a smaller selection."})

    def log_message(self, format: str, *args: object) -> None:
        return
