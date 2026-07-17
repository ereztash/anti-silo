    function remediationTable(rows) {
      const severityLabels = {block: 'חסם', review: 'בדיקה', cleanup: 'ניקוי'};
      const htmlRows = rows.map(row => `<tr><td><span class="pill ${escapeHtml(row.severity)}">${escapeHtml(severityLabels[row.severity] || row.severity)}</span></td><td>${escapeHtml(row.file)}</td><td>${escapeHtml(row.finding)}</td><td>${escapeHtml(row.action)}</td></tr>`).join('');
      return `<table><thead><tr><th>עדיפות</th><th>קובץ</th><th>ממצא</th><th>פעולה</th></tr></thead><tbody>${htmlRows || '<tr><td colspan="4">אין פעולות בתור התיקונים.</td></tr>'}</tbody></table>`;
    }

    function verdictMeta(data) {
      const verdict = data.verdict || {};
      if (verdict.status === 'stop') return {tone:'blocked', kicker:verdict.label || 'STOP', title:verdict.title, body:verdict.summary, action:'הצג קבצים חסומים', group:'blocked'};
      if (verdict.status === 'conditional_go') return {tone:'needs', kicker:verdict.label || 'CONDITIONAL GO', title:verdict.title, body:verdict.summary, action:'הצג קבצים לבדיקה', group:'needs'};
      return {tone:'ready', kicker:verdict.label || 'GO', title:verdict.title, body:verdict.summary, action:'הצג קבצים מאושרים', group:'ready'};
    }

    function recommendedRows(data) {
      return (data.remediation || []).slice(0, 3).map(item => {
        const sourceRow = (data.rows || []).find(row => row.file === item.file);
        return {...item, category: sourceRow && sourceRow.category};
      });
    }

    function renderVerdict(data) {
      const meta = verdictMeta(data);
      const fixes = recommendedRows(data);
      const fixesHtml = fixes.length ? `<ul class="next-fixes">${fixes.map(row => `<li><b>${escapeHtml(row.file)}</b><span>${escapeHtml(row.action || row.finding)}</span>${row.category === 'indexed' ? `<div class="actions"><button class="secondary" type="button" data-file="${escapeHtml(row.file)}" onclick="attachSource(this.dataset.file)">בחר מקור עצמאי</button></div>` : ''}</li>`).join('')}</ul>` : '<p class="hint">לא נמצאו פעולות תיקון מיידיות.</p>';
      const project = data.project || {};
      const delta = data.delta || {};
      const deltaHtml = delta.has_previous ? `<div class="delta"><span><b>${Number(delta.ready || 0) >= 0 ? '+' : ''}${delta.ready || 0}</b> מוכנים</span><span><b>${Number(delta.review || 0) >= 0 ? '+' : ''}${delta.review || 0}</b> לבדיקה</span><span><b>${Number(delta.blocked || 0) >= 0 ? '+' : ''}${delta.blocked || 0}</b> חסמים</span></div>` : '';
      statusEl.className = `panel verdict ${meta.tone}`;
      statusEl.innerHTML = `<div class="verdict-grid"><div><div class="project-line">${escapeHtml(project.client_name || 'לקוח')} · ${escapeHtml(project.project_name || 'RAG Preflight')}</div><div class="verdict-kicker">${escapeHtml(meta.kicker)}</div><h2>${escapeHtml(meta.title || '')}</h2><p>${escapeHtml(meta.body || '')}</p>${deltaHtml}<div class="actions"><button type="button" onclick="simpleGroup('${meta.group}')">${escapeHtml(meta.action)}</button><button class="secondary" type="button" onclick="filterNeedsRepair()">הצג רשימת תיקון</button></div><div class="trust-boundary-small">גבול אמון: Anti-Silo בודק שרשרת מקורות ושלמות חילוץ. הוא לא מוכיח שהטקסט נכון עובדתית או מקצועית.</div></div><div><b>תיקונים ראשונים</b>${fixesHtml}</div></div>`;
    }

    function renderCorpus(data) {
      const diagnostics = data.diagnostics || {};
      const counts = diagnostics.counts || {};
      corpusEl.hidden = false;
      corpusEl.innerHTML = `<h2 class="section-title">אבחון corpus</h2><p>${diagnostics.total_files || 0} קבצים נמצאו בתיקייה, ${diagnostics.ingested_files || 0} מהם נכללו בסריקה.</p><div class="corpus-grid"><div class="metric"><b>${counts.unsupported_files || 0}</b><span>פורמטים לא נתמכים</span></div><div class="metric"><b>${counts.duplicate_files || 0}</b><span>עותקים כפולים</span></div><div class="metric"><b>${counts.extraction_failed || 0}</b><span>כשלי חילוץ</span></div><div class="metric"><b>${counts.extraction_truncated || 0}</b><span>חילוץ חלקי</span></div></div>`;
    }
