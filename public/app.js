(function () {
  "use strict";

  const MAX_FILES = 150;
  const MAX_FILE_BYTES = 1500000;
  const MAX_TOTAL_BYTES = 2800000;
  const CONTENT_EXTENSIONS = new Set([
    ".csv", ".docx", ".htm", ".html", ".json", ".md", ".pdf", ".txt", ".xlsx"
  ]);
  const EXCLUDED_DIRS = new Set([
    ".git", ".obsidian", ".venv", "__pycache__", "anti_silo_out", "build", "dist", "node_modules", "vendor"
  ]);

  const folderInput = document.getElementById("folder-input");
  const chooseButton = document.getElementById("choose-folder");
  const dropzone = document.getElementById("dropzone");
  const selection = document.getElementById("selection");
  const selectionTitle = document.getElementById("selection-title");
  const selectionDetail = document.getElementById("selection-detail");
  const clearButton = document.getElementById("clear-selection");
  const runButton = document.getElementById("run-scan");
  const demoButton = document.getElementById("run-demo");
  const consentCheckbox = document.getElementById("cloud-consent");
  const websiteInput = document.getElementById("website");
  const readyHint = document.getElementById("ready-hint");
  const errorMessage = document.getElementById("error-message");
  const setup = document.getElementById("setup");
  const processing = document.getElementById("processing");
  const results = document.getElementById("results");
  const autoDemo = new URLSearchParams(window.location.search).get("demo") === "1";
  let selectedFiles = [];
  let lastReport = null;

  function extension(path) {
    const index = path.lastIndexOf(".");
    return index >= 0 ? path.slice(index).toLowerCase() : "";
  }

  function relativePath(file) {
    const raw = (file.webkitRelativePath || file.name).replaceAll("\\", "/");
    const parts = raw.split("/").filter(Boolean);
    return parts.length > 1 ? parts.slice(1).join("/") : parts[0];
  }

  function excluded(path) {
    return path.split("/").some(function (part) {
      return EXCLUDED_DIRS.has(part);
    });
  }

  function formatBytes(bytes) {
    if (bytes < 1024) return bytes + " B";
    return (bytes / 1024 / 1024).toFixed(2) + " MB";
  }

  function showError(message) {
    errorMessage.textContent = message;
    errorMessage.hidden = false;
    errorMessage.focus();
  }

  function clearError() {
    errorMessage.hidden = true;
    errorMessage.textContent = "";
  }

  function updateRunAvailability() {
    runButton.disabled = !selectedFiles.length || !consentCheckbox.checked;
    if (!selectedFiles.length) {
      readyHint.textContent = "בחרו תיקייה כדי להתחיל";
    } else if (!consentCheckbox.checked) {
      readyHint.textContent = "אשרו עיבוד זמני בענן כדי לסרוק";
    } else {
      readyHint.textContent = "הבחירה מוכנה לסריקה";
    }
  }

  function updateSelection(fileList) {
    clearError();
    const files = Array.from(fileList).map(function (file) {
      return { file: file, path: relativePath(file), supported: CONTENT_EXTENSIONS.has(extension(file.name)) };
    }).filter(function (item) {
      return item.path && !excluded(item.path);
    });

    if (!files.length) {
      clearSelection();
      showError("לא נמצאו קבצים מתאימים בתיקייה שנבחרה.");
      return;
    }
    if (files.length > MAX_FILES) {
      clearSelection();
      showError("הבחירה כוללת " + files.length + " קבצים. המגבלה בגרסת Web היא " + MAX_FILES + ".");
      return;
    }

    const supported = files.filter(function (item) { return item.supported; });
    const totalBytes = supported.reduce(function (sum, item) { return sum + item.file.size; }, 0);
    const oversized = supported.find(function (item) { return item.file.size > MAX_FILE_BYTES; });
    if (oversized) {
      clearSelection();
      showError("הקובץ " + oversized.path + " גדול מ־1.5 MB. יש להסיר אותו או להשתמש בגרסת Desktop.");
      return;
    }
    if (totalBytes > MAX_TOTAL_BYTES) {
      clearSelection();
      showError("הקבצים הנתמכים שוקלים " + formatBytes(totalBytes) + ". מגבלת הסריקה היא 2.8 MB.");
      return;
    }
    if (!supported.length) {
      clearSelection();
      showError("לא נמצאו בתיקייה קבצים בפורמט שניתן לסרוק.");
      return;
    }

    selectedFiles = files;
    selection.hidden = false;
    selectionTitle.textContent = files.length + " קבצים נבחרו";
    selectionDetail.textContent = supported.length + " ייסרקו, " + (files.length - supported.length) + " יסומנו כפורמט לא נתמך, " + formatBytes(totalBytes);
    updateRunAvailability();
  }

  function clearSelection() {
    selectedFiles = [];
    folderInput.value = "";
    selection.hidden = true;
    updateRunAvailability();
  }

  function arrayBufferToBase64(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = "";
    const chunkSize = 32768;
    for (let offset = 0; offset < bytes.length; offset += chunkSize) {
      binary += String.fromCharCode.apply(null, bytes.subarray(offset, offset + chunkSize));
    }
    return btoa(binary);
  }

  async function serializeFiles() {
    const output = [];
    for (const item of selectedFiles) {
      output.push({
        path: item.path,
        content_base64: item.supported ? arrayBufferToBase64(await item.file.arrayBuffer()) : ""
      });
    }
    return output;
  }

  function projectPayload() {
    return {
      client_name: document.getElementById("client-name").value,
      project_name: document.getElementById("project-name").value,
      consultant_name: document.getElementById("consultant-name").value
    };
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function verdictClass(status) {
    if (status === "go") return "go";
    if (status === "stop") return "stop";
    return "conditional";
  }

  function severityClass(value) {
    return String(value || "Low").toLowerCase();
  }

  function renderReport(report) {
    const verdict = report.verdict || {};
    const score = report.readiness_score || {};
    const scoreComponents = score.components || {};
    const scope = report.scope_impact || {};
    const executive = report.executive_summary || {};
    const effort = report.effort_estimate || {};
    const risks = report.risk_register || [];
    const actions = report.remediation || [];

    const verdictElement = document.getElementById("verdict");
    verdictElement.className = "verdict-band " + verdictClass(verdict.status);
    document.getElementById("verdict-label").textContent = verdict.label || verdict.status || "PRE-FLIGHT";
    document.getElementById("verdict-title").textContent = verdict.title || "הבדיקה הושלמה";
    document.getElementById("verdict-summary").textContent = executive.he || verdict.summary || "";
    document.getElementById("score-value").textContent = Number(score.score || 0);
    document.getElementById("score-label").textContent = score.label_he || "";
    const scoreValue = Math.max(0, Math.min(100, Number(score.score || 0)));
    document.getElementById("score-fill").style.width = scoreValue + "%";
    document.getElementById("score-meter").setAttribute("aria-valuenow", String(scoreValue));
    document.getElementById("score-weighted-base").textContent = Number(scoreComponents.weighted_base || 0);
    document.getElementById("score-duplicate-penalty").textContent =
      scoreComponents.duplicate_penalty ? "-" + Number(scoreComponents.duplicate_penalty) : "0";
    document.getElementById("score-stop-findings").textContent = Number(scoreComponents.stop_findings || 0);
    document.getElementById("score-stop-cap").textContent = scoreComponents.stop_cap_applied ? "כן, ל-49" : "לא";
    document.getElementById("score-methodology").textContent = score.methodology || "";
    document.getElementById("trust-boundary").textContent = report.trust_boundary || "";
    document.getElementById("metric-total").textContent = Number(scope.total || report.files || 0);
    document.getElementById("metric-ready").textContent = Number(scope.ready || 0);
    document.getElementById("metric-review").textContent = Number(scope.review || 0);
    document.getElementById("metric-blocked").textContent = Number(scope.blocked || 0);

    document.getElementById("effort-estimate").textContent =
      Number(effort.minimum_hours || 0) + "–" + Number(effort.maximum_hours || 0) + " שעות תיקון משוערות";

    const actionList = document.getElementById("action-list");
    actionList.innerHTML = actions.slice(0, 6).map(function (action) {
      return "<li><b>" + escapeHtml(action.file || "Corpus") + "</b><span>" +
        escapeHtml(action.action || action.finding || "") + "</span></li>";
    }).join("") || "<li><b>לא נמצאו פעולות דחופות</b><span>אפשר להמשיך לבדיקת התאמה מקצועית של התוכן.</span></li>";

    const riskBody = document.getElementById("risk-body");
    riskBody.innerHTML = risks.slice(0, 20).map(function (risk) {
      return "<tr><td>" + escapeHtml(risk.risk_id) + "</td><td><span class=\"severity " +
        severityClass(risk.severity) + "\">" + escapeHtml(risk.severity) + "</span></td><td>" +
        escapeHtml(risk.file) + "</td><td>" + escapeHtml(risk.description) + "</td><td>" +
        escapeHtml(risk.recommendation) + "</td></tr>";
    }).join("") || "<tr><td colspan=\"5\">לא נמצאו סיכונים לרישום.</td></tr>";
  }

  async function requestScan(payload) {
    clearError();
    runButton.disabled = true;
    demoButton.disabled = true;
    setup.hidden = true;
    processing.hidden = false;
    results.hidden = true;

    try {
      const response = await fetch("/api/scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await response.json().catch(function () { return {}; });
      if (!response.ok) throw new Error(data.error || "הסריקה נכשלה.");
      lastReport = data;
      renderReport(data);
      processing.hidden = true;
      results.hidden = false;
      results.scrollIntoView({ behavior: autoDemo ? "auto" : "smooth", block: "start" });
    } catch (error) {
      processing.hidden = true;
      setup.hidden = false;
      demoButton.disabled = false;
      updateRunAvailability();
      showError(error.message || "לא ניתן היה להשלים את הסריקה.");
    }
  }

  async function runScan() {
    if (!selectedFiles.length || !consentCheckbox.checked) return;
    await requestScan({
      files: await serializeFiles(),
      project: projectPayload(),
      consent: true,
      website: websiteInput.value
    });
  }

  async function runDemo() {
    await requestScan({
      demo: true,
      website: websiteInput.value
    });
  }

  function csvCell(value) {
    return '"' + String(value == null ? "" : value).replaceAll('"', '""') + '"';
  }

  function downloadBlob(name, content, type) {
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([content], { type: type }));
    link.download = name;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(function () { URL.revokeObjectURL(link.href); }, 1000);
  }

  function downloadReport() {
    if (!lastReport) return;
    downloadBlob("anti-silo-preflight.json", JSON.stringify(lastReport, null, 2), "application/json;charset=utf-8");
  }

  function buildClientReport(report) {
    const project = report.project || {};
    const verdict = report.verdict || {};
    const score = report.readiness_score || {};
    const components = score.components || {};
    const scope = report.scope_impact || {};
    const executive = report.executive_summary || {};
    const effort = report.effort_estimate || {};
    const actions = report.remediation || [];
    const risks = report.risk_register || [];
    const generatedAt = report.generated_at
      ? new Date(report.generated_at).toLocaleString("he-IL")
      : new Date().toLocaleString("he-IL");
    const actionRows = actions.slice(0, 10).map(function (action) {
      return "<tr><td>" + escapeHtml(action.priority) + "</td><td>" + escapeHtml(action.file || "Corpus") +
        "</td><td>" + escapeHtml(action.finding || "") + "</td><td>" + escapeHtml(action.action || "") + "</td></tr>";
    }).join("") || "<tr><td colspan=\"4\">לא נמצאו פעולות דחופות.</td></tr>";
    const riskRows = risks.slice(0, 30).map(function (risk) {
      return "<tr><td>" + escapeHtml(risk.risk_id) + "</td><td>" + escapeHtml(risk.severity) + "</td><td>" +
        escapeHtml(risk.file) + "</td><td>" + escapeHtml(risk.description) + "</td><td>" +
        escapeHtml(risk.recommendation) + "</td></tr>";
    }).join("") || "<tr><td colspan=\"5\">לא נמצאו סיכונים לרישום.</td></tr>";

    return `<!doctype html>
<html lang="he" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Anti-Silo Client Preflight</title>
  <style>
    body{margin:0;color:#1f2d27;background:#f4f7f5;font:15px/1.65 Arial,sans-serif}
    main{width:min(calc(100% - 40px),960px);margin:36px auto;background:#fff;border-top:8px solid #17745a;padding:36px;box-sizing:border-box}
    h1,h2,p{margin-top:0}h1{font-size:34px;margin-bottom:4px}h2{margin-top:32px;font-size:21px;border-bottom:1px solid #dce5e1;padding-bottom:8px}
    .meta,.trust{color:#52625b}.verdict{display:grid;grid-template-columns:1fr auto;gap:24px;padding:24px;margin:28px 0;background:#eef4f1;border-right:6px solid #17745a}
    .verdict b{font-size:20px}.score{font-size:48px;font-weight:800;line-height:1}.score small{font-size:16px;color:#52625b}
    .metrics{display:grid;grid-template-columns:repeat(4,1fr);border:1px solid #dce5e1}.metrics div{padding:16px;border-left:1px solid #dce5e1}.metrics div:last-child{border:0}.metrics b{display:block;font-size:25px}
    .ledger{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.ledger div{padding:14px;background:#f4f7f5}.ledger span{display:block;color:#607068;font-size:12px}
    table{width:100%;border-collapse:collapse;font-size:12px}th,td{padding:9px;border:1px solid #dce5e1;text-align:right;vertical-align:top}th{background:#eef4f1}
    .trust{margin-top:30px;padding:18px;border:1px solid #a9bbb3}.footer{margin-top:28px;color:#607068;font-size:11px}
    @media(max-width:680px){main{width:100%;margin:0;padding:22px}.verdict{grid-template-columns:1fr}.metrics,.ledger{grid-template-columns:1fr 1fr}table{font-size:10px}}
    @media print{body{background:#fff}main{width:100%;margin:0;border:0;padding:0}h2{break-after:avoid}table{break-inside:auto}tr{break-inside:avoid}}
  </style>
</head>
<body>
  <main>
    <p class="meta">ANTI-SILO · CONSULTANT PREFLIGHT</p>
    <h1>דוח מוכנות מקורות ל-RAG</h1>
    <p class="meta">לקוח: ${escapeHtml(project.client_name || "לא צוין")} · פרויקט: ${escapeHtml(project.project_name || "לא צוין")} · יועץ: ${escapeHtml(project.consultant_name || "לא צוין")}</p>
    <section class="verdict">
      <div><b>${escapeHtml(verdict.label || verdict.status || "PRE-FLIGHT")}</b><h2>${escapeHtml(verdict.title || "הבדיקה הושלמה")}</h2><p>${escapeHtml(executive.he || verdict.summary || "")}</p></div>
      <div class="score">${escapeHtml(score.score || 0)}<small>/100</small></div>
    </section>
    <section class="metrics">
      <div><b>${escapeHtml(scope.total || report.files || 0)}</b>קבצים</div>
      <div><b>${escapeHtml(scope.ready || 0)}</b>מוכנים</div>
      <div><b>${escapeHtml(scope.review || 0)}</b>דורשים בדיקה</div>
      <div><b>${escapeHtml(scope.blocked || 0)}</b>חסומים</div>
    </section>
    <h2>פירוט הציון</h2>
    <section class="ledger">
      <div><span>בסיס משוקלל</span><b>${escapeHtml(components.weighted_base || 0)}</b></div>
      <div><span>קנס כפילויות</span><b>-${escapeHtml(components.duplicate_penalty || 0)}</b></div>
      <div><span>ממצאי STOP</span><b>${escapeHtml(components.stop_findings || 0)}</b></div>
      <div><span>תקרת STOP</span><b>${components.stop_cap_applied ? "הופעלה" : "לא הופעלה"}</b></div>
    </section>
    <p class="meta">${escapeHtml(score.methodology || "")}</p>
    <h2>תור תיקונים</h2>
    <p class="meta">הערכת תכנון: ${escapeHtml(effort.minimum_hours || 0)}-${escapeHtml(effort.maximum_hours || 0)} שעות, בכפוף לבדיקת מורכבות.</p>
    <table><thead><tr><th>עדיפות</th><th>קובץ</th><th>ממצא</th><th>פעולה</th></tr></thead><tbody>${actionRows}</tbody></table>
    <h2>מרשם סיכונים</h2>
    <table><thead><tr><th>מזהה</th><th>חומרה</th><th>קובץ</th><th>ממצא</th><th>המלצה</th></tr></thead><tbody>${riskRows}</tbody></table>
    <div class="trust"><b>גבול האמון</b><p>${escapeHtml(report.trust_boundary || "")}</p></div>
    <p class="footer">נוצר ב-${escapeHtml(generatedAt)}. הדוח הופק מאותו מנוע דטרמיניסטי שמציג את התוצאה במסך. Anti-Silo אינו מאמת נכונות עובדתית.</p>
  </main>
</body>
</html>`;
  }

  function downloadClientReport() {
    if (!lastReport) return;
    downloadBlob("anti-silo-client-report.html", buildClientReport(lastReport), "text/html;charset=utf-8");
  }

  function downloadRisks() {
    if (!lastReport) return;
    const header = ["risk_id", "severity", "category", "file", "description", "recommendation"];
    const rows = (lastReport.risk_register || []).map(function (risk) {
      return header.map(function (key) { return csvCell(risk[key]); }).join(",");
    });
    downloadBlob("anti-silo-risk-register.csv", "\ufeff" + header.join(",") + "\n" + rows.join("\n"), "text/csv;charset=utf-8");
  }

  function resetScan() {
    lastReport = null;
    results.hidden = true;
    setup.hidden = false;
    demoButton.disabled = false;
    consentCheckbox.checked = false;
    clearSelection();
    clearError();
    setup.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  chooseButton.addEventListener("click", function (event) {
    event.stopPropagation();
    folderInput.click();
  });
  dropzone.addEventListener("click", function () { folderInput.click(); });
  folderInput.addEventListener("change", function () { updateSelection(folderInput.files); });
  clearButton.addEventListener("click", clearSelection);
  consentCheckbox.addEventListener("change", updateRunAvailability);
  runButton.addEventListener("click", runScan);
  demoButton.addEventListener("click", runDemo);
  document.getElementById("download-client-report").addEventListener("click", downloadClientReport);
  document.getElementById("download-report").addEventListener("click", downloadReport);
  document.getElementById("download-risks").addEventListener("click", downloadRisks);
  document.getElementById("new-scan").addEventListener("click", resetScan);

  ["dragenter", "dragover"].forEach(function (name) {
    dropzone.addEventListener(name, function (event) {
      event.preventDefault();
      dropzone.classList.add("dragging");
    });
  });
  ["dragleave", "drop"].forEach(function (name) {
    dropzone.addEventListener(name, function (event) {
      event.preventDefault();
      dropzone.classList.remove("dragging");
    });
  });
  dropzone.addEventListener("drop", function (event) {
    if (event.dataTransfer && event.dataTransfer.files.length) {
      updateSelection(event.dataTransfer.files);
    }
  });

  if (autoDemo) {
    void runDemo();
  }
})();
