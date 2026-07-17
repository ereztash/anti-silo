    const labels = {
      ready: 'מוכן לשימוש',
      backed: 'מגובה, דורש אימות נוסף',
      indexed: 'נסרק, טרם אומת',
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
    const simpleSummaryEl = document.getElementById('simple-summary');
    const resultsEl = document.getElementById('results');
    const downloadsEl = document.getElementById('downloads');
    const wizardEl = document.getElementById('wizard');
    const brainEl = document.getElementById('brain');
    const dropzone = document.getElementById('dropzone');
    const button = document.getElementById('scan');
    const onboardingEl = document.getElementById('onboarding');
    const csrfToken = '__CSRF_TOKEN__';
    let lastReport = null;
    let lastPath = '';
    let latestWatchEvent = '';
    const initialView = '__INITIAL_VIEW__';
    const initialPath = __INITIAL_PATH_JSON__;

    function metric(key, value) {
      return `<div class="metric ${key}"><b>${value || 0}</b><span>${labels[key]}</span></div>`;
    }

    function table(rows) {
      const htmlRows = rows.map(row => `
        <tr>
          <td><span class="pill ${escapeHtml(row.category)}">${escapeHtml(row.status)}</span></td>
          <td>${escapeHtml(row.file)}</td>
          <td>${escapeHtml(row.action || row.explanation)}${row.category === 'indexed' ? `<div class="actions"><button class="secondary" type="button" data-file="${escapeHtml(row.file)}" onclick="attachSource(this.dataset.file)">בחר מקור עצמאי</button></div>` : ''}</td>
          <td class="technical">${escapeHtml(row.technical_tier || '-')}</td>
          <td class="technical">${escapeHtml(row.technical_reason || '-')}</td>
          <td class="technical">${escapeHtml(row.needs || '-')}</td>
        </tr>`).join('');
      return `<table><thead><tr><th>מצב</th><th>קובץ</th><th>מה לעשות</th><th class="technical">Tier</th><th class="technical">Reason</th><th class="technical">Needs</th></tr></thead><tbody>${htmlRows}</tbody></table>`;
    }

    function simpleGroup(group) {
      if (!lastReport) return;
      const groups = {
        ready: ['ready'],
        needs: ['backed', 'indexed', 'synthesis'],
        blocked: ['unsupported', 'contradiction']
      };
      resultsEl.hidden = false;
      resultsEl.innerHTML = table(lastReport.rows.filter(row => groups[group].includes(row.category)));
      recordEvent('result_action_taken', {group});
    }

    function renderSimpleSummary(data) {
      const trusted = data.counts.ready || 0;
      const needs = (data.counts.backed || 0) + (data.counts.indexed || 0) + (data.counts.synthesis || 0);
      const blocked = (data.counts.unsupported || 0) + (data.counts.contradiction || 0);
      simpleSummaryEl.hidden = false;
      simpleSummaryEl.innerHTML = `
        <button class="simple-card ready" type="button" onclick="simpleGroup('ready')"><b>${trusted}</b>עברו את מדיניות המקורות</button>
        <button class="simple-card needs" type="button" onclick="simpleGroup('needs')"><b>${needs}</b>מומלץ להוסיף מקורות</button>
        <button class="simple-card blocked" type="button" onclick="simpleGroup('blocked')"><b>${blocked}</b>לא מומלץ להסתמך</button>`;
    }

    function render(data) {
      lastReport = data;
      statusEl.className = 'panel';
      const trusted = data.counts.ready || 0;
      const needs = (data.counts.backed || 0) + (data.counts.indexed || 0) + (data.counts.synthesis || 0);
      const blocked = (data.counts.unsupported || 0) + (data.counts.contradiction || 0);
      const headline = blocked ? 'יש קבצים שלא מומלץ להסתמך עליהם כרגע.' : needs ? 'יש קבצים שכדאי לבדוק לפני שמסתמכים עליהם.' : 'כל הקבצים עברו את מדיניות המקורות שנבחרה.';
      const modeLabel = data.input_mode === 'structured_vault' ? 'זוהה מאגר עם קשרי מקור קיימים.' : 'זוהתה תיקיית מסמכים רגילה.';
      statusEl.innerHTML = `<b>${headline}</b><br><span class="hint">${modeLabel} נסרקו ${data.files} קבצים. Anti-Silo בודק מקורות ושלמות חילוץ, לא אמת מקצועית או עובדתית.</span>`;
      summaryEl.hidden = true;
      renderSimpleSummary(data);

      const links = Object.entries(data.downloads || {}).map(([name, path]) => {
        return `<a href="/download?path=${encodeURIComponent(path)}">${downloadNames[name] || name}</a>`;
      }).join('');
      downloadsEl.hidden = false;
      downloadsEl.innerHTML = `<b>ייצוא:</b><br>${links || 'אין קבצי ייצוא זמינים.'}<div class="hint">אפשר לפתוח את דוח ה-HTML ולשמור PDF דרך Print / Save as PDF בדפדפן.</div>`;
      downloadsEl.innerHTML += `<div class="actions">
        <button class="secondary" type="button" onclick="showTechnicalSummary()">הצג פרטים למתקדמים</button>
        <button class="secondary" type="button" onclick="rescan()">בדיקה חוזרת</button>
        <button class="secondary" type="button" onclick="discardResults()">מחק תוצאות זמניות</button>
        <button class="secondary" type="button" onclick="watchLastFolder()">עקוב אחרי התיקייה הזו</button>
      </div>`;

      const needsRepair = needs + blocked;
      wizardEl.hidden = needsRepair === 0;
      if (needsRepair > 0) {
        wizardEl.innerHTML = `
          <b>הפעולה הבאה</b>
          <p class="hint">נמצאו ${needsRepair} פריטים שכדאי לבדוק לפני שמסתמכים עליהם.</p>
          <div class="actions">
            ${data.repair_todo_count > 0 ? '<button class="secondary" type="button" onclick="downloadTodo()">צור תבנית להשלמת מקורות</button>' : ''}
            <button class="secondary" type="button" onclick="filterNeedsRepair()">הצג רק מה שדורש תיקון</button>
          </div>
          ${data.counts.indexed ? '<p class="hint">לפריט שטרם אומת אפשר לבחור קובץ מקור עצמאי ישירות בטבלה.</p>' : ''}`;
      }

      resultsEl.hidden = false;
      resultsEl.innerHTML = table(data.rows);
      loadBrain();
    }

    function startScan(path) {
      onboardingEl.hidden = true;
      document.getElementById('scan-panel').hidden = true;
      document.getElementById('path').value = path;
      scan();
    }

    async function scanDesktop() {
      try {
        const data = await api('/api/default-desktop', 'POST');
        startScan(data.path);
      } catch (err) {
        statusEl.hidden = false;
        statusEl.textContent = err.message;
      }
    }

    async function chooseFolder() {
      try {
        const data = await api('/api/pick-folder', 'POST');
        if (data.path) startScan(data.path);
      } catch (err) {
        statusEl.hidden = false;
        statusEl.textContent = err.message;
      }
    }

    function openBrain() {
      onboardingEl.hidden = true;
      document.getElementById('scan-panel').hidden = true;
      statusEl.hidden = true;
      recordEvent('brain_opened');
      loadBrain(true);
    }

    async function attachSource(targetFile) {
      if (!lastPath || !targetFile) return;
      try {
        recordEvent('repair_started', {kind: 'attach_source'});
        const selected = await api('/api/pick-source', 'POST');
        if (!selected.path) return;
        await api('/api/repair/source', 'POST', {source_root: lastPath, target_file: targetFile, source_path: selected.path});
        statusEl.className = 'panel';
        statusEl.textContent = 'המקור קושר. מריץ בדיקה חוזרת כדי למדוד את שינוי דרגת האמון.';
        await scan();
      } catch (err) {
        statusEl.className = 'panel';
        statusEl.textContent = err.message;
      }
    }

    async function exitApp() {
      try {
        await api('/api/shutdown', 'POST');
        document.body.innerHTML = '<main><section class="panel"><h2>Anti-Silo נסגר.</h2><p>אפשר לסגור את הלשונית.</p></section></main>';
      } catch (err) {
        statusEl.className = 'panel';
        statusEl.textContent = err.message;
      }
    }

    function downloadTodo() {
      const path = lastReport && lastReport.downloads && lastReport.downloads.source_todo;
      if (path) window.location.href = `/download?path=${encodeURIComponent(path)}`;
    }

    function filterNeedsRepair() {
      if (!lastReport) return;
      resultsEl.innerHTML = table(lastReport.rows.filter(row => row.category !== 'ready'));
      recordEvent('repair_started');
    }

    async function scan() {
      const path = document.getElementById('path').value.trim();
      if (!path) return;
      lastPath = path;
      button.disabled = true;
      statusEl.className = 'panel empty';
      statusEl.textContent = 'בודק מקורות, התאמה ביניהם וחוסרים...';
      try {
        const response = await fetch('/api/scan', {
          method: 'POST',
          headers: {'Content-Type': 'application/json', 'X-Anti-Silo-CSRF': csrfToken},
          body: JSON.stringify({path})
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'scan failed');
        render(data);
      } catch (err) {
        statusEl.className = 'panel';
        statusEl.textContent = `הסריקה נכשלה: ${err.message}`;
      } finally {
        button.disabled = false;
      }
    }
    function rescan() {
      if (lastPath) {
        document.getElementById('path').value = lastPath;
        scan();
      }
    }
    function showTechnicalSummary() {
      if (!lastReport) return;
      summaryEl.hidden = false;
      summaryEl.innerHTML = ['ready','backed','indexed','synthesis','unsupported','contradiction'].map(k => metric(k, lastReport.counts[k])).join('');
      document.body.classList.toggle('pro');
      recordEvent('result_action_taken', {group: 'technical_details'});
    }
    async function discardResults() {
      if (!lastReport || !lastReport.temporary) return;
      await fetch('/api/discard', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-Anti-Silo-CSRF': csrfToken},
        body: JSON.stringify({staged_vault: lastReport.staged_vault})
      });
      statusEl.className = 'panel empty';
      statusEl.textContent = 'תוצאות זמניות נמחקו.';
    }

    async function watchLastFolder() {
      if (!lastPath) return;
      try {
        await api('/api/watch', 'POST', {path: lastPath});
        if ('Notification' in window && Notification.permission === 'default') Notification.requestPermission();
        statusEl.hidden = false;
        statusEl.className = 'panel';
        statusEl.textContent = 'Anti-Silo יבדוק שינויים כל עוד האפליקציה פתוחה.';
      } catch (err) {
        statusEl.hidden = false;
        statusEl.className = 'panel';
        statusEl.textContent = err.message;
      }
    }

    async function refreshWatch(notify = false) {
      try {
        const data = await api('/api/watch');
        const event = data.events && data.events[0];
        if (!event || event.at === latestWatchEvent) return;
        const wasKnown = Boolean(latestWatchEvent);
        latestWatchEvent = event.at;
        if (notify && wasKnown && 'Notification' in window && Notification.permission === 'granted') {
          new Notification('Anti-Silo', {body: event.message});
        }
      } catch (_) {
        // The local GUI can be closing while the polling request is in flight.
      }
    }

    async function api(path, method = 'GET', body = null) {
      const response = await fetch(path, {
        method,
        headers: method === 'GET' ? {} : {'Content-Type': 'application/json', 'X-Anti-Silo-CSRF': csrfToken},
        body: body ? JSON.stringify(body) : null
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'request failed');
      return data;
    }

    function recordEvent(event, properties = {}) {
      api('/api/event', 'POST', {event, properties}).catch(() => {});
    }

    function escapeHtml(value) {
      return String(value ?? '').replace(/[&<>'"]/g, char => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
      })[char]);
    }

    function brainEntry(entry) {
      const decisionLabels = {draft_requires_sources: 'טיוטה: יש לצרף מקור', needs_source_review: 'ממתינה לבדיקת המקורות', supported: 'מגובה במקורות שעברו את המדיניות'};
      const detail = entry.kind === 'source' ? entry.trust_status || entry.trust_tier : entry.kind === 'decision' ? decisionLabels[entry.decision_status] || 'ממתינה לבדיקה' : entry.body;
      return `<li><b>${escapeHtml(entry.title)}</b><br><span class="hint">${escapeHtml(entry.kind)}${detail ? ` | ${escapeHtml(detail)}` : ''}</span></li>`;
    }

    async function loadBrain(simpleFirst = false) {
      try {
        const data = await api('/api/brain');
        brainEl.hidden = false;
        if (simpleFirst && data.entries.length === 0) {
          brainEl.innerHTML = `
            <div class="welcome">
              <h2>על מה אתה חושב עכשיו?</h2>
              <div class="actions">
                <button type="button" onclick="openBrainComposer('note')">רעיון או מחשבה</button>
                <button class="secondary" type="button" onclick="openBrainComposer('question')">שאלה שאני רוצה לבדוק</button>
                <button class="secondary" type="button" onclick="openBrainComposer('decision')">החלטה שאני צריך לקבל</button>
              </div>
            </div>`;
          return;
        }
        const counts = data.counts;
        const sources = data.entries.filter(entry => entry.kind === 'source');
        const sourceOptions = sources.map(entry => `<option value="${escapeHtml(entry.id)}">${escapeHtml(entry.title)} (${escapeHtml(entry.trust_status || entry.trust_tier)})</option>`).join('');
        const queue = data.review_queue.length
          ? `<ul class="brain-list">${data.review_queue.map(item => `<li><b>${escapeHtml(item.title)}</b><br><span class="hint">${escapeHtml(item.reason)}</span></li>`).join('')}</ul>`
          : '<p class="hint">אין כרגע פריטים שמחכים לבדיקה.</p>';
        brainEl.innerHTML = `
          <b>המוח השני שלך</b>
          <p class="hint">הידע נשמר מקומית ב-${escapeHtml(data.root)}. המקורות שומרים את דרגת האמון שבה נסרקו; יצירת הערה או החלטה אינה משנה אותה.</p>
          <div class="summary">${metric('ready', counts.trusted_sources)}${metric('indexed', counts.sources - counts.trusted_sources)}${metric('backed', counts.notes)}${metric('synthesis', counts.decisions)}${metric('unsupported', counts.questions)}${metric('contradiction', data.review_queue.length)}</div>
          <div class="actions"><button class="secondary" type="button" onclick="importLastScan()">הוסף את תוצאות הסריקה למוח השני</button></div>
          <div class="brain-grid">
            <div>
              <label for="brain-kind">פריט חדש</label>
              <select id="brain-kind"><option value="note">הערה</option><option value="decision">החלטה</option><option value="question">שאלה</option><option value="task">משימה</option></select>
              <input id="brain-title" placeholder="כותרת" style="margin-top:8px; direction:rtl; text-align:right;">
              <textarea id="brain-body" placeholder="מה חשוב לזכור או להחליט?"></textarea>
              <label for="brain-sources" class="hint">מקורות קשורים</label>
              <select id="brain-sources" multiple size="4">${sourceOptions}</select>
              <p class="hint">החלטה ללא מקור נשמרת כטיוטה לבדיקה. מקור שאינו מאומת נשאר מסומן כך גם כאן.</p>
              <div class="actions"><button type="button" onclick="addBrainEntry()">שמור במוח השני</button></div>
            </div>
            <div><b>תור בדיקה</b>${queue}</div>
          </div>
          <div><b>פריטים אחרונים</b><ul class="brain-list">${data.entries.slice(0, 8).map(brainEntry).join('') || '<li class="hint">עדיין אין פריטים.</li>'}</ul></div>`;
      } catch (err) {
        brainEl.hidden = false;
        brainEl.innerHTML = `<b>המוח השני לא נטען.</b><p class="hint">${err.message}</p>`;
      }
    }

    function openBrainComposer(kind) {
      loadBrain().then(() => {
        const select = document.getElementById('brain-kind');
        if (select) select.value = kind;
        const title = document.getElementById('brain-title');
        if (title) title.focus();
      });
    }

    async function importLastScan() {
      try {
        const data = await api('/api/brain/import-last-scan', 'POST');
        statusEl.className = 'panel';
        statusEl.textContent = `נוספו ${data.added} מקורות למוח השני.`;
        loadBrain();
      } catch (err) {
        statusEl.className = 'panel';
        statusEl.textContent = err.message;
      }
    }

    async function addBrainEntry() {
      const kind = document.getElementById('brain-kind').value;
      const title = document.getElementById('brain-title').value.trim();
      const body = document.getElementById('brain-body').value.trim();
      const sourceIds = Array.from(document.getElementById('brain-sources').selectedOptions).map(option => option.value);
      if (!title) return;
      try {
        await api('/api/brain/entries', 'POST', {kind, title, body, source_ids: sourceIds});
        loadBrain();
      } catch (err) {
        statusEl.className = 'panel';
        statusEl.textContent = err.message;
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
    if (initialPath) {
      startScan(initialPath);
    } else if (initialView === 'brain') {
      onboardingEl.hidden = true;
      document.getElementById('scan-panel').hidden = true;
      statusEl.hidden = true;
      loadBrain(true);
    }
    refreshWatch();
    window.setInterval(() => refreshWatch(true), 15000);
  
