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
  const readyHint = document.getElementById("ready-hint");
  const errorMessage = document.getElementById("error-message");
  const setup = document.getElementById("setup");
  const processing = document.getElementById("processing");
  const results = document.getElementById("results");
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
    runButton.disabled = false;
    readyHint.textContent = "הבחירה מוכנה לסריקה";
  }

  function clearSelection() {
    selectedFiles = [];
    folderInput.value = "";
    selection.hidden = true;
    runButton.disabled = true;
    readyHint.textContent = "בחרו תיקייה כדי להתחיל";
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

  async function runScan() {
    if (!selectedFiles.length || runButton.disabled) return;
    clearError();
    runButton.disabled = true;
    setup.hidden = true;
    processing.hidden = false;
    results.hidden = true;

    try {
      const response = await fetch("/api/scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ files: await serializeFiles(), project: projectPayload() })
      });
      const data = await response.json().catch(function () { return {}; });
      if (!response.ok) throw new Error(data.error || "הסריקה נכשלה.");
      lastReport = data;
      renderReport(data);
      processing.hidden = true;
      results.hidden = false;
      results.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
      processing.hidden = true;
      setup.hidden = false;
      runButton.disabled = false;
      showError(error.message || "לא ניתן היה להשלים את הסריקה.");
    }
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
  runButton.addEventListener("click", runScan);
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
})();
