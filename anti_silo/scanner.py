from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

from .config import rel
from .model import Claim


def iter_markdown(vault: Path, config: dict[str, Any]) -> Iterable[Path]:
    excluded = set(config.get("exclude_dirs", []))
    for path in vault.rglob("*.md"):
        parts = set(path.relative_to(vault).parts)
        if parts & excluded:
            continue
        yield path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def metadata(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines()[:80]:
        m = re.match(r"^\s*([A-Za-z0-9_-]+)\s*:\s*(.+?)\s*$", line)
        if m:
            values[m.group(1).lower()] = m.group(2).strip()
    return values


def scan_claims(vault: Path, config: dict[str, Any]) -> list[Claim]:
    claim_markers = [m.lower() for m in config.get("claim_markers", [])]
    blocked_markers = [m.lower() for m in config.get("blocked_markers", [])]
    corroboration_markers = [m.lower() for m in config.get("corroboration_markers", [])]
    ledger_markers = [m.lower() for m in config.get("ledger_markers", [])]

    claims: list[Claim] = []
    for path in iter_markdown(vault, config):
        text = read_text(path)
        blob = text.lower()
        meta = metadata(text)
        is_claim = any(marker in blob for marker in claim_markers)
        if not is_claim:
            continue
        claims.append(
            Claim(
                file=rel(vault, path),
                text=text,
                blocked=any(marker in blob for marker in blocked_markers),
                has_corroboration=any(marker in blob for marker in corroboration_markers),
                has_ledger=any(marker in blob for marker in ledger_markers),
                metadata=meta,
            )
        )
    return claims
