from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

from .config import output_dir
from .ingest import write_ingest
from .index import build_index
from .pulse import write_pulse
from .repair import RepairStore
from .report_labels import write_localized_outputs
from .scanner import iter_indexable_files, scan_claims


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


def is_structured_vault(source_root: Path, config: dict[str, Any]) -> bool:
    claims = scan_claims(source_root, config)
    if not claims:
        return False
    has_declared_source = any(claim.metadata.get("source_hash") or claim.metadata.get("source_spine") for claim in claims)
    has_anchorable_surface = any(surface.can_anchor_claim for surface in build_index(source_root, config))
    return has_declared_source or has_anchorable_surface


def _copy_structured_vault(source_root: Path, staging: Path, config: dict[str, Any]) -> dict[str, Any]:
    copied: list[dict[str, str]] = []
    for source in iter_indexable_files(source_root, config):
        relative = source.relative_to(source_root)
        target = staging / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append({"source_file": relative.as_posix(), "staged_file": relative.as_posix()})
    return {
        "generated_by": "anti-silo structured quick scan",
        "source_root": str(source_root),
        "output_vault": str(staging),
        "files": len(copied),
        "rows": copied,
    }


def run_quick_scan(
    source_root: Path,
    config: dict[str, Any],
    lang: str = "he",
    repair_store: RepairStore | None = None,
) -> dict[str, Any]:
    source_root = source_root.expanduser().resolve()
    staging = _quick_scan_dir()
    structured = is_structured_vault(source_root, config)
    if structured:
        staging.mkdir(parents=True, exist_ok=True)
        ingest_payload = _copy_structured_vault(source_root, staging, config)
    else:
        links = (repair_store or RepairStore()).links_for(source_root)
        ingest_payload = write_ingest(source_root, config, output_vault=staging, source_links=links)
    pulse_payload = write_pulse(staging, config)
    localized = write_localized_outputs(staging, pulse_payload, lang=lang, config=config)
    out = output_dir(staging, config)
    return {
        "source_root": str(Path(source_root).resolve()),
        "staged_vault": str(staging),
        "output_dir": str(out),
        "temporary": True,
        "input_mode": "structured_vault" if structured else "document_folder",
        "lang": lang,
        "ingest": ingest_payload,
        "pulse": pulse_payload,
        "localized_outputs": localized,
    }
