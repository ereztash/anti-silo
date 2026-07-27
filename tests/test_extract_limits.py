from __future__ import annotations

import zipfile

import pytest

from anti_silo.extract_limits import (
    MAX_ARCHIVE_UNCOMPRESSED_BYTES,
    MAX_COLUMNS,
    MAX_EXTRACTED_CHARS,
    Budget,
    archive_too_large,
    clamp,
)
from anti_silo.ingest_extract import extract_text


def test_budget_stops_at_the_limit() -> None:
    budget = Budget(limit=10)
    assert budget.add("12345") is True
    assert budget.add("67890123") is False
    assert budget.exhausted is True
    assert len(budget.text().replace("\n", "")) == 10
    # Further additions are ignored rather than growing past the cap.
    assert budget.add("more") is False
    assert len(budget.text().replace("\n", "")) == 10


def test_clamp_bounds_text() -> None:
    assert clamp("short") == ("short", False)
    clamped, truncated = clamp("x" * (MAX_EXTRACTED_CHARS + 100))
    assert truncated is True
    assert len(clamped) == MAX_EXTRACTED_CHARS


def test_csv_with_unbounded_columns_is_truncated(tmp_path) -> None:
    # Row count was already capped; column count was not, so a single row
    # could carry unlimited text into the extracted output.
    path = tmp_path / "wide.csv"
    path.write_text(",".join(["cell"] * (MAX_COLUMNS * 4)) + "\n", encoding="utf-8")

    result = extract_text(path)

    assert result.status == "truncated"
    assert len(result.text) <= MAX_EXTRACTED_CHARS
    assert result.text.count("|") < MAX_COLUMNS * 4


def test_text_file_is_bounded(tmp_path) -> None:
    path = tmp_path / "huge.txt"
    path.write_text("y" * (MAX_EXTRACTED_CHARS + 5_000), encoding="utf-8")

    result = extract_text(path)

    assert result.status == "truncated"
    assert len(result.text) == MAX_EXTRACTED_CHARS


def test_archive_guard_ignores_normal_and_non_zip_files(tmp_path) -> None:
    plain = tmp_path / "note.txt"
    plain.write_text("not a zip", encoding="utf-8")
    assert archive_too_large(plain) is None

    small_zip = tmp_path / "small.zip"
    with zipfile.ZipFile(small_zip, "w") as archive:
        archive.writestr("a.txt", "hello")
    assert archive_too_large(small_zip) is None


def test_archive_guard_flags_an_oversized_expansion(tmp_path) -> None:
    # A highly compressible archive: small on disk, huge once expanded. Built
    # with one entry so the test stays fast; the guard reads the central
    # directory only and never decompresses.
    bomb = tmp_path / "bomb.zip"
    with zipfile.ZipFile(bomb, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("big.xml", "0" * (MAX_ARCHIVE_UNCOMPRESSED_BYTES + 1024))

    assert bomb.stat().st_size < MAX_ARCHIVE_UNCOMPRESSED_BYTES
    oversized = archive_too_large(bomb)
    assert oversized is not None
    assert oversized > MAX_ARCHIVE_UNCOMPRESSED_BYTES


def test_oversized_xlsx_is_refused_before_parsing(tmp_path) -> None:
    pytest.importorskip("openpyxl")
    # Not a real workbook - the guard must reject it before openpyxl is asked
    # to parse anything, so the contents never matter.
    path = tmp_path / "bomb.xlsx"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("xl/worksheets/sheet1.xml", "0" * (MAX_ARCHIVE_UNCOMPRESSED_BYTES + 1024))

    result = extract_text(path)

    assert result.status == "failed"
    assert "refused before parsing" in result.note


def test_normal_xlsx_still_extracts(tmp_path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    path = tmp_path / "normal.xlsx"
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(["service", "tier", "price"])
    sheet.append(["Starter", "Tier 1", 1500])
    workbook.save(path)

    result = extract_text(path)

    assert result.status == "complete"
    assert "Starter" in result.text
    assert "1500" in result.text
