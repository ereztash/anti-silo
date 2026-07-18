    function table(rows) {
      const htmlRows = rows.map(row => `<tr><td><span class="pill ${escapeHtml(row.category)}">${escapeHtml(row.status)}</span></td><td class="file-cell">${escapeHtml(row.file)}</td><td>${escapeHtml(row.action || row.explanation)}${row.category === 'indexed' ? `<div class="actions"><button class="secondary" type="button" data-file="${escapeHtml(row.file)}" onclick="attachSource(this.dataset.file)">בחר מקור עצמאי</button></div>` : ''}</td><td class="technical">${escapeHtml(row.technical_tier || '-')}</td><td class="technical">${escapeHtml(row.technical_reason || '-')}</td><td class="technical">${escapeHtml(row.needs || '-')}</td></tr>`).join('');
      return `<div class="panel table-scroll"><table><thead><tr><th>מצב</th><th>קובץ</th><th>מה לעשות</th><th class="technical">Tier</th><th class="technical">Reason</th><th class="technical">Needs</th></tr></thead><tbody>${htmlRows}</tbody></table></div>`;
    }

    function simpleGroup(group) {
      if (!lastReport) return;
      const groups = {ready:['ready'], needs:['backed','indexed','synthesis'], blocked:['unsupported','contradiction']};
      resultsEl.hidden = false;
      resultsEl.innerHTML = table(lastReport.rows.filter(row => groups[group].includes(row.category)));
      recordEvent('result_action_taken', {group});
    }

    function renderSimpleSummary(data) {
      const trusted = data.counts.ready || 0;
      const needs = (data.counts.backed || 0) + (data.counts.indexed || 0) + (data.counts.synthesis || 0);
      const blocked = (data.counts.unsupported || 0) + (data.counts.contradiction || 0);
      simpleSummaryEl.hidden = false;
      simpleSummaryEl.innerHTML = `<button class="simple-card ready" type="button" onclick="simpleGroup('ready')"><b class="num">${trusted}</b><span>עברו את מדיניות המקורות</span></button><button class="simple-card needs" type="button" onclick="simpleGroup('needs')"><b class="num">${needs}</b><span>מומלץ להוסיף מקורות</span></button><button class="simple-card blocked" type="button" onclick="simpleGroup('blocked')"><b class="num">${blocked}</b><span>לא מומלץ להסתמך</span></button>`;
    }

    function renderDownloads(data) {
      const preferredOrder = ['audit_pack','sow_ready','html_report','risk_register','remediation_queue','scan_delta','preflight_summary','client_manifest','allowed_sources','source_todo','pulse_markdown','manifest'];
      const entries = Object.entries(data.downloads || {}).sort(([a],[b]) => preferredOrder.indexOf(a) - preferredOrder.indexOf(b));
      const packPath = (data.downloads || {}).audit_pack;
      const links = entries.filter(([name]) => name !== 'audit_pack').map(([name, path]) => `<a href="${downloadHref(path)}"><span>${downloadNames[name] || name}</span><span aria-hidden="true">↓</span></a>`).join('');
      downloadsEl.hidden = false;
      downloadsEl.innerHTML = `<h2 class="section-title">חבילת מסירה ללקוח</h2><div class="downloads-grid"><div><p class="hint" style="margin-top:0">כל הקבצים נכתבים מקומית ומופקים מאותו מנוע דטרמיניסטי — הדוח, ה-SOW והמניפסטים תמיד מסכימים עם המסך הזה.</p><div class="artifact-list">${links || '<p class="hint">אין קבצי ייצוא זמינים.</p>'}</div></div><div class="export-card"><b>תן ללקוח את ההוכחה</b><p class="hint">Audit Pack אחד: דוח HTML (ניתן לשמירה כ-PDF), תקציר מנהלים דו־לשוני, תור תיקונים, מרשם סיכונים ומניפסט מקורות.</p>${packPath ? `<a class="cta" style="display:block;background:var(--accent);color:var(--accent-ink);text-decoration:none;font-weight:650" href="${downloadHref(packPath)}">הורד Audit Pack (ZIP)</a>` : '<p class="hint">ה-Audit Pack ייווצר לאחר סריקה מלאה.</p>'}<div class="actions"><button class="secondary" type="button" onclick="showTechnicalSummary()">הצג פרטים למתקדמים</button><button class="secondary" type="button" onclick="rescan()">בדיקה חוזרת</button><button class="secondary" type="button" onclick="discardResults()">מחק תוצאות זמניות</button><button class="secondary" type="button" onclick="watchLastFolder()">עקוב אחרי התיקייה</button></div></div></div>`;
    }

    function renderWizard(data) {
      const needsRepair = (data.remediation || []).length;
      wizardEl.hidden = needsRepair === 0;
      if (needsRepair === 0) return;
      wizardEl.innerHTML = `<h2 class="section-title">תור התיקונים — לפי השפעה</h2><p class="hint" style="margin-top:0">הפעולה הבאה: נמצאו ${needsRepair} פעולות — תקן או החרג, הרץ בדיקה חוזרת, והדלתא תימדד מול הסריקה הזו.</p><div class="actions">${data.repair_todo_count > 0 ? '<button class="secondary" type="button" onclick="downloadTodo()">צור תבנית להשלמת מקורות</button>' : ''}<button class="secondary" type="button" onclick="filterNeedsRepair()">הצג רק מה שדורש תיקון</button></div>${data.counts.indexed ? '<p class="hint">לפריט שטרם אומת אפשר לבחור קובץ מקור עצמאי ישירות בטבלה.</p>' : ''}`;
    }

    function render(data) {
      lastReport = data;
      renderVerdict(data);
      summaryEl.hidden = true;
      renderSimpleSummary(data);
      renderWizard(data);
      resultsEl.hidden = false;
      resultsEl.innerHTML = table(data.rows);
      renderCorpus(data);
      renderRiskRegister(data);
      renderWhatIf(data);
      renderDownloads(data);
      loadBrain();
      loadProjects();
    }
