from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


MAX_LOGO_BYTES = 300_000  # data-URI is embedded in every exported report; keep it small
_ALLOWED_LOGO_TYPES = ("data:image/png;base64,", "data:image/jpeg;base64,", "data:image/svg+xml;base64,")


def default_branding_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".anti-silo"))
    return base / "AntiSilo" / "branding.json"


def _clean_text(value: Any, limit: int = 160) -> str:
    return " ".join(str(value or "").strip().split())[:limit]


def _clean_logo(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if not text.startswith(_ALLOWED_LOGO_TYPES):
        raise ValueError("הלוגו חייב להיות PNG, JPEG או SVG.")
    if len(text) > MAX_LOGO_BYTES:
        raise ValueError("קובץ הלוגו גדול מדי (מקסימום כ-300KB) — הוא מוטבע בכל דוח שמיוצא.")
    return text


class BrandingStore:
    """Consultant-level identity, applied to every exported client report: a logo, a
    business name, and free-form notes for the current engagement. Global (logo,
    business name) persists across scans; notes are per-report and passed at scan time,
    not stored here."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_branding_path()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def get(self) -> dict[str, str]:
        data = self._load()
        return {
            "business_name": _clean_text(data.get("business_name"), 120),
            "logo_data_uri": str(data.get("logo_data_uri", "")),
        }

    def set(self, business_name: Any, logo_data_uri: Any) -> dict[str, str]:
        payload = {
            "business_name": _clean_text(business_name, 120),
            "logo_data_uri": _clean_logo(logo_data_uri),
        }
        self._save(payload)
        return payload
