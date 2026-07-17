"""Repository hygiene guard: keep Python modules small and focused.

A single oversized module (the former 987-line ``gui.py``) is hard to reason
about and review. This test enforces a hard ceiling on every Python file in the
``anti_silo`` package so modules stay modular going forward. When a file grows
past the limit, split it by responsibility instead of raising the ceiling.
"""

from __future__ import annotations

from pathlib import Path

MAX_LINES = 250
PACKAGE_ROOT = Path(__file__).resolve().parent.parent / "anti_silo"


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def test_no_python_module_exceeds_line_limit() -> None:
    offenders = {
        path.relative_to(PACKAGE_ROOT).as_posix(): count
        for path in sorted(PACKAGE_ROOT.rglob("*.py"))
        if (count := _line_count(path)) > MAX_LINES
    }
    assert not offenders, (
        f"These modules exceed {MAX_LINES} lines; split them by responsibility "
        f"instead of raising the limit: {offenders}"
    )
