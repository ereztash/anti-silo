from __future__ import annotations

HUMAN_TIERS = {
    "triangulated": ("ready", "מאומת", "הקובץ מגובה במקור ויש לו חיזוק נוסף."),
    "source_backed": ("backed", "מגובה במקור", "יש אסמכתא ראשונית, אבל כדאי להוסיף אימות נוסף לפני הסתמכות חזקה."),
    "indexed_unverified": ("indexed", "נסרק, טרם אומת", "הקובץ נקלט לבדיקה מקומית, אך לא נמצא לו מקור עצמאי שאפשר להסתמך עליו."),
    "graph_only": ("unsupported", "ללא אסמכתא", "לא נמצא מקור ראשוני שאפשר להישען עליו."),
    "ledger_supported": ("unsupported", "יש רישום, חסר מקור", "יש סימן תמיכה פנימי, אבל חסר מקור ראשוני."),
    "corroborated_no_source": ("unsupported", "יש חיזוק, חסר מקור", "יש חיזוק, אבל אין אסמכתא ראשונית."),
    "refuted_or_blocked": ("contradiction", "חסום או מופרך", "הקובץ סומן כלא מתאים להסתמכות."),
}

CATEGORY_LABELS = {
    "ready": "מוכן לשימוש",
    "backed": "מגובה, דורש אימות נוסף",
    "indexed": "נסרק, טרם אומת",
    "synthesis": "סיכום שצריך השלמת מקורות",
    "unsupported": "חסר אסמכתא",
    "contradiction": "סתירה או חסם אמון",
}
