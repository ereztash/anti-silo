"""Client-facing explanation copy for each diagnostic finding.

Separated from the diagnostics computation so the Web and Desktop surfaces
render the same wording from one source, and so changing what a consultant
says to a client is not a change to how findings are computed.
"""

from __future__ import annotations


# Why each issue matters for a RAG build, in a consultant's words. Keyed by the
# corpus-diagnostic `kind` and by the triangulation `category`, so both the Web
# and Desktop surfaces render the same explanation from this one source.
RAG_IMPACT = {
    # corpus diagnostics
    "unsupported_format": "הקובץ לא ייכנס ל-RAG כלל — הידע שבו יהיה שקוף למנוע האחזור.",
    "empty_file": "קובץ ריק תורם רעש בלי ידע ועלול לדלל את תוצאות האחזור.",
    "extraction_failed": "התוכן חסר — הקובץ יהיה שקוף ל-RAG, אובדן מידע שהלקוח מצפה שיהיה זמין.",
    "extraction_truncated": "רק חלק מהתוכן נכלל — המנוע יאחזר ידע חלקי ועלול לענות על סמך קטע חסר.",
    "exact_duplicate": "אותו תוכן נספר כמה פעמים — מטה את ה-retrieval, העותק הכפול מקבל משקל-יתר בתוצאות.",
    "near_duplicate": "גרסאות כמעט-זהות תופסות כמה מקומות בתוצאות האחזור, דוחקות מקורות אחרים ומנפחות את מסד הווקטורים.",
    "near_duplicate_conflict": "גרסאות חלוקות של אותו מסמך — המנוע יאחזר כמה מהן ואינו יודע איזו עדכנית; זהו מקור מוביל לתשובה בטוחה-אך-שגויה.",
    # triangulation categories
    "contradiction": "חסם-אמון — הסתמכות עליו עלולה להזין את ה-RAG במידע שנמצא סותר או מופרך.",
    "unsupported": "אין מקור ראשוני — ה-LLM עלול להציג טענה לא-מבוססת כעובדה (סכנת הזיה).",
    "indexed": "נקלט בלי אימות מקור — אין דרך לוודא שהאחזור נשען על מקור אמין.",
    "synthesis": "סיכום ללא רשימת-מקורות — ה-LLM עלול להתייחס לפרשנות כאל עובדה (סכנת הזיה).",
    "backed": "יש מקור אך אין חיזוק עצמאי — הסתמכות מלאה מוקדמת מדי לפני אימות נוסף.",
}
