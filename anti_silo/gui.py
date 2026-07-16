from __future__ import annotations

import json
import threading
import webbrowser
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlparse

from .config import output_dir
from .ingest import write_ingest
from .pulse import write_pulse


HUMAN_TIERS = {
    "triangulated": ("ready", "מאומת", "הקובץ מגובה במקור ויש לו חיזוק נוסף."),
    "source_backed": ("backed", "מגובה במקור", "יש אסמכתא ראשונית, אבל כדאי להוסיף אימות נוסף לפני הסתמכות חזקה."),
    "graph_only": ("unsupported", "ללא אסמכתא", "לא נמצא מקור ראשוני שאפשר להישען עליו."),
    "ledger_supported": ("unsupported", "יש רישום, חסר מקור", "יש סימן תמיכה פנימי, אבל חסר מקור ראשוני."),
    "corroborated_no_source": ("unsupported", "יש חיזוק, חסר מקור", "יש חיזוק, אבל אין אסמכתא ראשונית."),
    "refuted_or_blocked": ("contradiction", "חסום או מופרך", "הקובץ סומן כלא מתאים להסתמכות."),
}

CATEGORY_LABELS = {
    "ready": "מוכן לשימוש",
    "backed": "מגובה, דורש אימות נוסף",
    "synthesis": "סיכום שצריך השלמת מקורות",
    "unsupported": "חסר אסמכתא",
    "contradiction": "סתירה או חסם אמון",
}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _source_lookup(ingest_payload: dict[str, Any]) -> dict[str, str]:
    return {str(row["staged_file"]): str(row["source_file"]) for row in ingest_payload.get("rows", [])}


def _penalty_lookup(penalty_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row["file"]): row for row in penalty_payload.get("rows", [])}


def _human_row(row: dict[str, Any], sources: dict[str, str], penalties: dict[str, dict[str, Any]]) -> dict[str, Any]:
    tier = str(row.get("tier", "graph_only"))
    reason = str(row.get("reason", ""))
    category, label, explanation = HUMAN_TIERS.get(tier, ("unsupported", tier, "דורש בדיקה ידנית."))
    if tier == "graph_only" and reason == "synthesis_without_source_spine":
        category = "synthesis"
        label = "סיכום, לא מקור ראשוני"
        explanation = "זה נראה כמו סיכום או מסגרת חשיבה, אבל חסרה רשימת מקורות מסודרת."

    penalty = penalties.get(str(row.get("file", "")), {})
    if penalty.get("hard_block") is True:
        category = "contradiction"
        label = "חסם אמון"
        explanation = "נמצאה בעיית אמון שמונעת הסתמכות לפני תיקון."

    return {
        "file": sources.get(str(row.get("file", "")), row.get("file", "")),
        "staged_file": row.get("file", ""),
        "category": category,
        "category_label": CATEGORY_LABELS.get(category, category),
        "status": label,
        "explanation": explanation,
        "technical_tier": tier,
        "technical_reason": reason,
        "needs": row.get("needs", ""),
        "penalty_rules": penalty.get("rules", []),
    }


def render_report_html(report: dict[str, Any]) -> str:
    rows = "\n".join(
        "<tr>"
        f"<td><span class=\"pill {escape(str(row['category']))}\">{escape(str(row['status']))}</span></td>"
        f"<td>{escape(str(row['file']))}</td>"
        f"<td>{escape(str(row['explanation']))}</td>"
        f"<td>{escape(str(row.get('needs') or '-'))}</td>"
        "</tr>"
        for row in report.get("rows", [])
    )
    metrics = "\n".join(
        f"<div class=\"metric {key}\"><b>{int(report.get('counts', {}).get(key, 0))}</b><span>{escape(CATEGORY_LABELS[key])}</span></div>"
        for key in ["ready", "backed", "synthesis", "unsupported", "contradiction"]
    )
    return f"""<!doctype html>
<html lang="he" dir="rtl">
<head>
  <meta charset="utf-8">
  <title>Anti-Silo Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; color:#17212b; margin:32px; }}
    h1 {{ margin-bottom: 6px; }}
    .meta {{ color:#5f6b76; margin-bottom:22px; }}
    .summary {{ display:grid; grid-template-columns:repeat(5,1fr); gap:10px; margin:18px 0; }}
    .metric {{ border:1px solid #d9e1e8; border-radius:8px; padding:12px; }}
    .metric b {{ display:block; font-size:24px; }}
    table {{ width:100%; border-collapse:collapse; margin-top:18px; }}
    th, td {{ border-bottom:1px solid #d9e1e8; padding:10px; text-align:right; vertical-align:top; }}
    th {{ background:#eef3f8; }}
    .pill {{ display:inline-block; border-radius:999px; padding:4px 8px; font-weight:700; }}
    .ready {{ color:#1f7a4d; }} .backed,.synthesis {{ color:#9a6500; }} .unsupported,.contradiction {{ color:#b3261e; }}
    @media print {{ body {{ margin: 18mm; }} }}
  </style>
</head>
<body>
  <h1>Anti-Silo Report</h1>
  <div class="meta">תיקייה: {escape(str(report.get("source_root", "")))}<br>החלטת מערכת: {escape(str(report.get("decision", "")))}<br>קבצים שנסרקו: {int(report.get("files", 0))}</div>
  <section class="summary">{metrics}</section>
  <table>
    <thead><tr><th>מצב</th><th>קובץ</th><th>מה זה אומר</th><th>מה חסר</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</body>
</html>
"""


def build_human_report(source_root: Path, config: dict[str, Any], output_vault: Path | None = None) -> dict[str, Any]:
    ingest_payload = write_ingest(source_root, config, output_vault=output_vault)
    staged_vault = Path(str(ingest_payload["output_vault"]))
    pulse_payload = write_pulse(staged_vault, config)
    out = output_dir(staged_vault, config)
    triangulation = _read_json(out / "triangulation_gate.json")
    penalties = _read_json(out / "contradiction_penalty.json")

    sources = _source_lookup(ingest_payload)
    penalty_by_file = _penalty_lookup(penalties)
    rows = [_human_row(row, sources, penalty_by_file) for row in triangulation.get("rows", [])]
    counts = {key: 0 for key in CATEGORY_LABELS}
    for row in rows:
        counts[row["category"]] = counts.get(row["category"], 0) + 1

    report: dict[str, Any] = {
        "source_root": str(Path(source_root).resolve()),
        "staged_vault": str(staged_vault),
        "output_dir": str(out),
        "decision": pulse_payload["decision"],
        "files": ingest_payload["files"],
        "counts": counts,
        "rows": rows,
    }
    report_path = out / "ANTI_SILO_REPORT.html"
    report_path.write_text(render_report_html(report), encoding="utf-8")

    downloads = {
        "html_report": report_path,
        "allowed_sources": out / "eligible_sources.csv",
        "source_todo": out / "source_spine_todo.csv",
        "pulse_markdown": out / "PULSE.md",
        "manifest": staged_vault / "SOURCE_MANIFEST.json",
    }
    report["downloads"] = {name: str(path) for name, path in downloads.items() if path.exists()}
    return report


HTML = r"""<!doctype html>
<html lang="he" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Anti-Silo Local</title>
  <style>
    :root { color-scheme: light; --ok:#1f7a4d; --warn:#9a6500; --bad:#b3261e; --ink:#17212b; --muted:#5f6b76; --line:#d9e1e8; --bg:#f6f8fa; }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: Arial, "Noto Sans Hebrew", sans-serif; background: var(--bg); color: var(--ink); }
    header { padding: 28px 32px 18px; background: #fff; border-bottom: 1px solid var(--line); }
    h1 { margin: 0 0 8px; font-size: 28px; }
    p { margin: 0; color: var(--muted); line-height: 1.55; }
    main { max-width: 1120px; margin: 0 auto; padding: 24px; }
    .panel { background: #fff; border: 1px solid var(--line); border-radius: 8px; padding: 20px; margin-bottom: 18px; }
    label { display:block; font-weight: 700; margin-bottom: 8px; }
    .row { display: grid; grid-template-columns: 1fr 160px; gap: 12px; align-items: end; }
    input, button { font: inherit; min-height: 42px; border-radius: 6px; border: 1px solid var(--line); }
    input { width: 100%; padding: 0 12px; background: #fff; direction:ltr; text-align:left; }
    button { padding: 0 16px; border: 0; background: #1d4ed8; color: #fff; font-weight: 700; cursor: pointer; }
    button.secondary { background:#eef3f8; color:#17212b; border:1px solid var(--line); }
    button:disabled { opacity: .55; cursor: wait; }
    .hint { margin-top: 8px; font-size: 13px; color: var(--muted); }
    .dropzone { margin-top: 14px; border: 2px dashed #b8c4d0; border-radius: 8px; padding: 22px; text-align: center; background:#fbfcfd; color:var(--muted); }
    .dropzone.active { border-color:#1d4ed8; background:#edf4ff; color:#17212b; }
    .summary { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; }
    .metric { background: #fff; border: 1px solid var(--line); border-radius: 8px; padding: 14px; }
    .metric b { display:block; font-size: 24px; margin-bottom: 4px; }
    .ready b { color: var(--ok); } .backed b, .synthesis b { color: var(--warn); } .unsupported b, .contradiction b { color: var(--bad); }
    table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
    th, td { padding: 11px 12px; border-bottom: 1px solid var(--line); text-align: right; vertical-align: top; }
    th { background: #eef3f8; font-size: 13px; color: #344252; }
    tr:last-child td { border-bottom: 0; }
    .pill { display:inline-block; padding: 4px 8px; border-radius: 999px; font-size: 12px; font-weight: 700; }
    .pill.ready { background:#e7f5ed; color:var(--ok); }
    .pill.backed, .pill.synthesis { background:#fff4d8; color:var(--warn); }
    .pill.unsupported, .pill.contradiction { background:#fdebea; color:var(--bad); }
    .downloads a { display:inline-block; margin: 6px 0 0 8px; color:#1d4ed8; font-weight:700; }
    .actions { display:flex; flex-wrap:wrap; gap:10px; margin-top:12px; }
    .empty { color: var(--muted); padding: 18px; }
    @media (max-width: 800px) { .row, .summary { grid-template-columns: 1fr; } main { padding: 14px; } }
  </style>
</head>
<body>
  <header>
    <h1>Anti-Silo Local</h1>
    <p>סריקה מקומית ודטרמיניסטית: אילו קבצים מגובים, אילו הם סיכומים, ואילו לא מתאימים להסתמכות.</p>
  </header>
  <main>
    <section class="panel">
      <label for="path">תיקייה לסריקה</label>
      <div class="row">
        <input id="path" placeholder="C:\Users\me\Desktop\project-docs">
        <button id="scan">סרוק ואמת</button>
      </div>
      <div id="dropzone" class="dropzone">גרור תיקייה לכאן, או הדבק נתיב מקומי בשדה למעלה.</div>
      <div class="hint">הכל רץ על המחשב שלך דרך 127.0.0.1. לא מתבצעת קריאת רשת ולא נשלחים קבצים לענן.</div>
    </section>

    <section id="status" class="panel empty">ממתין לתיקייה.</section>
    <section id="summary" class="summary" hidden></section>
    <section id="downloads" class="panel downloads" hidden></section>
    <section id="wizard" class="panel" hidden></section>
    <section id="results" hidden></section>
  </main>
  <script>
    const labels = {
      ready: 'מוכן לשימוש',
      backed: 'מגובה, דורש אימות נוסף',
      synthesis: 'סיכום שצריך השלמת מקורות',
      unsupported: 'חסר אסמכתא',
      contradiction: 'סתירה או חסם אמון'
    };
    const downloadNames = {
      html_report: 'שמור דוח HTML',
      allowed_sources: 'רשימת מקורות מותרים',
      source_todo: 'תבנית להשלמת מקורות',
      pulse_markdown: 'דוח טכני',
      manifest: 'מניפסט מקור'
    };
    const statusEl = document.getElementById('status');
    const summaryEl = document.getElementById('summary');
    const resultsEl = document.getElementById('results');
    const downloadsEl = document.getElementById('downloads');
    const wizardEl = document.getElementById('wizard');
    const dropzone = document.getElementById('dropzone');
    const button = document.getElementById('scan');
    let lastReport = null;

    function metric(key, value) {
      return `<div class="metric ${key}"><b>${value || 0}</b><span>${labels[key]}</span></div>`;
    }

    function table(rows) {
      const htmlRows = rows.map(row => `
        <tr>
          <td><span class="pill ${row.category}">${row.status}</span></td>
          <td>${row.file}</td>
          <td>${row.explanation}</td>
          <td>${row.needs || '-'}</td>
        </tr>`).join('');
      return `<table><thead><tr><th>מצב</th><th>קובץ</th><th>מה זה אומר</th><th>מה חסר</th></tr></thead><tbody>${htmlRows}</tbody></table>`;
    }

    function render(data) {
      lastReport = data;
      statusEl.className = 'panel';
      statusEl.innerHTML = `<b>הסריקה הסתיימה.</b><br>נסרקו ${data.files} קבצים. החלטת מערכת: <code>${data.decision}</code>`;
      summaryEl.hidden = false;
      summaryEl.innerHTML = ['ready','backed','synthesis','unsupported','contradiction'].map(k => metric(k, data.counts[k])).join('');

      const links = Object.entries(data.downloads || {}).map(([name, path]) => {
        return `<a href="/download?path=${encodeURIComponent(path)}">${downloadNames[name] || name}</a>`;
      }).join('');
      downloadsEl.hidden = false;
      downloadsEl.innerHTML = `<b>ייצוא:</b><br>${links || 'אין קבצי ייצוא זמינים.'}<div class="hint">אפשר לפתוח את דוח ה-HTML ולשמור PDF דרך Print / Save as PDF בדפדפן.</div>`;

      const needsRepair = (data.counts.synthesis || 0) + (data.counts.unsupported || 0) + (data.counts.contradiction || 0);
      wizardEl.hidden = needsRepair === 0;
      if (needsRepair > 0) {
        wizardEl.innerHTML = `
          <b>אשף תיקון</b>
          <p class="hint">נמצאו ${needsRepair} פריטים שדורשים השלמת אסמכתאות או תיקון אמון.</p>
          <div class="actions">
            <button class="secondary" type="button" onclick="downloadTodo()">צור תבנית להשלמת מקורות</button>
            <button class="secondary" type="button" onclick="filterNeedsRepair()">הצג רק מה שדורש תיקון</button>
          </div>`;
      }

      resultsEl.hidden = false;
      resultsEl.innerHTML = table(data.rows);
    }

    function downloadTodo() {
      const path = lastReport && lastReport.downloads && lastReport.downloads.source_todo;
      if (path) window.location.href = `/download?path=${encodeURIComponent(path)}`;
    }

    function filterNeedsRepair() {
      if (!lastReport) return;
      resultsEl.innerHTML = table(lastReport.rows.filter(row => row.category !== 'ready' && row.category !== 'backed'));
    }

    async function scan() {
      const path = document.getElementById('path').value.trim();
      if (!path) return;
      button.disabled = true;
      statusEl.className = 'panel empty';
      statusEl.textContent = 'סורק ומאמת...';
      try {
        const response = await fetch('/api/scan', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({path})
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'scan failed');
        render(data);
      } catch (err) {
        statusEl.className = 'panel';
        statusEl.innerHTML = `<b>הסריקה נכשלה.</b><br>${err.message}`;
      } finally {
        button.disabled = false;
      }
    }
    button.addEventListener('click', scan);
    document.getElementById('path').addEventListener('keydown', event => { if (event.key === 'Enter') scan(); });
    dropzone.addEventListener('dragover', event => { event.preventDefault(); dropzone.classList.add('active'); });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('active'));
    dropzone.addEventListener('drop', event => {
      event.preventDefault();
      dropzone.classList.remove('active');
      const file = event.dataTransfer.files && event.dataTransfer.files[0];
      if (file && file.path) {
        document.getElementById('path').value = file.path;
        scan();
      } else {
        statusEl.className = 'panel';
        statusEl.innerHTML = '<b>הדפדפן לא חשף נתיב תיקייה מלא.</b><br>בגרסת דפדפן רגילה יש להדביק את הנתיב בשדה. באריזת Desktop הפעולה הזו תעבוד כגרירה מלאה.';
      }
    });
  </script>
</body>
</html>
"""


class AntiSiloGuiHandler(BaseHTTPRequestHandler):
    server_version = "AntiSiloGUI/0.1"

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/":
            body = HTML.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/download":
            query = dict(part.split("=", 1) for part in parsed.query.split("&") if "=" in part)
            path = Path(unquote(query.get("path", ""))).resolve()
            allowed_roots = getattr(self.server, "allowed_roots", [])
            if not any(path.is_relative_to(root) for root in allowed_roots) or not path.exists():
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            data = path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{quote(path.name)}")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/api/scan":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            source_root = Path(str(payload.get("path", ""))).expanduser().resolve()
            if not source_root.exists():
                raise ValueError("התיקייה לא קיימת")
            report = build_human_report(source_root, self.server.config)
            self.server.allowed_roots = [Path(report["staged_vault"]).resolve(), Path(report["output_dir"]).resolve()]
            self._send_json(report)
        except Exception as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def log_message(self, format: str, *args: Any) -> None:
        return


class AntiSiloGuiServer(ThreadingHTTPServer):
    config: dict[str, Any]
    allowed_roots: list[Path]


def serve_gui(config: dict[str, Any], host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> str:
    server = AntiSiloGuiServer((host, port), AntiSiloGuiHandler)
    server.config = config
    server.allowed_roots = []
    url = f"http://{server.server_address[0]}:{server.server_address[1]}/"
    if open_browser:
        threading.Timer(0.3, lambda: webbrowser.open(url)).start()
    try:
        print(f"Anti-Silo GUI running locally at {url}")
        server.serve_forever()
    finally:
        server.server_close()
    return url
