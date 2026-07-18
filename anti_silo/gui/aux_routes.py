"""Auxiliary local-server routes: pickers, watch, branding, brain, repair, What-If.

Split out of handler.py to keep it under the project's module-size guard — these
routes are self-contained (no dependency on the core /api/scan flow) and share a
common shape: read a small JSON body, call one store method, send the result back.
"""
from __future__ import annotations

import json
import threading
from http import HTTPStatus
from pathlib import Path
from typing import Any

from ..quick_scan import discard_quick_scan
from ..simulate import simulate_readiness
from .pickers import _choose_file, _choose_folder, _default_desktop_dir


def _read_json_body(handler: Any) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    return json.loads(handler.rfile.read(length).decode("utf-8"))


# GET routes -------------------------------------------------------------------

def handle_brain_get(handler: Any) -> None:
    handler._send_json(handler.server.brain_store.dashboard())


def handle_watch_get(handler: Any) -> None:
    handler._send_json(handler.server.watch_store.dashboard())


def handle_projects_get(handler: Any) -> None:
    handler._send_json({"projects": handler.server.project_store.list_projects()})


def handle_branding_get(handler: Any) -> None:
    handler._send_json(handler.server.branding_store.get())


# POST routes --------------------------------------------------------------------

def handle_default_desktop(handler: Any) -> None:
    handler.server.telemetry.record("scan_started", source="desktop")
    handler._send_json({"path": str(_default_desktop_dir())})


def handle_pick_folder(handler: Any) -> None:
    try:
        handler._send_json({"path": _choose_folder()})
    except Exception as exc:
        handler._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)


def handle_pick_source(handler: Any) -> None:
    try:
        handler._send_json({"path": _choose_file()})
    except Exception as exc:
        handler._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)


def handle_shutdown(handler: Any) -> None:
    handler.server.telemetry.record("app_exit")
    handler._send_json({"closed": True})
    threading.Thread(target=handler.server.shutdown, name="anti-silo-shutdown", daemon=True).start()


def handle_event(handler: Any) -> None:
    try:
        payload = _read_json_body(handler)
        event = str(payload.get("event", ""))
        allowed = {"result_action_taken", "brain_opened", "brain_decision_saved", "watch_enabled", "repair_started"}
        if event not in allowed:
            raise ValueError("unknown local usage event")
        handler.server.telemetry.record(event, **dict(payload.get("properties", {})))
        handler._send_json({"recorded": True})
    except Exception as exc:
        handler._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)


def handle_watch_post(handler: Any) -> None:
    try:
        payload = _read_json_body(handler)
        handler._send_json({"watch": handler.server.watch_store.add(Path(str(payload.get("path", ""))))})
        handler.server.telemetry.record("watch_enabled")
    except Exception as exc:
        handler._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)


def handle_branding_post(handler: Any) -> None:
    try:
        payload = _read_json_body(handler)
        saved = handler.server.branding_store.set(payload.get("business_name", ""), payload.get("logo_data_uri", ""))
        handler._send_json(saved)
    except Exception as exc:
        handler._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)


def handle_repair_source(handler: Any) -> None:
    try:
        payload = _read_json_body(handler)
        report = getattr(handler.server, "last_report", None)
        source_root = Path(str(payload.get("source_root", ""))).expanduser().resolve()
        if not report or source_root != Path(str(report.get("source_root", ""))).resolve():
            raise ValueError("יש לסרוק את התיקייה לפני קישור מקור")
        link = handler.server.repair_store.add(
            source_root, str(payload.get("target_file", "")), Path(str(payload.get("source_path", "")))
        )
        handler.server.telemetry.record("repair_completed", kind="attach_source")
        handler._send_json({"link": link})
    except Exception as exc:
        handler._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)


def handle_discard(handler: Any) -> None:
    try:
        payload = _read_json_body(handler)
        discard_quick_scan(str(payload.get("staged_vault", "")))
        handler._send_json({"discarded": True})
    except Exception as exc:
        handler._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)


def handle_brain_import_last_scan(handler: Any) -> None:
    try:
        report = getattr(handler.server, "last_report", None)
        if not report:
            raise ValueError("יש לבצע סריקה לפני ייבוא מקורות למוח השני")
        handler._send_json(handler.server.brain_store.import_scan_report(report))
    except Exception as exc:
        handler._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)


def handle_brain_entries(handler: Any) -> None:
    try:
        payload = _read_json_body(handler)
        entry = handler.server.brain_store.add_entry(
            kind=str(payload.get("kind", "note")),
            title=str(payload.get("title", "")),
            body=str(payload.get("body", "")),
            source_ids=[str(item) for item in payload.get("source_ids", [])],
        )
        handler._send_json({"entry": entry})
        if entry.get("kind") == "decision":
            handler.server.telemetry.record("brain_decision_saved", has_sources=bool(entry.get("source_ids")))
    except Exception as exc:
        handler._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)


def handle_simulate(handler: Any) -> None:
    try:
        payload = _read_json_body(handler)
        report = getattr(handler.server, "last_report", None)
        if not report:
            raise ValueError("יש לבצע סריקה לפני הרצת What-If")
        resolutions = payload.get("resolutions", [])
        if not isinstance(resolutions, list):
            raise ValueError("resolutions must be a list")
        handler._send_json(simulate_readiness(report, resolutions))
    except Exception as exc:
        handler._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)


GET_ROUTES = {
    "/api/brain": handle_brain_get,
    "/api/watch": handle_watch_get,
    "/api/projects": handle_projects_get,
    "/api/branding": handle_branding_get,
}

POST_ROUTES = {
    "/api/default-desktop": handle_default_desktop,
    "/api/pick-folder": handle_pick_folder,
    "/api/pick-source": handle_pick_source,
    "/api/shutdown": handle_shutdown,
    "/api/event": handle_event,
    "/api/watch": handle_watch_post,
    "/api/branding": handle_branding_post,
    "/api/repair/source": handle_repair_source,
    "/api/discard": handle_discard,
    "/api/brain/import-last-scan": handle_brain_import_last_scan,
    "/api/brain/entries": handle_brain_entries,
    "/api/simulate": handle_simulate,
}
