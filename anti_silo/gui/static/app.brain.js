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
