from __future__ import annotations

from html import escape
from typing import Any


def _remediation_rows(report: dict[str, Any]) -> str:
    rows = "\n".join(
        "<tr>"
        f"<td>{int(row.get('priority', 0))}</td>"
        f"<td>{escape(str(row.get('file', '')))}</td>"
        f"<td>{escape(str(row.get('finding', '')))}</td>"
        f"<td>{escape(str(row.get('action', '')))}</td>"
        "</tr>"
        for row in report.get("remediation", [])
    )
    return rows or '<tr><td colspan="4">לא נמצאו פעולות תיקון.</td></tr>'


def _source_rows(report: dict[str, Any]) -> str:
    return "\n".join(
        "<tr>"
        f"<td><span class=\"pill {escape(str(row['category']))}\">{escape(str(row['status']))}</span></td>"
        f"<td>{escape(str(row['file']))}</td>"
        f"<td>{escape(str(row.get('action') or '-'))}</td>"
        "</tr>"
        for row in report.get("rows", [])
    )


def _delta_section(delta: dict[str, Any]) -> str:
    if not delta.get("has_previous"):
        return ""
    return f"""<section><h2>שינוי מהבדיקה הקודמת</h2><div class="metrics">
      <div class="metric"><b>{int(delta.get('ready', 0)):+d}</b><span>שינוי במוכנים</span></div>
      <div class="metric"><b>{int(delta.get('review', 0)):+d}</b><span>שינוי לבדיקה</span></div>
      <div class="metric"><b>{int(delta.get('blocked', 0)):+d}</b><span>שינוי בחסמים</span></div>
      <div class="metric"><b>{int(delta.get('corpus_issues', 0)):+d}</b><span>שינוי בבעיות corpus</span></div>
    </div></section>"""


def render_report_html(report: dict[str, Any]) -> str:
    project = dict(report.get("project", {}))
    verdict = dict(report.get("verdict", {}))
    scope = dict(report.get("scope_impact", {}))
    diagnostic_counts = dict(report.get("diagnostics", {}).get("counts", {}))
    verdict_class = escape(str(verdict.get("status", "conditional_go")))
    return f"""<!doctype html>
<html lang="he" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Anti-Silo Preflight - {escape(str(project.get('project_name', 'RAG')))}</title>
  <style>
    :root {{ --ink:#17212b; --muted:#5f6b76; --line:#d9e1e8; --ok:#1f7a4d; --warn:#9a6500; --bad:#b3261e; }}
    * {{ box-sizing:border-box; }}
    body {{ font-family:Arial,"Noto Sans Hebrew",sans-serif; color:var(--ink); margin:0; background:#fff; line-height:1.5; }}
    header,main,footer {{ max-width:1080px; margin:0 auto; padding:28px 32px; }}
    header {{ border-bottom:1px solid var(--line); }}
    h1 {{ margin:0 0 6px; font-size:30px; }} h2 {{ margin:0 0 12px; font-size:20px; }}
    section {{ padding:24px 0; border-bottom:1px solid var(--line); }}
    .eyebrow,.meta {{ color:var(--muted); font-weight:700; }} .meta {{ margin-top:8px; font-weight:400; }}
    .verdict {{ border-right:6px solid var(--warn); padding:18px; background:#fbfcfd; }}
    .verdict.go {{ border-right-color:var(--ok); }} .verdict.stop {{ border-right-color:var(--bad); }}
    .verdict strong {{ display:block; font-size:25px; margin:4px 0; }}
    .metrics {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; }}
    .metric {{ border:1px solid var(--line); border-radius:8px; padding:14px; }}
    .metric b {{ display:block; font-size:24px; }}
    table {{ width:100%; border-collapse:collapse; }}
    th,td {{ border-bottom:1px solid var(--line); padding:10px; text-align:right; vertical-align:top; }}
    th {{ background:#eef3f8; }}
    .pill {{ display:inline-block; border-radius:999px; padding:4px 8px; font-weight:700; }}
    .ready {{ color:var(--ok); }} .backed,.synthesis,.indexed {{ color:var(--warn); }} .unsupported,.contradiction {{ color:var(--bad); }}
    .boundary {{ padding:14px; background:#fff8e8; border:1px solid #f0d99a; }}
    footer {{ color:var(--muted); font-size:13px; }}
    @media (max-width:700px) {{ header,main,footer {{ padding:20px; }} .metrics {{ grid-template-columns:1fr 1fr; }} table {{ font-size:13px; }} }}
    @media print {{ header,main,footer {{ max-width:none; padding:12mm 0; }} section {{ break-inside:avoid; }} }}
  </style>
</head>
<body>
  <header>
    <div class="eyebrow">Anti-Silo Preflight · RAG Source Audit</div>
    <h1>{escape(str(project.get('project_name', 'בדיקת מקורות RAG')))}</h1>
    <div>{escape(str(project.get('client_name', 'לקוח')))}</div>
    <div class="meta">הוכן על ידי {escape(str(project.get('consultant_name') or 'יועץ ה-AI'))} · {escape(str(report.get('generated_at', ''))[:10])}</div>
  </header>
  <main>
    <section><div class="verdict {verdict_class}"><span>{escape(str(verdict.get('label', 'CONDITIONAL GO')))}</span><strong>{escape(str(verdict.get('title', '')))}</strong><div>{escape(str(verdict.get('summary', '')))}</div></div></section>
    <section><h2>השפעת היקף</h2><div class="metrics">
      <div class="metric"><b>{int(scope.get('total', 0))}</b><span>קבצים בתיקייה</span></div>
      <div class="metric"><b>{int(scope.get('ready', 0))}</b><span>עברו מדיניות</span></div>
      <div class="metric"><b>{int(scope.get('review', 0))}</b><span>דורשים בדיקה</span></div>
      <div class="metric"><b>{int(scope.get('blocked', 0))}</b><span>חסמים</span></div>
    </div></section>
    {_delta_section(dict(report.get('delta', {})))}
    <section><h2>תוכנית תיקון</h2><table><thead><tr><th>עדיפות</th><th>קובץ</th><th>ממצא</th><th>פעולה</th></tr></thead><tbody>{_remediation_rows(report)}</tbody></table></section>
    <section><h2>אבחון corpus</h2><div class="metrics">
      <div class="metric"><b>{int(diagnostic_counts.get('unsupported_files', 0))}</b><span>פורמטים לא נתמכים</span></div>
      <div class="metric"><b>{int(diagnostic_counts.get('duplicate_files', 0))}</b><span>עותקים כפולים</span></div>
      <div class="metric"><b>{int(diagnostic_counts.get('extraction_failed', 0))}</b><span>כשלי חילוץ</span></div>
      <div class="metric"><b>{int(diagnostic_counts.get('extraction_truncated', 0))}</b><span>חילוץ חלקי</span></div>
    </div></section>
    <section><h2>פירוט מדיניות המקורות</h2><table><thead><tr><th>מצב</th><th>קובץ</th><th>מה לעשות</th></tr></thead><tbody>{_source_rows(report)}</tbody></table></section>
    <section><div class="boundary"><b>גבול אמון</b><br>{escape(str(report.get('trust_boundary', '')))}</div></section>
  </main>
  <footer>הדוח נוצר מקומית. שמות ונתיבי תיקיות מקומיים אינם נשלחים לשירות חיצוני.</footer>
</body>
</html>
"""
