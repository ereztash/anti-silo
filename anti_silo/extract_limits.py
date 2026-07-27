"""Resource limits for text extraction.

A scanned folder is untrusted input. Every extractor here previously capped
exactly one dimension (rows, or pages) and left the others unbounded, so a
small, highly compressible .xlsx/.docx/.pdf could expand into gigabytes of
extracted text during ingest.

Two layers, because they defend different things:

- `Budget` bounds the *output* while it accumulates. Clamping a finished
  string would not help: building it already spent the memory.
- `archive_too_large` bounds the *parse*. openpyxl/python-docx must read the
  whole archive before any output cap can apply even once (a 9.6 MB crafted
  .xlsx measured ~19s inside `load_workbook()` alone, with output caps in
  place and doing nothing), so oversized archives are refused before parsing.
"""

from __future__ import annotations

import zipfile
from pathlib import Path


MAX_ROWS = 200
MAX_COLUMNS = 512
MAX_PDF_PAGES = 20
MAX_EXTRACTED_CHARS = 200_000
MAX_ARCHIVE_UNCOMPRESSED_BYTES = 150 * 1024 * 1024


class Budget:
    """Collects text chunks, stopping once the character budget is spent."""

    def __init__(self, limit: int = MAX_EXTRACTED_CHARS) -> None:
        self.limit = limit
        self.used = 0
        self.chunks: list[str] = []
        self.exhausted = False

    def add(self, chunk: str) -> bool:
        """Append a chunk. Returns False once the budget is exhausted."""
        if self.exhausted:
            return False
        remaining = self.limit - self.used
        if len(chunk) >= remaining:
            self.chunks.append(chunk[:remaining])
            self.used = self.limit
            self.exhausted = True
            return False
        self.chunks.append(chunk)
        self.used += len(chunk)
        return True

    def text(self) -> str:
        return "\n".join(self.chunks)


def archive_too_large(path: Path) -> int | None:
    """Return the uncompressed size if it exceeds the cap, else None.

    Reads the zip central directory only - no decompression, so this is cheap
    even for a file specifically built to be expensive to decompress.
    """
    try:
        with zipfile.ZipFile(path) as archive:
            total = sum(info.file_size for info in archive.infolist())
    except (zipfile.BadZipFile, OSError):
        return None
    return total if total > MAX_ARCHIVE_UNCOMPRESSED_BYTES else None


def archive_refusal_note(kind: str, uncompressed: int) -> str:
    return (
        f"{kind} refused before parsing: it expands to "
        f"{uncompressed / 1024 / 1024:.0f} MB, over the "
        f"{MAX_ARCHIVE_UNCOMPRESSED_BYTES / 1024 / 1024:.0f} MB limit"
    )


def limit_note(kind: str) -> str:
    return (
        f"{kind} truncated to the first {MAX_ROWS} rows, {MAX_COLUMNS} columns per row, "
        f"and {MAX_EXTRACTED_CHARS:,} characters"
    )


def clamp(text: str) -> tuple[str, bool]:
    if len(text) > MAX_EXTRACTED_CHARS:
        return text[:MAX_EXTRACTED_CHARS], True
    return text, False
