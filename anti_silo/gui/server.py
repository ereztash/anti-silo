from __future__ import annotations

import json
import secrets
import threading
import webbrowser
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from ..brain import BrainStore
from ..repair import RepairStore
from ..telemetry import LocalTelemetry
from ..watch import WatchService, WatchStore
from .handler import AntiSiloGuiHandler
from .report import _watch_scan


class AntiSiloGuiServer(ThreadingHTTPServer):
    config: dict[str, Any]
    allowed_roots: list[Path]
    csrf_token: str
    brain_store: BrainStore
    watch_store: WatchStore
    watch_service: WatchService
    initial_view: str
    initial_path: str
    last_report: dict[str, Any] | None
    telemetry: LocalTelemetry
    repair_store: RepairStore


def serve_gui(
    config: dict[str, Any],
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
    initial_view: str = "scan",
    initial_path: Path | None = None,
) -> str:
    url = f"http://{host}:{port}/"
    try:
        server = AntiSiloGuiServer((host, port), AntiSiloGuiHandler)
    except OSError:
        try:
            with urlopen(url, timeout=1) as response:
                existing = str(response.headers.get("Server", "")).startswith("AntiSiloGUI/")
        except Exception:
            existing = False
        if not existing:
            raise
        if open_browser:
            webbrowser.open(url)
        return url
    server.config = config
    server.allowed_roots = []
    server.csrf_token = secrets.token_urlsafe(32)
    server.brain_store = BrainStore()
    server.watch_store = WatchStore()
    server.repair_store = RepairStore()
    server.watch_service = WatchService(server.watch_store, lambda root: _watch_scan(root, config, server.repair_store))
    server.watch_service.start()
    server.initial_view = initial_view
    server.initial_path = str(initial_path.resolve()) if initial_path else ""
    server.last_report = None
    server.telemetry = LocalTelemetry()
    server.telemetry.record("app_opened", initial_view=initial_view)
    url = f"http://{server.server_address[0]}:{server.server_address[1]}/"
    if open_browser:
        threading.Timer(0.3, lambda: webbrowser.open(url)).start()
    try:
        print(f"Anti-Silo GUI running locally at {url}")
        server.serve_forever()
    finally:
        server.watch_service.stop()
        server.server_close()
    return url
