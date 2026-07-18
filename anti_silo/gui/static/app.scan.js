    function startScan(path) {
      onboardingEl.hidden = true;
      document.getElementById('project-panel').hidden = false;
      document.getElementById('scan-panel').hidden = false;
      document.getElementById('path').value = path;
      const projectInput = document.getElementById('project-name');
      if (!projectInput.value.trim()) projectInput.value = path.split(/[\\/]/).filter(Boolean).pop() || 'RAG Preflight';
      // Quick Preflight: a dragged or picked folder runs immediately. Client and
      // project default server-side, so no form-filling is required for a first
      // verdict — names matter only for saving, comparing, or exporting, and the
      // consultant can set them and re-scan.
      scan();
    }

    async function scanDesktop() {
      try { const data = await api('/api/default-desktop', 'POST'); startScan(data.path); }
      catch (err) { statusEl.hidden = false; statusEl.textContent = err.message; }
    }

    async function chooseFolder() {
      try { const data = await api('/api/pick-folder', 'POST'); if (data.path) startScan(data.path); }
      catch (err) { statusEl.hidden = false; statusEl.textContent = err.message; }
    }

    function openBrain() {
      onboardingEl.hidden = true;
      document.getElementById('project-panel').hidden = true;
      document.getElementById('scan-panel').hidden = true;
      statusEl.hidden = true;
      recordEvent('brain_opened');
      loadBrain(true);
    }

    async function attachSource(targetFile) {
      if (!lastPath || !targetFile) return;
      try {
        recordEvent('repair_started', {kind:'attach_source'});
        const selected = await api('/api/pick-source', 'POST');
        if (!selected.path) return;
        await api('/api/repair/source', 'POST', {source_root:lastPath, target_file:targetFile, source_path:selected.path});
        statusEl.className = 'panel'; statusEl.textContent = 'המקור קושר. מריץ בדיקה חוזרת כדי למדוד את שינוי דרגת האמון.';
        await scan();
      } catch (err) { statusEl.className = 'panel'; statusEl.textContent = err.message; }
    }

    async function exitApp() {
      try { await api('/api/shutdown', 'POST'); document.body.innerHTML = '<main><section class="panel"><h2>Anti-Silo נסגר.</h2><p>אפשר לסגור את הלשונית.</p></section></main>'; }
      catch (err) { statusEl.className = 'panel'; statusEl.textContent = err.message; }
    }

    function downloadTodo() {
      const path = lastReport && lastReport.downloads && lastReport.downloads.source_todo;
      if (path) window.location.href = `/download?path=${encodeURIComponent(path)}`;
    }

    function filterNeedsRepair() {
      if (!lastReport) return;
      resultsEl.innerHTML = remediationTable(lastReport.remediation || []);
      recordEvent('repair_started');
    }

    async function scan() {
      const path = document.getElementById('path').value.trim();
      if (!path) return;
      // Names are optional for a quick scan; the server defaults an empty client
      // to "לקוח" and an empty project to the folder name.
      const clientName = document.getElementById('client-name').value.trim();
      const projectName = document.getElementById('project-name').value.trim();
      const consultantName = document.getElementById('consultant-name').value.trim();
      lastPath = path; button.disabled = true; statusEl.className = 'panel empty'; statusEl.textContent = 'בודק מקורות, התאמה ביניהם וחוסרים...';
      try {
        const response = await fetch('/api/scan', {method:'POST', headers:{'Content-Type':'application/json','X-Anti-Silo-CSRF':csrfToken}, body:JSON.stringify({path,project:{client_name:clientName,project_name:projectName,consultant_name:consultantName}})});
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'scan failed');
        render(data);
      } catch (err) { statusEl.className = 'panel'; statusEl.textContent = `הסריקה נכשלה: ${err.message}`; }
      finally { button.disabled = false; }
    }

    function rescan() { if (lastPath) { document.getElementById('path').value = lastPath; scan(); } }

    function setExpertMode(enabled) {
      document.body.classList.toggle('pro', enabled);
      const toggle = document.getElementById('expert-toggle');
      if (toggle) { toggle.setAttribute('aria-pressed', enabled ? 'true' : 'false'); toggle.textContent = enabled ? 'הסתר פרטים למתקדמים' : 'פרטים למתקדמים'; }
    }

    function toggleExpertMode() {
      setExpertMode(!document.body.classList.contains('pro'));
      if (lastReport) {
        summaryEl.hidden = !document.body.classList.contains('pro');
        if (!summaryEl.hidden) summaryEl.innerHTML = ['ready','backed','indexed','synthesis','unsupported','contradiction'].map(key => metric(key,lastReport.counts[key])).join('');
      }
      recordEvent('result_action_taken', {group:'expert_mode'});
    }

    function showTechnicalSummary() {
      if (!lastReport) return;
      summaryEl.hidden = false;
      summaryEl.innerHTML = ['ready','backed','indexed','synthesis','unsupported','contradiction'].map(key => metric(key,lastReport.counts[key])).join('');
      setExpertMode(true);
      recordEvent('result_action_taken', {group:'technical_details'});
    }

    async function discardResults() {
      if (!lastReport || !lastReport.temporary) return;
      await fetch('/api/discard', {method:'POST', headers:{'Content-Type':'application/json','X-Anti-Silo-CSRF':csrfToken}, body:JSON.stringify({staged_vault:lastReport.staged_vault})});
      statusEl.className = 'panel empty'; statusEl.textContent = 'תוצאות זמניות נמחקו.';
    }

    async function watchLastFolder() {
      if (!lastPath) return;
      try {
        await api('/api/watch', 'POST', {path:lastPath});
        if ('Notification' in window && Notification.permission === 'default') Notification.requestPermission();
        statusEl.hidden = false; statusEl.className = 'panel'; statusEl.textContent = 'Anti-Silo יבדוק שינויים כל עוד האפליקציה פתוחה.';
      } catch (err) { statusEl.hidden = false; statusEl.className = 'panel'; statusEl.textContent = err.message; }
    }

    async function refreshWatch(notify = false) {
      try {
        const data = await api('/api/watch');
        const event = data.events && data.events[0];
        if (!event || event.at === latestWatchEvent) return;
        const wasKnown = Boolean(latestWatchEvent); latestWatchEvent = event.at;
        if (notify && wasKnown && 'Notification' in window && Notification.permission === 'granted') new Notification('Anti-Silo', {body:event.message});
      } catch (_) {
        // The local GUI can be closing while the polling request is in flight.
      }
    }
