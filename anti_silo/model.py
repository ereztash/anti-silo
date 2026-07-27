from __future__ import annotations

from dataclasses import dataclass, field


# Who vouches for a source, which is a different question from what tier it
# reaches. A marker written inside the scanned folder is an assertion by
# whoever assembled that folder - structurally the same kind of statement as
# the claim it is vouching for. Nothing inside a corpus can establish that a
# source is independent of it; only a person pointing at something from
# outside can. This is surfaced rather than silently scored, because which
# origin is acceptable depends on whose folder it is.
SELF_DECLARED = "self_declared"
OPERATOR_ATTESTED = "operator_attested"


@dataclass(frozen=True)
class Surface:
    file: str
    surfaces: tuple[str, ...]
    authority: str
    can_anchor_claim: bool
    content_hash: str
    raw_source: bool = False
    raw_source_hash: str = ""
    normalized_content_hash: str = ""
    trust_origin: str = SELF_DECLARED


@dataclass(frozen=True)
class Claim:
    file: str
    text: str
    blocked: bool = False
    has_corroboration: bool = False
    has_ledger: bool = False
    claim_kind: str = "claim"
    has_source_spine: bool = False
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class TriangulationRow:
    file: str
    tier: str
    source: str
    authority: str
    reason: str
    source_hash: str = ""
    claim_kind: str = "claim"
    needs: str = ""
    trust_origin: str = ""


@dataclass(frozen=True)
class EnforcementRow:
    file: str
    tier: str
    decision: str
    reason: str
    action: str
