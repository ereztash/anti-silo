"""Ordering the remediation queue by what a finding costs, not by what it blocks.

Ingestion severity and downstream consequence are different axes, and sorting by
severity alone buries the findings that matter most.

Measured on a real legal intake folder (13 files, no tagging convention): three
drafts of one services agreement carrying liability caps of $250,000 and
$100,000 and terms of 24 and 18 months were correctly detected as a
`near_duplicate_conflict` — and landed at position **13 of 14**, under ten rows
of boilerplate. An empty placeholder file ranked first.

That ordering is defensible for ingestion and wrong for the reader. An extraction
failure is loud: the file is visibly absent and someone notices. A contradiction
is silent: retrieval returns one of several conflicting values with full
confidence, and nothing in the answer discloses that a conflict existed. The
silent failure belongs at the top.

The second problem is volume. In a folder that has never adopted provenance
tagging — which is every ordinary client folder — every single file lands in
`indexed` and produces its own "no independent source" row. That is not ten
findings; it is one fact about the folder, repeated ten times. Worse, it labels
the client's own authoritative documents (a fee schedule, a matter list) as
risks for lacking an external source, when those documents *are* the source.
"""

from __future__ import annotations

from typing import Any

# What a finding costs if the corpus is ingested anyway, independent of whether
# it blocks ingestion. Lower sorts first.
CONSEQUENCE_RANK = {
    # Silent and downstream: the answer is wrong and looks confident.
    "near_duplicate_conflict": 1,
    "contradiction": 1,
    # Loud and immediate: content is visibly missing.
    "extraction_failed": 2,
    "extraction_truncated": 2,
    "unsupported": 2,
    # Structural noise: real, cheap, and nobody is misled by it.
    "unsupported_format": 3,
    "empty_file": 3,
    "near_duplicate": 3,
    "exact_duplicate": 3,
    # Provenance state of the corpus, not a defect in any one file.
    "backed": 4,
    "synthesis": 4,
    "indexed": 5,
}

DEFAULT_CONSEQUENCE = 3

# Below this many, listing per file is still readable and more useful.
AGGREGATE_THRESHOLD = 3

_AGGREGATED = "indexed"


def consequence(category: str) -> int:
    return CONSEQUENCE_RANK.get(str(category), DEFAULT_CONSEQUENCE)


def aggregate_unanchored(queue: list[dict[str, Any]], threshold: int = AGGREGATE_THRESHOLD) -> list[dict[str, Any]]:
    """Collapse the per-file "no independent source" rows into a single finding.

    Kept per file below the threshold, where the list is short enough to read.
    Above it, the rows stop being findings and become a property of the folder.
    """
    unanchored = [item for item in queue if item.get("category") == _AGGREGATED]
    if len(unanchored) < threshold:
        return queue

    files = sorted({str(item.get("file", "")) for item in unanchored if item.get("file")})
    rest = [item for item in queue if item.get("category") != _AGGREGATED]
    rest.append(
        {
            "priority": 2,
            "severity": "review",
            "category": "corpus_unanchored",
            "file": f"{len(files)} קבצים",
            "related_files": files,
            "finding": (
                f"{len(files)} קבצים אינם נושאים מקור עצמאי מחוץ לתיקייה — "
                "צפוי בתיקיית-intake שמעולם לא אימצה מוסכמת-מקורות, ואינו פגם בקבצים עצמם. "
                "מסמך שהוא-עצמו הסמכות (לוח שכר-טרחה, רשימת-תיקים) אינו חסר-מקור: הוא המקור."
            ),
            "action": "לקבוע אילו מסמכים הם מקור-אמת ולתייג אותם, לפני בניית שכבת-האחזור.",
            "impact": (
                "כל עוד לא נקבע מקור-אמת, אין דרך מכנית להעדיף גרסה אחת על אחרת בזמן אחזור."
            ),
        }
    )
    return rest


def sort_queue(queue: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Consequence first, then ingestion severity, then filename for determinism."""
    return sorted(
        queue,
        key=lambda row: (
            consequence(str(row.get("category", ""))),
            int(row.get("priority", 3)),
            str(row.get("file", "")).casefold(),
        ),
    )
