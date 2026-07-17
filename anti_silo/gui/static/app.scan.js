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

