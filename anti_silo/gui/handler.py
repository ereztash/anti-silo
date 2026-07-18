from __future__ import annotations

import hmac
import json
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlparse

from ..quick_scan import discard_quick_scan
from ..simulate import simulate_readiness
from .assets import HTML
from .pickers import _choose_file, _choose_folder, _default_desktop_dir
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
        if parsed.path == "/api/brain":
            self._send_json(self.server.brain_store.dashboard())
            return
        if parsed.path == "/api/watch":
            self._send_json(self.server.watch_store.dashboard())
            return
        if parsed.path == "/api/projects":
            self._send_json({"projects": self.server.project_store.list_projects()})
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        if not self._valid_csrf_token():
            self._send_json({"error": "invalid local request token"}, HTTPStatus.FORBIDDEN)
            return
        path = urlparse(self.path).path
        if path == "/api/default-desktop":
            self.server.telemetry.record("scan_started", source="desktop")
            self._send_json({"path": str(_default_desktop_dir())})
            return
        if path == "/api/pick-folder":
            try:
                self._send_json({"path": _choose_folder()})
            except Exception as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        if path == "/api/pick-source":
            try:
                self._send_json({"path": _choose_file()})
            except Exception as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        if path == "/api/shutdown":
            self.server.telemetry.record("app_exit")
            self._send_json({"closed": True})
            threading.Thread(target=self.server.shutdown, name="anti-silo-shutdown", daemon=True).start()
            return
        if path == "/api/event":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                event = str(payload.get("event", ""))
                allowed = {"result_action_taken", "brain_opened", "brain_decision_saved", "watch_enabled", "repair_started"}
                if event not in allowed:
                    raise ValueError("unknown local usage event")
                self.server.telemetry.record(event, **dict(payload.get("properties", {})))
                self._send_json({"recorded": True})
            except Exception as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        if path == "/api/watch":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                self._send_json({"watch": self.server.watch_store.add(Path(str(payload.get("path", ""))))})
                self.server.telemetry.record("watch_enabled")
            except Exception as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        if path == "/api/repair/source":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                report = getattr(self.server, "last_report", None)
                source_root = Path(str(payload.get("source_root", ""))).expanduser().resolve()
                if not report or source_root != Path(str(report.get("source_root", ""))).resolve():
                    raise ValueError("יש לסרוק את התיקייה לפני קישור מקור")
                link = self.server.repair_store.add(
                    source_root,
                    str(payload.get("target_file", "")),
                    Path(str(payload.get("source_path", ""))),
                )
                self.server.telemetry.record("repair_completed", kind="attach_source")
                self._send_json({"link": link})
            except Exception as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        if path == "/api/discard":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                discard_quick_scan(str(payload.get("staged_vault", "")))
                self._send_json({"discarded": True})
            except Exception as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        if path == "/api/brain/import-last-scan":
            try:
                report = getattr(self.server, "last_report", None)
                if not report:
                    raise ValueError("יש לבצע סריקה לפני ייבוא מקורות למוח השני")
                self._send_json(self.server.brain_store.import_scan_report(report))
            except Exception as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        if path == "/api/brain/entries":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                entry = self.server.brain_store.add_entry(
                    kind=str(payload.get("kind", "note")),
                    title=str(payload.get("title", "")),
                    body=str(payload.get("body", "")),
                    source_ids=[str(item) for item in payload.get("source_ids", [])],
                )
                self._send_json({"entry": entry})
                if entry.get("kind") == "decision":
                    self.server.telemetry.record("brain_decision_saved", has_sources=bool(entry.get("source_ids")))
            except Exception as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        if path == "/api/simulate":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                report = getattr(self.server, "last_report", None)
                if not report:
                    raise ValueError("יש לבצע סריקה לפני הרצת What-If")
                resolutions = payload.get("resolutions", [])
                if not isinstance(resolutions, list):
                    raise ValueError("resolutions must be a list")
                self._send_json(simulate_readiness(report, resolutions))
            except Exception as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
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
