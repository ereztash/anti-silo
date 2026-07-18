from __future__ import annotations

import hmac
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlparse

from .aux_routes import GET_ROUTES, POST_ROUTES
from .assets import HTML
from .report import build_human_report


class AntiSiloGuiHandler(BaseHTTPRequestHandler):
    server_version = "AntiSiloGUI/0.1"

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _valid_csrf_token(self) -> bool:
        expected = str(getattr(self.server, "csrf_token", ""))
        provided = self.headers.get("X-Anti-Silo-CSRF", "")
        return bool(expected) and hmac.compare_digest(provided, expected)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/":
            body = HTML.replace("__CSRF_TOKEN__", str(getattr(self.server, "csrf_token", ""))).replace(
                "__INITIAL_VIEW__", str(getattr(self.server, "initial_view", "scan"))
            ).replace("__INITIAL_PATH_JSON__", json.dumps(str(getattr(self.server, "initial_path", "")))).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/download":
            query = dict(part.split("=", 1) for part in parsed.query.split("&") if "=" in part)
            path = Path(unquote(query.get("path", ""))).resolve()
            allowed_roots = getattr(self.server, "allowed_roots", [])
            if not any(path.is_relative_to(root) for root in allowed_roots) or not path.exists():
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            self.server.telemetry.record("export_downloaded", artifact=path.name)
            data = path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{quote(path.name)}")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        route = GET_ROUTES.get(parsed.path)
        if route:
            route(self)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        if not self._valid_csrf_token():
            self._send_json({"error": "invalid local request token"}, HTTPStatus.FORBIDDEN)
            return
        path = urlparse(self.path).path
        route = POST_ROUTES.get(path)
        if route:
            route(self)
            return
        if path != "/api/scan":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            source_root = Path(str(payload.get("path", ""))).expanduser().resolve()
            if not source_root.exists():
                raise ValueError("התיקייה לא קיימת")
            project_meta = dict(payload.get("project", {}))
            if "go_threshold" in payload:
                project_meta["go_threshold"] = payload.get("go_threshold")
            project = self.server.project_store.upsert(project_meta, source_root)
            previous_scan = self.server.project_store.latest_scan(str(project["id"]))
            previous_report = getattr(self.server, "last_report", None)
            config = self.server.config
            if "go_threshold" in payload:
                # The consultant can set their own GO threshold per scan (e.g. a
                # stricter bar for a regulated domain); the engine clamps it.
                config = {**config, "go_threshold": payload.get("go_threshold")}
                self.server.config = config
            report = build_human_report(
                source_root,
                config,
                repair_store=self.server.repair_store,
                project=project,
                previous_scan=previous_scan,
                permit_request=payload.get("permit") if isinstance(payload.get("permit"), dict) else None,
                branding=self.server.branding_store.get(),
                consultant_notes=str(payload.get("consultant_notes", "")),
            )
            self.server.project_store.record_scan(str(project["id"]), report)
            self.server.allowed_roots = [Path(report["staged_vault"]).resolve(), Path(report["output_dir"]).resolve()]
            self.server.last_report = report
            if not self.server.telemetry.has_event("first_scan_completed"):
                self.server.telemetry.record("first_scan_completed", files=report["files"], decision=report["decision"])
            self.server.telemetry.record(
                "scan_completed",
                files=report["files"],
                decision=report["decision"],
                input_mode=report.get("input_mode", "unknown"),
            )
            if previous_report and previous_report.get("counts") != report.get("counts"):
                self.server.telemetry.record("trust_changed", before=previous_report.get("counts"), after=report.get("counts"))
            self._send_json(report)
        except Exception as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def log_message(self, format: str, *args: Any) -> None:
        return
