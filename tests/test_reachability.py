"""Every state the product can display must be reachable by following its own docs.

This file exists because of a defect no amount of adversarial testing found. Four
separate red-team passes attacked the engine with inputs designed to fail —
malformed archives, junction escapes, injected formulas, fabricated hashes — and
all of them missed it, because the defect was not in what happens when you feed
the tool garbage. It was in what happens when you do exactly what the README
tells you to do.

Following the documented tagging convention perfectly left `provenance_opinion`
permanently `disclaimed`, which meant the permit could never be granted and the
plain `GO` verdict could never be reached. The product promised an outcome and
had no path to it, and nothing in the suite noticed, because every test either
asserted a failure mode or asserted a unit's internals.

The rule this file enforces: **a state the product can show is a promise, and a
promise with no reachable construction is a broken one.** Adding a new verdict,
permission or opinion without adding a construction that reaches it fails here.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from anti_silo.config import load_config
from anti_silo.gui.report import build_human_report

# Every state declared by the engine. Kept explicit rather than scraped, so that
# deleting a construction cannot silently shrink what is being guaranteed.
VERDICT_STATUSES = {"go", "go_hygiene_only", "conditional_go", "stop", "no_corpus"}
PERMIT_PERMISSIONS = {"granted", "conditional", "denied"}
PROVENANCE_OPINIONS = {"expressed", "disclaimed"}

_TOPICS = {
    "vendor": "Vendor onboarding requires a signed data processing addendum before production access is granted to any third party processor operating on regulated data.",
    "travel": "Reimbursement for international travel is capped at economy fare unless the flight segment exceeds eight hours of continuous scheduled duration.",
    "retention": "Client engagement records are retained for seven years from the closing date of the matter, after which they are destroyed under witnessed procedure.",
}


def _tagged_corpus(root: Path, *, attested: bool) -> Path:
    """A corpus built by following the documented convention, start to finish.

    Distinct content per file so nothing trips near-duplicate detection, a real
    source per claim, a `source_hash:` that genuinely verifies, and
    `corroborated:`. With `attested`, it also carries the pointer the repair flow
    writes when a human selects the source — the only thing the engine counts as
    testimony from outside the corpus.
    """
    root.mkdir(parents=True, exist_ok=True)
    sources = root / "sources"
    sources.mkdir()
    attestations = root / "_sources"
    if attested:
        attestations.mkdir()
    for name, text in _TOPICS.items():
        raw = sources / f"{name}-source.md"
        raw.write_text(f"# {name} source of truth\n\n{text}\n" * 3, encoding="utf-8")
        digest = hashlib.sha256(raw.read_bytes()).hexdigest()
        if attested:
            (attestations / f"{digest}.md").write_text(
                f"type: user_selected_source\nsource_of_truth: true\nraw_source_hash: {digest}\n"
                "---\nuser-selected independent local file\n",
                encoding="utf-8",
            )
        (root / f"{name}.md").write_text(
            f"---\ncorroborated: true\nsource_hash: {digest}\n---\n\nclaim: {text}\n" * 3,
            encoding="utf-8",
        )
    return root


def _report(folder: Path, authority: str = "locate", audience: str = "internal", impact: str = "low"):
    return build_human_report(
        folder,
        load_config(),
        permit_request={"requested_authority": authority, "audience": audience, "failure_impact": impact},
    )


def test_every_declared_output_state_is_reachable(tmp_path: Path) -> None:
    """The guarantee. Each state below has a construction that actually reaches it."""
    verdicts: set[str] = set()
    permissions: set[str] = set()
    opinions: set[str] = set()

    def observe(report) -> None:
        verdicts.add(report["verdict"]["status"])
        permissions.add(report["grounding_permit"]["permission"])
        opinions.add(str(report["verdict"].get("provenance_opinion", "")))

    # Nothing to judge.
    empty = tmp_path / "empty"
    empty.mkdir()
    observe(_report(empty))

    # A blocking defect.
    blocked = tmp_path / "blocked"
    blocked.mkdir()
    (blocked / "placeholder.md").write_text("", encoding="utf-8")
    observe(_report(blocked))

    # An ordinary client folder with no convention at all.
    plain = tmp_path / "plain"
    plain.mkdir()
    for name, text in _TOPICS.items():
        (plain / f"{name}.md").write_text(f"# {name}\n\n{text}\n" * 3, encoding="utf-8")
    observe(_report(plain))

    # The documented convention followed exactly — clean, but self-declared.
    observe(_report(_tagged_corpus(tmp_path / "tagged", attested=False)))

    # The same, plus the human attestation. This is the only route to `go`.
    attested = _tagged_corpus(tmp_path / "attested", attested=True)
    observe(_report(attested))
    observe(_report(attested, authority="act", audience="external", impact="safety"))

    assert VERDICT_STATUSES <= verdicts, f"unreachable verdicts: {sorted(VERDICT_STATUSES - verdicts)}"
    assert PERMIT_PERMISSIONS <= permissions, f"unreachable permissions: {sorted(PERMIT_PERMISSIONS - permissions)}"
    assert PROVENANCE_OPINIONS <= opinions, f"unreachable opinions: {sorted(PROVENANCE_OPINIONS - opinions)}"


def test_the_documented_path_alone_cannot_reach_go(tmp_path: Path) -> None:
    """Pins the boundary, so the README's claim about it stays true.

    Tagging is not testimony. A corpus that follows the convention perfectly is
    still the corpus speaking about itself, so it stops at `go_hygiene_only`
    with a disclaimed opinion. That is correct — and it is exactly the promise
    that had no path, until the attestation route was documented.
    """
    tagged = _report(_tagged_corpus(tmp_path / "tagged", attested=False))
    assert tagged["verdict"]["status"] == "go_hygiene_only"
    assert tagged["verdict"]["provenance_opinion"] == "disclaimed"

    attested = _report(_tagged_corpus(tmp_path / "attested", attested=True))
    assert attested["verdict"]["status"] == "go"
    assert attested["verdict"]["provenance_opinion"] == "expressed"
    assert attested["grounding_permit"]["permission"] == "granted"
