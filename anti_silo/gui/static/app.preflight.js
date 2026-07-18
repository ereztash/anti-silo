    function remediationTable(rows) {
      const severityLabels = {block: 'חסם', review: 'בדיקה', cleanup: 'ניקוי'};
      const htmlRows = rows.map(row => `<tr><td><span class="pill ${escapeHtml(row.severity)}">${escapeHtml(severityLabels[row.severity] || row.severity)}</span></td><td class="file-cell">${escapeHtml(row.file)}</td><td>${escapeHtml(row.finding)}${row.impact ? `<em class="impact-note"><span>למה זה משנה:</span> ${escapeHtml(row.impact)}</em>` : ''}</td><td>${escapeHtml(row.action)}</td></tr>`).join('');
      return `<div class="panel table-scroll"><table><thead><tr><th>עדיפות</th><th>קובץ</th><th>ממצא</th><th>פעולה</th></tr></thead><tbody>${htmlRows || '<tr><td colspan="4">אין פעולות בתור התיקונים.</td></tr>'}</tbody></table></div>`;
    }

    const VERDICT_ICONS = {
      blocked: '<svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true"><path fill="var(--bad)" d="M7.6 2h8.8L22 7.6v8.8L16.4 22H7.6L2 16.4V7.6L7.6 2z"/><rect x="7" y="11" width="10" height="2.4" rx="1.2" fill="#fff"/></svg>',
      needs: '<svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true"><path fill="var(--warn)" d="M12 2.5 22.5 21h-21L12 2.5z"/><rect x="11" y="9" width="2" height="6" rx="1" fill="#0b0b0b"/><circle cx="12" cy="17.4" r="1.3" fill="#0b0b0b"/></svg>',
      ready: '<svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="10" fill="var(--ok)"/><path d="M7.2 12.4 10.6 16 17 8.6" stroke="#fff" stroke-width="2.4" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    };

    function verdictMeta(data) {
      const verdict = data.verdict || {};
      if (verdict.status === 'stop') return {tone:'blocked', kicker:verdict.label || 'STOP', title:verdict.title, body:verdict.summary, action:'הצג את התיקונים החוסמים', group:'blocked'};
      if (verdict.status === 'conditional_go') return {tone:'needs', kicker:verdict.label || 'CONDITIONAL GO', title:verdict.title, body:verdict.summary, action:'הצג מה דורש בדיקה', group:'needs'};
      return {tone:'ready', kicker:verdict.label || 'GO', title:verdict.title, body:verdict.summary, action:'הצג קבצים מאושרים', group:'ready'};
    }

    function recommendedRows(data) {
      return (data.remediation || []).slice(0, 3).map(item => {
        const sourceRow = (data.rows || []).find(row => row.file === item.file);
        return {...item, category: sourceRow && sourceRow.category};
      });
    }

    function scoreLedger(data) {
      const readiness = data.readiness_score || {};
      const parts = readiness.components || {};
      const counts = data.counts || {};
      const total = (data.diagnostics || {}).total_files || 0;
      const counted = Object.keys(TIER_POINTS).reduce((sum, key) => sum + (counts[key] || 0), 0);
      const tierRows = Object.keys(TIER_POINTS).map(key => {
        const count = counts[key] || 0;
        return `<tr class="${count ? '' : 'zero'}"><td>${labels[key]}</td><td class="num">${count}</td><td class="num">${TIER_POINTS[key]}</td><td class="num">${count * TIER_POINTS[key]}</td></tr>`;
      }).join('');
      const outsideRow = total > counted ? `<tr><td>קבצים מחוץ לסריקה (פורמט לא נתמך)</td><td class="num">${total - counted}</td><td class="num">0</td><td class="num">0</td></tr>` : '';
      return `<details class="ledger-toggle"><summary>איך הציון חושב</summary><div class="ledger">
        <p>דטרמיניסטי — אותו corpus תמיד יקבל את אותו ציון. כל קובץ מקבל נקודות לפי דרגת הראיה שלו, בממוצע על כל הקבצים בהיקף; כל עותק כפול מוריד 2 נקודות (עד 15); כל ממצא STOP חוסם את הציון ב-49.</p>
        <table><thead><tr><th>דרגת ראיה</th><th>קבצים</th><th>נק' לקובץ</th><th>סה"כ</th></tr></thead><tbody>
        ${tierRows}${outsideRow}
        <tr><td>ממוצע משוקלל על ${total} קבצים</td><td colspan="2"></td><td class="num">${Number(parts.weighted_base || 0)}</td></tr>
        <tr><td>עונש כפילויות</td><td colspan="2"></td><td class="num">−${Number(parts.duplicate_penalty || 0)}</td></tr>
        <tr><td>תקרת STOP (49)</td><td colspan="2"></td><td>${parts.stop_cap_applied ? 'הופעלה' : (Number(parts.stop_findings || 0) ? 'קיימת, לא חותכת' : '—')}</td></tr>
        <tr class="total"><td>ציון מוכנות</td><td colspan="2"></td><td class="num">${Number(readiness.score || 0)}</td></tr>
        </tbody></table></div></details>`;
    }

    function toggleBoundary(btn) {
      const more = btn.closest('.boundary-line').nextElementSibling;
      more.hidden = !more.hidden;
      btn.setAttribute('aria-expanded', more.hidden ? 'false' : 'true');
    }

    function verdictDelta(data) {
      const delta = data.delta || {};
      if (!delta.has_previous) return '<div class="delta-label">השוואת סריקות</div><p class="hint">סריקה ראשונה — עדיין אין בסיס להשוואה. תקן, סרוק שוב, וראה את השיפור נמדד.</p>';
      const scoreDiff = Number(delta.readiness_score || 0);
      const current = Number((data.readiness_score || {}).score || 0);
      const previous = current - scoreDiff;
      const sign = value => `${value >= 0 ? '+' : ''}${value}`;
      const row = (label, value, goodWhenNegative) => {
        const num = Number(value || 0);
        const cls = num === 0 ? '' : ((num < 0) === goodWhenNegative ? 'up' : 'down');
        return `<span><b class="num ${cls}">${sign(num)}</b> ${label}</span>`;
      };
      return `<div class="delta-label">מול הסריקה הקודמת</div>
        <div class="delta-big num"><span class="${scoreDiff >= 0 ? 'up' : 'down'}">${scoreDiff >= 0 ? '▲' : '▼'} ${sign(scoreDiff)}</span></div>
        <div class="delta-rows num">מוכנות <b>${previous} ← ${current}</b><br>${row('מוכנים', delta.ready, false)} · ${row('לבדיקה', delta.review, true)} · ${row('חסמים', delta.blocked, true)}</div>`;
    }

    function verdictCta(data, meta) {
      const downloads = data.downloads || {};
      if (meta.tone === 'ready' && downloads.audit_pack) {
        return `<a class="cta" style="display:block;background:var(--accent);color:var(--accent-ink);text-decoration:none;font-weight:650" href="${downloadHref(downloads.audit_pack)}">הורד Audit Pack ללקוח</a><div class="cta-note">דוח, SOW ומניפסטים — קובץ אחד, נכתב מקומית</div>`;
      }
      const onclick = meta.tone === 'blocked' ? 'filterNeedsRepair()' : `simpleGroup('${meta.group}')`;
      return `<button class="cta" type="button" onclick="${onclick};document.getElementById('results').scrollIntoView({behavior:'smooth'})">${escapeHtml(meta.action)}</button><div class="cta-note">תקן ← סרוק שוב ← מדוד את הדלתא</div>`;
    }

    function renderVerdict(data) {
      const meta = verdictMeta(data);
      const fixes = recommendedRows(data);
      const project = data.project || {};
      const readiness = data.readiness_score || {};
      const executive = data.executive_summary || {};
      const score = Number(readiness.score || 0);
      const delta = data.delta || {};
      const previous = delta.has_previous ? score - Number(delta.readiness_score || 0) : null;
      const fixesHtml = fixes.length ? `<b style="font-size:12.5px">תיקונים ראשונים</b><ul class="next-fixes">${fixes.map(row => `<li><b>${escapeHtml(row.file)}</b><span>${escapeHtml(row.action || row.finding)}</span>${row.impact ? `<em class="impact-note"><span>למה זה משנה:</span> ${escapeHtml(row.impact)}</em>` : ''}${row.category === 'indexed' ? `<div class="actions"><button class="secondary" type="button" data-file="${escapeHtml(row.file)}" onclick="attachSource(this.dataset.file)">בחר מקור עצמאי</button></div>` : ''}</li>`).join('')}</ul>` : '';
      statusEl.className = `panel verdict ${meta.tone}`;
      statusEl.innerHTML = `<div class="verdict-grid">
        <div>
          <div class="project-line">${escapeHtml(project.client_name || 'לקוח')} · ${escapeHtml(project.project_name || 'RAG Preflight')}</div>
          <span class="vchip">${VERDICT_ICONS[meta.tone]}<span>${escapeHtml(meta.kicker)}</span></span>
          <h2>${escapeHtml(meta.title || '')}</h2>
          <p class="vsub">${escapeHtml(meta.body || '')}</p>
          <p class="executive-summary">${escapeHtml(executive.he || '')}</p>
          <div class="boundary-line">גבול אמון: בודק שרשרת מקורות ושלמות חילוץ — לא נכונות עובדתית. <button type="button" onclick="toggleBoundary(this)" aria-expanded="false">מה זה אומר</button></div>
          <div class="boundary-more" hidden>GO פירושו שכל קובץ בהיקף <b>כשיר לקליטה</b>: נקרא במלואו, ניתן לעקוב אחר מקורו, ואינו מתנגש עם מקור אחר. Anti-Silo אינו שופט אם התוכן נכון — האחריות הזו נשארת אצל בעלי המסמכים, והמשפט הזה מופיע גם בדוח ללקוח.</div>
        </div>
        <div class="readiness-score">
          <div class="scorelab">ציון מוכנות</div>
          <div class="readiness-hero num" aria-label="ציון מוכנות ${score} מתוך 100">${score}<small> / 100</small></div>
          <div class="readiness-band-label">${escapeHtml(readiness.label_he || '')}</div>
          <div class="meter" role="img" aria-label="ציון ${score} מתוך 100. סף GO הוא 85.${previous === null ? '' : ' סריקה קודמת ' + previous + '.'}">
            <div class="fill" style="width:${Math.max(0, Math.min(100, score))}%"></div>
            <div class="tick" style="inset-inline-start:85%"></div>
            ${previous === null ? '' : `<div class="ghost" style="inset-inline-start:${Math.max(0, Math.min(100, previous))}%"></div>`}
          </div>
          <div class="meter-labels"><span style="inset-inline-start:85%">GO ≥ 85</span></div>
          ${scoreLedger(data)}
        </div>
        <div>
          ${verdictDelta(data)}
          ${verdictCta(data, meta)}
          <div class="band-actions"><button class="secondary" type="button" onclick="rescan()">בדיקה חוזרת</button><button class="secondary" type="button" onclick="filterNeedsRepair()">רשימת תיקון</button></div>
          ${fixesHtml}
        </div>
      </div>`;
    }

    function renderCorpus(data) {
      const diagnostics = data.diagnostics || {};
      const counts = diagnostics.counts || {};
      corpusEl.hidden = false;
      corpusEl.innerHTML = `<h2 class="section-title">אבחון corpus</h2><p>${diagnostics.total_files || 0} קבצים נמצאו בתיקייה, ${diagnostics.ingested_files || 0} מהם נכללו בסריקה. כל הספירות נגזרות מהקבצים עצמם (SHA-256).</p><div class="corpus-grid"><div class="metric"><b>${counts.unsupported_files || 0}</b><span>פורמטים לא נתמכים</span></div><div class="metric"><b>${counts.duplicate_files || 0}</b><span>עותקים כפולים</span></div><div class="metric"><b>${counts.extraction_failed || 0}</b><span>כשלי חילוץ</span></div><div class="metric"><b>${counts.extraction_truncated || 0}</b><span>חילוץ חלקי</span></div></div>`;
    }

    function renderRiskRegister(data) {
      const risks = data.risk_register || [];
      const effort = data.effort_estimate || {};
      const rows = risks.slice(0, 8).map(risk => `<tr><td class="num">${escapeHtml(risk.risk_id)}</td><td>${escapeHtml(risk.category)}</td><td class="file-cell">${escapeHtml(risk.file)}</td><td><span class="risk-severity ${escapeHtml(String(risk.severity).toLowerCase())}">${escapeHtml(risk.severity)}</span></td><td>${escapeHtml(risk.recommendation)}</td></tr>`).join('');
      riskEl.hidden = false;
      riskEl.innerHTML = `<div class="risk-header"><div><h2 class="section-title">מרשם סיכונים</h2><p>השאלות שהלקוח ישאל — עם התשובות שלך מוכנות מראש. ניתן לצרף לשיחת היקף או ל-SOW.</p></div><div class="effort-range"><b class="num">${Number(effort.minimum_hours || 0)}-${Number(effort.maximum_hours || 0)}</b><span>שעות לתכנון</span></div></div><div class="table-scroll"><table><thead><tr><th>מזהה</th><th>קטגוריה</th><th>קובץ</th><th>חומרה</th><th>המלצה</th></tr></thead><tbody>${rows || '<tr><td colspan="5">לא נמצאו סיכונים לרישום.</td></tr>'}</tbody></table></div><p class="hint">הערכת השעות מבוססת על מספר הממצאים וחומרתם. יש לאמת מורכבות לפני הצעת מחיר.</p>`;
    }
