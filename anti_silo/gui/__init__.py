"""Local-only Anti-Silo GUI.

The GUI is split into focused modules (frontend assets, HTTP handler, report
builder, server bootstrap). This package re-exports the stable names so callers
and tests can keep importing them from ``anti_silo.gui``.
"""

from __future__ import annotations

from .assets import HTML
from .handler import AntiSiloGuiHandler
from .report import build_human_report, render_report_html
from .server import AntiSiloGuiServer, serve_gui

__all__ = [
    "HTML",
    "AntiSiloGuiHandler",
    "AntiSiloGuiServer",
    "build_human_report",
    "render_report_html",
    "serve_gui",
]
