"""CSV writing that is safe to open in a spreadsheet.

Anti-Silo's CSV outputs carry attacker-controlled text: the `file` column is
the scanned filename, and a scanned folder is by definition untrusted input.
Excel, LibreOffice, and Google Sheets interpret a cell whose first character
is `=`, `+`, `-`, `@` (or a leading tab/CR before one of those) as a formula,
so a file named `=HYPERLINK(...)` becomes a live formula in the consultant's
Audit Pack - and that pack is handed to the client. This module neutralizes
that at the single point where cells are written.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterable


# Leading characters a spreadsheet may treat as the start of a formula.
_FORMULA_LEADERS = ("=", "+", "-", "@")
# Stripped before inspection: a spreadsheet skips these, so "\t=cmd" is still
# a formula to Excel even though it does not literally start with "=".
_SKIPPED_LEADERS = ("\t", "\r", "\n", " ")


def csv_safe_cell(value: Any) -> str:
    """Return value as text that a spreadsheet will treat as data, not formula.

    Prefixes a single quote when the cell would otherwise be parsed as a
    formula. The quote is the standard spreadsheet "treat as text" marker and
    is not displayed as part of the value in Excel/LibreOffice/Sheets.
    """
    text = "" if value is None else str(value)
    if not text:
        return text
    probe = text.lstrip("".join(_SKIPPED_LEADERS))
    if probe.startswith(_FORMULA_LEADERS):
        return "'" + text
    return text


def csv_safe_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: csv_safe_cell(value) for key, value in row.items()}


class SafeDictWriter(csv.DictWriter):
    """Drop-in csv.DictWriter that formula-escapes every cell it writes.

    Used instead of csv.DictWriter at each site that emits a CSV containing
    scanned-filename or scanned-content text, so call sites keep whatever row
    shaping they already do and only the writer type changes.
    """

    def writerow(self, rowdict: dict[str, Any]) -> Any:  # type: ignore[override]
        return super().writerow(csv_safe_row(rowdict))

    def writerows(self, rowdicts: Iterable[dict[str, Any]]) -> Any:  # type: ignore[override]
        return super().writerows(csv_safe_row(row) for row in rowdicts)


def write_csv(
    path: Path,
    fieldnames: list[str],
    rows: Iterable[dict[str, Any]],
    *,
    encoding: str = "utf-8",
    extrasaction: str = "raise",
) -> None:
    """Write a CSV whose cells cannot become spreadsheet formulas."""
    with path.open("w", encoding=encoding, newline="") as handle:
        writer = SafeDictWriter(handle, fieldnames=fieldnames, extrasaction=extrasaction)
        writer.writeheader()
        writer.writerows(rows)
