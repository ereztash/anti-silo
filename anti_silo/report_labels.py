from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import output_dir


TIER_LABELS_HE = {
    "triangulated": "מאומת",
    "source_backed": "מגובה_במקור",
    "graph_only": "ללא_תימוכין",
    "ledger_supported": "רישום_ללא_מקור",
    "corroborated_no_source": "חיזוק_ללא_מקור",
    "refuted_or_blocked": "חסום_או_מופרך",
}

DECISION_LABELS_HE = {
    "proceed": "אפשר_להמשיך",
    "source_backed_pending_corroboration": "מגובה_אך_דורש_אימות_נוסף",
    "blocked": "חסום_עד_תיקון",
    "allow": "אפשר_להשתמש",
    "review": "דורש_בדיקה",
    "block": "לא_להסתמך",
}

ACTION_LABELS_HE = {
    "ready": "אפשר להשתמש",
    "backed": "הוסף אימות נוסף",
    "synthesis": "השלם רשימת מקורות",
    "unsupported": "הוסף קובץ מקור תומך",
    "contradiction": "תקן לפני הסתמכות",
}


def tier_label(value: str, lang: str = "en") -> str:
    if lang != "he":
        return value
    return TIER_LABELS_HE.get(value, value)


def decision_label(value: str, lang: str = "en") -> str:
    if lang != "he":
        return value
    return DECISION_LABELS_HE.get(value, value)


def action_label(category: str, lang: str = "en") -> str:
    if lang != "he":
        return category
    return ACTION_LABELS_HE.get(category, "בדוק ידנית")


def localize_pulse_payload(payload: dict[str, Any], lang: str = "en") -> dict[str, Any]:
    if lang != "he":
        return payload
    localized = dict(payload)
    localized["decision"] = decision_label(str(payload.get("decision", "")), lang)
    localized["triangulation"] = {
        tier_label(str(key), lang): value for key, value in dict(payload.get("triangulation", {})).items()
    }
    localized["promotion_gate"] = {
        decision_label(str(key), lang): value for key, value in dict(payload.get("promotion_gate", {})).items()
    }
    return localized


def write_localized_outputs(vault: Path, pulse_payload: dict[str, Any], lang: str = "en", config: dict[str, Any] | None = None) -> dict[str, str]:
    if lang != "he":
        return {}
    out = output_dir(vault, config or {})
    paths: dict[str, str] = {}
    localized_pulse = localize_pulse_payload(pulse_payload, lang)
    pulse_json = out / "pulse.he.json"
    pulse_json.write_text(json.dumps(localized_pulse, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["pulse_he_json"] = str(pulse_json)

    pulse_md = out / "PULSE_HE.md"
    pulse_md.write_text(
        "\n".join(
            [
                "# דוח Anti-Silo",
                "",
                f"- החלטה: **{localized_pulse.get('decision', '')}**",
                f"- קבצים שנסרקו: **{localized_pulse.get('claims', 0)}**",
                f"- מקורות/משטחי אמת: **{localized_pulse.get('truth_surfaces', 0)}**",
                f"- חסמי אמון: **{localized_pulse.get('contradiction_penalty', {}).get('hard_blocks', 0)}**",
                "",
                "## סיכום מצבים",
                "",
                *[
                    f"- `{tier_label(str(key), lang)}`: {value}"
                    for key, value in sorted(dict(pulse_payload.get("triangulation", {})).items())
                ],
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    paths["pulse_he_md"] = str(pulse_md)

    source_csv = out / "triangulation_gate.csv"
    if source_csv.exists():
        target_csv = out / "triangulation_gate.he.csv"
        with source_csv.open("r", encoding="utf-8", newline="") as src, target_csv.open(
            "w", encoding="utf-8", newline=""
        ) as dst:
            reader = csv.DictReader(src)
            fieldnames = ["file", "status", "action", "technical_tier", "reason"]
            writer = csv.DictWriter(dst, fieldnames=fieldnames)
            writer.writeheader()
            for row in reader:
                technical_tier = str(row.get("tier", ""))
                status = tier_label(technical_tier, lang)
                writer.writerow(
                    {
                        "file": row.get("file", ""),
                        "status": status,
                        "action": "בדוק בדוח",
                        "technical_tier": technical_tier,
                        "reason": row.get("reason", ""),
                    }
                )
        paths["triangulation_he_csv"] = str(target_csv)
    return paths
