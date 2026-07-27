"""Whether Anti-Silo can express an opinion on where a claim's backing came from.

Assurance practice separates an *adverse* opinion ("the provenance is bad") from
a *disclaimer* of opinion ("I cannot form one"). The two are not interchangeable:
an adverse opinion is a finding, a disclaimer is an admission that the evidence
needed to reach a finding was never available.

Anti-Silo reads files. When every source marker in scope was written inside the
same folder being audited, the corpus is vouching for itself and the tool has no
independent footing. Measured on a fabricated, wholly self-referential corpus,
the engine still returned CONDITIONAL GO with `permit: granted -> locate` - it
held `trust_origin: self_declared` on every row and acted on none of it. Showing
the field was not enough; the verdict and the permit have to abstain.
"""

from __future__ import annotations

from typing import Any

from .model import SELF_DECLARED

EXPRESSED = "expressed"
DISCLAIMED = "disclaimed"

_DISCLAIMER_TEXT = (
    "Anti-Silo נמנע מחוות דעת על מקוריות המקורות בקורפוס הזה. "
    "כל סימוני המקור נכתבו בתוך התיקייה שנסרקה — הקורפוס מעיד על עצמו. "
    "לניקוי המצב הזה יש דרך אחת: לצרף מקור דרך זרימת-התיקון, כלומר שאדם יבחר "
    "את הקובץ ידנית. תיוג מדויק ככל שיהיה בתוך הקורפוס נשאר `self_declared` — "
    "וזה נכון, לא ליקוי."
)

_NO_ROWS_TEXT = (
    "Anti-Silo נמנע מחוות דעת על מקוריות המקורות: לא נמצאה ולו שורה אחת "
    "עם סימון מקור, ולכן אין על מה לחוות דעה."
)


def evaluate_provenance_opinion(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Classify whether an opinion on provenance can be expressed at all.

    Only rows that actually carry a backing are counted. A row with an empty
    `trust_origin` has no source to judge - it is silent about provenance, not
    evidence of self-certification, and inflating it either way would be a
    finding the data does not support.
    """
    backed = [row for row in rows if str(row.get("trust_origin", "")).strip()]
    independent = [row for row in backed if str(row.get("trust_origin", "")).strip() != SELF_DECLARED]

    if not backed:
        return {
            "opinion": DISCLAIMED,
            "basis": "no_backed_rows",
            "statement": _NO_ROWS_TEXT,
            "backed_rows": 0,
            "independent_rows": 0,
        }
    if not independent:
        return {
            "opinion": DISCLAIMED,
            "basis": "all_self_declared",
            "statement": _DISCLAIMER_TEXT,
            "backed_rows": len(backed),
            "independent_rows": 0,
        }
    return {
        "opinion": EXPRESSED,
        "basis": "independent_backing_present",
        "statement": (
            f"{len(independent)} מתוך {len(backed)} המקורות אינם מוצהרים-עצמית, "
            "ולכן ניתן לחוות דעה על שרשרת המקורות."
        ),
        "backed_rows": len(backed),
        "independent_rows": len(independent),
    }


def apply_to_verdict(verdict: dict[str, str], provenance: dict[str, Any]) -> dict[str, str]:
    """Stop a clean-hygiene corpus from reading as a clean-provenance corpus.

    Hygiene findings (failed extraction, duplicates, unsupported formats) are
    fully verifiable from the bytes, so GO stays a real statement about them.
    What it must not silently also mean is "the sources check out" - when
    provenance is disclaimed, the headline says which of the two it earned.
    """
    result = dict(verdict)
    result["provenance_opinion"] = str(provenance.get("opinion", EXPRESSED))
    result["provenance_statement"] = str(provenance.get("statement", ""))
    if provenance.get("opinion") != DISCLAIMED or verdict.get("status") != "go":
        return result
    result["status"] = "go_hygiene_only"
    result["label"] = "GO — היגיינה בלבד"
    result["title"] = "התיקייה נקייה טכנית; על מקוריות המקורות אין חוות דעת"
    result["summary"] = (
        "לא נמצאו חסמי חילוץ או כפילויות. זו קביעה על תקינות הקבצים בלבד — "
        "לא על כך שהמקורות אומתו."
    )
    return result
