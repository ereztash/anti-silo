from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Surface:
    file: str
    surfaces: tuple[str, ...]
    authority: str
    can_anchor_claim: bool


@dataclass(frozen=True)
class Claim:
    file: str
    text: str
    blocked: bool = False
    has_corroboration: bool = False
    has_ledger: bool = False
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class TriangulationRow:
    file: str
    tier: str
    source: str
    authority: str
    reason: str
