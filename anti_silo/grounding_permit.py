"""Grounding Permit — what a corpus's evidence state actually authorizes.

Anti-Silo's Readiness Score answers "is this corpus source-traceable?" This module
answers a narrower, separate question: "given that evidence state, what is a RAG
system built on it allowed to DO?" A corpus can be identically scored and still earn
different permission depending on what the consultant requests — locating sources,
drafting a reviewed answer, advising a client, or acting autonomously.

Two variables are kept deliberately separate and neither is derived from the other:
`Corpus Readiness` (the existing Readiness Score) measures evidence quality. `Use
Permission` (this module) measures what that evidence quality authorizes for a
requested use, audience, and failure impact. Collapsing them would make the same
corpus report a different "quality" depending on a dropdown choice, which would
break the deterministic meaning the Readiness Score already has.

Design boundary, stated once here because it shapes every rule below: this module
audits file-level evidence, not organizational governance. It can verify whether a
claim has an independent source; it cannot verify whether a named owner exists or a
human fallback procedure is followed. So `decide` is never fully GRANTED — it caps
at an `advise` grant with an explicit note that owner/fallback must be attested to
separately — and `act` is never granted at all. This mirrors the standard RAG
security distinction between retrieval permission and action permission: the right
to find a source is not the right to act on it.
"""
from __future__ import annotations

from typing import Any


REQUESTED_AUTHORITIES = ("locate", "draft", "advise", "decide", "act")
AUDIENCES = ("internal", "client", "external")
FAILURE_IMPACTS = ("low", "financial", "legal", "safety")

# Evidence rank per triangulation category, worst to best. "synthesis" (a summary
# without a source spine) ranks with "unsupported" — it offers no independent anchor.
_EVIDENCE_RANK = {"unsupported": 0, "synthesis": 0, "indexed": 1, "backed": 2, "ready": 3}
EVIDENCE_TIER_LABEL = {0: "ללא אסמכתא", 1: "נסרק, טרם אומת", 2: "מגובה במקור", 3: "משולש ומאומת"}

_AUTHORITY_BASE_RANK = {"locate": 1, "draft": 2, "advise": 3, "decide": 3}

_DOWNGRADE = {"decide": "advise", "advise": "draft_with_human_review", "draft": "locate", "locate": "none"}

_GRANTED_COPY = {
    "none": {
        "permitted": ["אין להשתמש בקורפוס הזה להפקת תשובות, המלצות או פעולות."],
        "prohibited": ["חיפוש, ניסוח, המלצה, החלטה ופעולה — כולם חסומים עד לתיקון."],
    },
    "locate": {
        "permitted": ["חיפוש והצגת מקורות רלוונטיים למשתמש.", "הצגת קטעי מקור גולמיים בלי ניסוח מחדש."],
        "prohibited": ["ניסוח תשובה מהמקורות.", "המלצה או קבלת החלטה על בסיסם."],
    },
    "draft_with_human_review": {
        "permitted": ["ניסוח טיוטת תשובה עם ציטוטים למקור.", "הצגת המסמך שעליו התבססה הטיוטה."],
        "prohibited": ["מסירת תשובה סופית ללא אישור אנושי.", "המלצה בעלת השלכה כספית או משפטית."],
    },
    "draft": {
        "permitted": ["ניסוח טיוטת תשובה עם ציטוטים למקור, לשימוש פנימי.", "הצגת המסמך שעליו התבססה הטיוטה."],
        "prohibited": ["מסירת התשובה ללקוח בלי סקירה אנושית.", "המלצה בעלת השלכה כספית או משפטית."],
    },
    "advise": {
        "permitted": ["המלצה למשתמש המבוססת על מקורות משולשים.", "הצגת שרשרת המקורות שביסוד ההמלצה."],
        "prohibited": ["קבלת החלטה אוטונומית על בסיס ההמלצה.", "הפעלת פעולה על בסיס ההמלצה."],
    },
}


def corpus_evidence_rank(counts: dict[str, Any], diagnostics: dict[str, Any]) -> int:
    """The corpus's weakest-link evidence rank, or -1 if hard-blocked / no evidence.

    Mirrors build_verdict's own STOP philosophy: a single unresolved block (a
    contradiction, a failed extraction, an empty file) denies the whole corpus,
    regardless of how strong the rest of the evidence is.
    """
    diag_counts = dict(diagnostics.get("counts", {}))
    hard_block = (
        int(counts.get("contradiction", 0)) > 0
        or int(diag_counts.get("extraction_failed", 0)) > 0
        or int(diag_counts.get("empty_files", 0)) > 0
    )
    if hard_block:
        return -1
    present = [rank for category, rank in _EVIDENCE_RANK.items() if int(counts.get(category, 0)) > 0]
    return min(present) if present else -1


def _full_grant_label(requested_authority: str, audience: str) -> str:
    # A client- or public-facing draft is never granted without a human-review
    # condition attached — the table treats that condition as part of what "granted"
    # means for that audience, not a downgrade from insufficient evidence.
    if requested_authority == "draft" and audience != "internal":
        return "draft_with_human_review"
    return requested_authority


def _min_rank(requested_authority: str, audience: str, failure_impact: str) -> int:
    base = _AUTHORITY_BASE_RANK.get(requested_authority, 3)
    if requested_authority == "draft" and audience != "internal":
        base = max(base, 2)
    if audience == "external":
        base = max(base, 3)
    if failure_impact in ("legal", "safety"):
        base = min(3, base + 1)
    return base


def _upgrade_conditions(
    requested_authority: str, counts: dict[str, Any], diagnostics: dict[str, Any]
) -> list[str]:
    conditions: list[str] = []
    if int(counts.get("contradiction", 0)) > 0:
        conditions.append("לפתור את הסתירות שסומנו כחסמי אמון.")
    if int(dict(diagnostics.get("counts", {})).get("extraction_failed", 0)) > 0:
        conditions.append("לתקן קבצים שכשלו בחילוץ תוכן.")
    if int(counts.get("unsupported", 0)) > 0:
        conditions.append("להוסיף מקור ראשוני עצמאי לטענות שכרגע חסרות אסמכתא.")
    if int(counts.get("synthesis", 0)) > 0:
        conditions.append("להשלים רשימת מקורות (source spine) לסיכומים הקיימים.")
    if int(counts.get("indexed", 0)) > 0:
        conditions.append("לאמת מקור עצמאי לקבצים שנסרקו אך טרם אומתו.")
    if int(counts.get("backed", 0)) > 0:
        conditions.append("להוסיף חיזוק (corroboration) עצמאי למקורות הקיימים.")
    if requested_authority in ("decide", "act"):
        conditions.append(
            "Anti-Silo בודק ראיות בקבצים בלבד ואינו יכול לאמת בעלים (owner) או נוהל fallback אנושי — "
            "אלה תנאים ארגוניים שיש לאשר בנפרד לפני הענקת סמכות החלטה או פעולה."
        )
    return conditions


def evaluate_grounding_permit(
    requested_authority: str,
    audience: str,
    failure_impact: str,
    counts: dict[str, Any],
    diagnostics: dict[str, Any],
) -> dict[str, Any]:
    requested_authority = requested_authority if requested_authority in REQUESTED_AUTHORITIES else "locate"
    audience = audience if audience in AUDIENCES else "internal"
    failure_impact = failure_impact if failure_impact in FAILURE_IMPACTS else "low"

    corpus_rank = corpus_evidence_rank(counts, diagnostics)

    if requested_authority == "act":
        # Anti-Silo audits file evidence; it never certifies autonomous action authority.
        return {
            "requested_authority": "act",
            "audience": audience,
            "failure_impact": failure_impact,
            "permission": "denied",
            "granted_authority": "none",
            "corpus_evidence_tier": EVIDENCE_TIER_LABEL.get(max(corpus_rank, 0), EVIDENCE_TIER_LABEL[0]),
            "permitted_uses": _GRANTED_COPY["none"]["permitted"],
            "prohibited_uses": ["הפעלת פעולה אוטומטית מכל סוג — Anti-Silo אינו מעניק את הרמה הזו."],
            "upgrade_conditions": [
                "Anti-Silo אינו מעניק אי-פעם הרשאת Act אוטונומית על סמך בדיקת מקורות — "
                "נדרשת מדיניות ארגונית נפרדת, מעבר לבדיקת קבצים."
            ],
        }

    if corpus_rank < 0:
        return {
            "requested_authority": requested_authority,
            "audience": audience,
            "failure_impact": failure_impact,
            "permission": "denied",
            "granted_authority": "none",
            "corpus_evidence_tier": EVIDENCE_TIER_LABEL[0],
            "permitted_uses": _GRANTED_COPY["none"]["permitted"],
            "prohibited_uses": _GRANTED_COPY["none"]["prohibited"],
            "upgrade_conditions": _upgrade_conditions(requested_authority, counts, diagnostics),
        }

    min_rank = _min_rank(requested_authority, audience, failure_impact)
    # `decide` is never fully granted (see module docstring) even when evidence clears the bar.
    force_conditional = requested_authority == "decide"

    if corpus_rank >= min_rank and not force_conditional:
        permission = "granted"
        granted_authority = _full_grant_label(requested_authority, audience)
    elif corpus_rank >= min_rank - 1:
        permission = "conditional"
        granted_authority = _DOWNGRADE.get(requested_authority, "none")
    else:
        permission = "denied"
        granted_authority = "none"

    copy = _GRANTED_COPY.get(granted_authority, _GRANTED_COPY["none"])
    return {
        "requested_authority": requested_authority,
        "audience": audience,
        "failure_impact": failure_impact,
        "permission": permission,
        "granted_authority": granted_authority,
        "corpus_evidence_tier": EVIDENCE_TIER_LABEL.get(corpus_rank, EVIDENCE_TIER_LABEL[0]),
        "permitted_uses": copy["permitted"],
        "prohibited_uses": copy["prohibited"],
        "upgrade_conditions": _upgrade_conditions(requested_authority, counts, diagnostics)
        if permission != "granted"
        else [],
    }
