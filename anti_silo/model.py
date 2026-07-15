from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Surface:
    file: str
    surfaces: tuple[str, ...]
    authority: str
    can_anchor_claim: bool
    content_hash: str
    raw_source: bool = False
    raw_source_hash: str = ""


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


@dataclass(frozen=True)
class EnforcementRow:
    file: str
    tier: str
    decision: str
    reason: str
    action: str
