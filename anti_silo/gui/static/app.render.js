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

