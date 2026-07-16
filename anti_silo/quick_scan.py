from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

from .config import output_dir
from .ingest import write_ingest
from .pulse import write_pulse
from .report_labels import write_localized_outputs


def _quick_scan_dir() -> Path:
    root = Path(tempfile.gettempdir()) / "anti_silo_quick_scan"
    root.mkdir(parents=True, exist_ok=True)
    placeholder = Path(tempfile.mkdtemp(prefix="scan_", dir=root))
    shutil.rmtree(placeholder)
    return placeholder


def discard_quick_scan(path: str | Path) -> None:
    target = Path(path).resolve()
    root = (Path(tempfile.gettempdir()) / "anti_silo_quick_scan").resolve()
    if root == target or root not in target.parents:
        raise ValueError("refusing to delete a non quick-scan folder")
    if target.exists():
        shutil.rmtree(target)


def run_quick_scan(source_root: Path, config: dict[str, Any], lang: str = "he") -> dict[str, Any]:
    staging = _quick_scan_dir()
    ingest_payload = write_ingest(source_root, config, output_vault=staging)
    pulse_payload = write_pulse(staging, config)
    localized = write_localized_outputs(staging, pulse_payload, lang=lang, config=config)
    out = output_dir(staging, config)
    return {
        "source_root": str(Path(source_root).resolve()),
        "staged_vault": str(staging),
        "output_dir": str(out),
        "temporary": True,
        "lang": lang,
        "ingest": ingest_payload,
        "pulse": pulse_payload,
        "localized_outputs": localized,
    }
