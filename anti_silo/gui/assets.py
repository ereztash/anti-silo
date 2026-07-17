from __future__ import annotations

from pathlib import Path

_STATIC_DIR = Path(__file__).resolve().parent / "static"


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
    script = _read_static("app.js")
    return document.replace("__ANTI_SILO_CSS__", styles).replace("__ANTI_SILO_JS__", script)


HTML = build_html()
