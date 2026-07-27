"""Deterministic near-duplicate detection for corpus hygiene.

Exact SHA-256 duplicates are the *rare* case in a real client folder: people
do not byte-copy files, they save `sow.md`, `sow-v2.md`, `sow-FINAL.md`. Those
are near-identical, carry conflicting numbers, and are genuine RAG poison - the
retriever returns all three and the model may ground on the outdated one. Hash
equality cannot see them at all.

This uses a bottom-k shingle sketch (a MinHash variant), chosen so the result
stays consistent with the rest of the engine:

- deterministic: same bytes in, same sketch out, on any machine, no model and
  no randomness, so it can sit in a decision path that promises determinism.
- explainable: the score is an estimated Jaccard overlap of word 5-grams, and
  can be stated to a client as "these files share ~94% of their phrasing".
- bounded: each file is reduced to at most `SKETCH_SIZE` integers, so a large
  document costs the same to compare as a small one.
"""

from __future__ import annotations

import hashlib
import re

# Calibrated by measurement, not intuition. Scores for a true near-duplicate
# (one price edited) against two *different* documents sharing one template -
# the realistic false-positive case for a consultancy corpus:
#
#              long docs            short docs
#   3-gram   0.963 vs 0.460      0.815 vs 0.615
#   5-gram   0.938 vs 0.422      0.600 vs 0.539   <- unusable on short docs
#
# 3-grams are equally specific on long documents and far more usable on short
# ones, so they win outright. The threshold sits between the short-document
# pair, the tightest case; long documents clear it by a wide margin. Short
# documents are inherently the weaker signal here - a handful of shingles
# means one edit moves the score a lot - which is why a near-duplicate alone
# is only "cleanup" severity, and disagreeing figures are what escalate it.
SHINGLE_WORDS = 3
SKETCH_SIZE = 256
DEFAULT_THRESHOLD = 0.72
FIGURE_LIMIT = 200

_WORD = re.compile(r"\w+", re.UNICODE)
# Numbers worth disagreeing about: money, percentages, quantities, years.
# Single digits are excluded because list markers and "Phase 1" are noise.
_FIGURE = re.compile(r"\d[\d,._]*\d|\d{2,}")


def figure_fingerprint(text: str) -> list[str]:
    """Bounded, normalized set of the numbers a document asserts.

    Two drafts of the same document that disagree on a price, a headcount or a
    deadline will differ here even though their prose is ~identical - which is
    what separates "someone renamed a file" from "these documents contradict
    each other and the retriever cannot tell which one is current".
    """
    figures = set()
    for raw in _FIGURE.findall(text):
        normalized = raw.replace(",", "").replace("_", "").rstrip(".")
        if normalized and normalized not in {"0"}:
            figures.add(normalized)
    return sorted(figures)[:FIGURE_LIMIT]


def _hash_shingle(shingle: str) -> int:
    digest = hashlib.blake2b(shingle.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big")


def content_sketch(text: str) -> list[int]:
    """Reduce text to a bounded, deterministic set of shingle hashes.

    Returns an empty sketch for text too short to shingle, which the
    similarity function treats as "not comparable" rather than "identical".
    """
    tokens = _WORD.findall(text.lower())
    if len(tokens) < SHINGLE_WORDS:
        return []
    hashes = {
        _hash_shingle(" ".join(tokens[i : i + SHINGLE_WORDS]))
        for i in range(len(tokens) - SHINGLE_WORDS + 1)
    }
    return sorted(hashes)[:SKETCH_SIZE]


def similarity(left: list[int], right: list[int]) -> float:
    """Estimated Jaccard overlap of two bottom-k sketches, in 0.0-1.0.

    For documents short enough that the sketch holds every shingle, this is
    the exact Jaccard similarity rather than an estimate.
    """
    if not left or not right:
        return 0.0
    left_set, right_set = set(left), set(right)
    k = min(len(left_set), len(right_set))
    union_sample = sorted(left_set | right_set)[:k]
    if not union_sample:
        return 0.0
    shared = sum(1 for value in union_sample if value in left_set and value in right_set)
    return shared / len(union_sample)


def find_near_duplicate_groups(
    sketches: dict[str, list[int]],
    threshold: float = DEFAULT_THRESHOLD,
    exclude: set[str] | None = None,
) -> list[dict[str, object]]:
    """Group files whose content overlaps at or above `threshold`.

    `exclude` skips files already reported as exact duplicates, so the same
    problem is not raised twice under two different names. Groups are built by
    transitive linking (a~b, b~c => one group) because a draft chain is one
    decision for the consultant, not several.
    """
    exclude = exclude or set()
    names = sorted(name for name in sketches if name not in exclude and sketches[name])
    parent = {name: name for name in names}

    def find(name: str) -> str:
        while parent[name] != name:
            parent[name] = parent[parent[name]]
            name = parent[name]
        return name

    scores: dict[tuple[str, str], float] = {}
    for i, left in enumerate(names):
        for right in names[i + 1 :]:
            score = similarity(sketches[left], sketches[right])
            if score >= threshold:
                scores[(left, right)] = score
                parent[find(left)] = find(right)

    grouped: dict[str, list[str]] = {}
    for name in names:
        grouped.setdefault(find(name), []).append(name)

    results: list[dict[str, object]] = []
    for members in grouped.values():
        if len(members) < 2:
            continue
        members = sorted(members)
        relevant = [
            score
            for (left, right), score in scores.items()
            if left in members and right in members
        ]
        results.append(
            {
                "files": members,
                "similarity": round(min(relevant), 3) if relevant else threshold,
            }
        )
    return sorted(results, key=lambda row: str(row["files"][0]))


def build_issues(
    ingest_rows: list[dict[str, object]],
    threshold: float = DEFAULT_THRESHOLD,
    exclude: set[str] | None = None,
) -> list[dict[str, object]]:
    """Turn near-duplicate groups into corpus-diagnostic issues.

    Two severities, because they are two different problems for the operator:
    near-duplicates that agree are cleanup (they inflate the index and crowd
    retrieval), while near-duplicates that disagree on their figures are a
    correctness risk - the retriever will surface several and cannot tell
    which is current.
    """
    sketches = {
        str(row.get("source_file", "")): list(row.get("content_sketch") or []) for row in ingest_rows
    }
    figures = {
        str(row.get("source_file", "")): list(row.get("figures") or []) for row in ingest_rows
    }
    issues: list[dict[str, object]] = []
    for group in find_near_duplicate_groups(sketches, threshold, exclude):
        members = [str(name) for name in group["files"]]  # type: ignore[index]
        percent = f"{float(group['similarity']) * 100:.0f}%"
        differing = {name: set(figures.get(name, [])) for name in members}
        shared = set.intersection(*differing.values()) if differing else set()
        conflicting = sorted({v for values in differing.values() for v in values} - shared)
        if conflicting and len({frozenset(v) for v in differing.values()}) > 1:
            issues.append(
                {
                    "kind": "near_duplicate_conflict",
                    "severity": "review",
                    "file": members[0],
                    "related_files": members[1:],
                    "similarity": group["similarity"],
                    "conflicting_values": conflicting[:12],
                    "finding": (
                        f"{len(members)} מסמכים חופפים ב-{percent} אך חלוקים בנתונים "
                        f"({', '.join(conflicting[:4])}) — ככל הנראה גרסאות שונות של אותו מסמך."
                    ),
                    "action": "לקבוע איזו גרסה קנונית ולהחריג את השאר לפני ingestion.",
                }
            )
        else:
            issues.append(
                {
                    "kind": "near_duplicate",
                    "severity": "cleanup",
                    "file": members[0],
                    "related_files": members[1:],
                    "similarity": group["similarity"],
                    "finding": f"{len(members)} מסמכים חופפים ב-{percent} בתוכן כמעט זהה.",
                    "action": "לבחור עותק קנוני אחד ולהחריג את השאר מהאינדקס.",
                }
            )
    return issues
