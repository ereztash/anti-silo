from __future__ import annotations

from pathlib import Path

_STATIC_DIR = Path(__file__).resolve().parent / "static"

# The frontend script is authored as focused source files and concatenated,
# in this order, into one classic (non-module) script. Order matters: shared
# state and helpers are declared before the wiring block runs.
_SCRIPT_PARTS = (
    "app.core.js",     # constants, DOM refs, mutable state, metric() helper
    "app.render.js",   # report table + summary rendering
    "app.scan.js",     # scan / repair / watch actions
    "app.net.js",      # api(), recordEvent(), escapeHtml() helpers
    "app.brain.js",    # second-brain view
    "app.init.js",     # event wiring + bootstrap (must stay last)
)


def _read_static(name: str) -> str:
    """Read a bundled frontend asset.

    ``__file__``-relative resolution works for source checkouts, installed
    wheels (files ship as package data), and PyInstaller builds (the ``static``
    folder is added to the bundle under the same package path).
    """
    return (_STATIC_DIR / name).read_text(encoding="utf-8")


def build_html() -> str:
    """Assemble the single-page GUI document from its component assets."""
    document = _read_static("index.html")
    styles = _read_static("styles.css")
    script = "".join(_read_static(name) for name in _SCRIPT_PARTS)
    return document.replace("__ANTI_SILO_CSS__", styles).replace("__ANTI_SILO_JS__", script)


HTML = build_html()
