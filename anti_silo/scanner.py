from __future__ import annotations

import re
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any, Iterable

from .config import rel
from .model import Claim


def _matches_any(path: Path, patterns: list[str]) -> bool:
    path_text = path.as_posix()
    for pattern in patterns:
        if path.match(pattern) or fnmatchcase(path_text, pattern):
            return True
        if pattern.startswith("**/") and fnmatchcase(path_text, pattern[3:]):
            return True
    return False


def _inside_included_dir(vault: Path, rel_path: Path, include_dirs: list[str]) -> bool:
    if not include_dirs:
        return True
    parts = {part.lower() for part in rel_path.parts}
    parts.add(vault.name.lower())
    search_blob = f"{vault.name}/{rel_path.as_posix()}".lower()
    return any(token.lower() in parts or token.lower() in search_blob for token in include_dirs)


def iter_markdown(vault: Path, config: dict[str, Any]) -> Iterable[Path]:
    excluded = set(config.get("exclude_dirs", []))
    include_dirs = list(config.get("include_dirs", []))
    globs = list(config.get("claim_globs", ["**/*.md"]))
    for path in vault.rglob("*.md"):
        rel_path = path.relative_to(vault)
        parts = set(rel_path.parts)
        if parts & excluded:
            continue
        if not _matches_any(rel_path, globs):
            continue
        if not _inside_included_dir(vault, rel_path, include_dirs):
            continue
        yield path


def iter_indexable_files(vault: Path, config: dict[str, Any]) -> Iterable[Path]:
    excluded = set(config.get("exclude_dirs", []))
    include_dirs = list(config.get("include_dirs", []))
    extensions = {ext.lower() for ext in config.get("index_extensions", [".md"])}
    for path in vault.rglob("*"):
        if not path.is_file():
            continue
        rel_path = path.relative_to(vault)
        parts = set(rel_path.parts)
        if parts & excluded:
            continue
        if path.suffix.lower() not in extensions:
            continue
        if not _inside_included_dir(vault, rel_path, include_dirs):
            continue
        yield path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def metadata(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines()[:80]:
        m = re.match(r"^\s*([A-Za-z0-9_-]+)\s*:\s*(.+?)\s*$", line)
        if m:
            values.setdefault(m.group(1).lower(), m.group(2).strip())
    return values


def _has_any(blob: str, markers: list[str]) -> bool:
    return any(marker in blob for marker in markers)


def has_blocked_marker(text: str, meta: dict[str, str], config: dict[str, Any]) -> bool:
    markers = [m.lower() for m in config.get("blocked_markers", [])]
    if not markers:
        return False

    mode = str(config.get("blocked_marker_mode", "field")).lower()
    if mode == "substring":
        return _has_any(text.lower(), markers)

    fields = {field.lower() for field in config.get("blocked_marker_fields", [])}
    for field in fields:
        value = meta.get(field)
        if value and _has_any(value.lower(), markers):
            return True

    line_prefixes = tuple(str(prefix).lower() for prefix in config.get("blocked_line_prefixes", []))
    for line in text.splitlines():
        cleaned = line.strip().lower()
        if not cleaned:
            continue
        if line_prefixes and cleaned.startswith(line_prefixes) and _has_any(cleaned, markers):
            return True
        if cleaned in markers:
            return True
    return False


def claim_kind(blob: str, meta: dict[str, str], config: dict[str, Any]) -> str:
    explicit = meta.get("claim_type") or meta.get("claim_kind")
    if explicit:
        return explicit.strip().lower()
    synthesis_markers = [m.lower() for m in config.get("synthesis_markers", [])]
    if _has_any(blob, synthesis_markers):
        return "synthesis"
    return "claim"


def has_source_spine(blob: str, meta: dict[str, str], config: dict[str, Any]) -> bool:
    if meta.get("source_hash") or meta.get("source_spine"):
        return True
    spine_markers = [m.lower() for m in config.get("source_spine_markers", [])]
    return _has_any(blob, spine_markers)


def scan_claims(vault: Path, config: dict[str, Any]) -> list[Claim]:
    claim_markers = [m.lower() for m in config.get("claim_markers", [])]
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
                blocked=has_blocked_marker(text, meta, config),
                has_corroboration=any(marker in blob for marker in corroboration_markers),
                has_ledger=any(marker in blob for marker in ledger_markers),
                claim_kind=claim_kind(blob, meta, config),
                has_source_spine=has_source_spine(blob, meta, config),
                metadata=meta,
            )
        )
    return claims
