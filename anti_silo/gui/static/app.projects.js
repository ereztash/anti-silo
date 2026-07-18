    async function loadProjects() {
      try {
        const data = await api('/api/projects');
        recentProjects = data.projects || [];
        const select = document.getElementById('recent-projects');
        if (!select) return;
        const current = select.value;
        select.innerHTML = '<option value="">פרויקטים אחרונים</option>' + recentProjects.map(project => {
          const suffix = project.scan_count ? ` · ${project.scan_count} בדיקות` : '';
          return `<option value="${escapeHtml(project.id)}">${escapeHtml(project.client_name)} · ${escapeHtml(project.project_name)}${suffix}</option>`;
        }).join('');
        if (recentProjects.some(project => project.id === current)) select.value = current;
      } catch (_) {
        // Project history is optional; scanning remains available without it.
      }
    }

    function selectRecentProject(projectId) {
      const project = recentProjects.find(item => item.id === projectId);
      if (!project) return;
      document.getElementById('client-name').value = project.client_name || '';
      document.getElementById('project-name').value = project.project_name || '';
      document.getElementById('consultant-name').value = project.consultant_name || '';
      document.getElementById('path').value = project.source_root || '';
      const threshold = document.getElementById('go-threshold');
      if (threshold && project.go_threshold) threshold.value = project.go_threshold;
      onboardingEl.hidden = true;
    }

    // Branding: a logo + business name embedded in every exported client report, so
    // the report reads as the consultant's own work, not Anti-Silo's. Persists locally
    // and applies to all future scans; unrelated to the per-report consultant notes.
    async function loadBranding() {
      try {
        const data = await api('/api/branding');
        document.getElementById('branding-business-name').value = data.business_name || '';
        pendingLogoDataUri = data.logo_data_uri || '';
        const preview = document.getElementById('branding-logo-preview');
        if (pendingLogoDataUri) {
          document.getElementById('branding-logo-img').src = pendingLogoDataUri;
          preview.hidden = false;
        } else {
          preview.hidden = true;
        }
      } catch (_) {
        // Branding is optional; the form just stays empty.
      }
    }

    function openBranding() {
      document.getElementById('branding-panel').hidden = false;
      document.getElementById('branding-status').textContent = '';
      loadBranding();
      document.getElementById('branding-panel').scrollIntoView({behavior: 'smooth', block: 'start'});
    }

    function closeBranding() {
      document.getElementById('branding-panel').hidden = true;
    }

    function clearBrandingLogo() {
      pendingLogoDataUri = '';
      document.getElementById('branding-logo-preview').hidden = true;
      document.getElementById('branding-logo-file').value = '';
    }

    function onBrandingLogoSelected(event) {
      const file = event.target.files && event.target.files[0];
      if (!file) return;
      const statusEl = document.getElementById('branding-status');
      if (file.size > 300000) {
        statusEl.textContent = 'הקובץ גדול מדי (מקסימום כ-300KB) — הוא מוטבע בכל דוח שמיוצא.';
        event.target.value = '';
        return;
      }
      statusEl.textContent = '';
      const reader = new FileReader();
      reader.onload = () => {
        pendingLogoDataUri = String(reader.result || '');
        document.getElementById('branding-logo-img').src = pendingLogoDataUri;
        document.getElementById('branding-logo-preview').hidden = false;
      };
      reader.readAsDataURL(file);
    }

    async function saveBranding() {
      const businessName = document.getElementById('branding-business-name').value.trim();
      const statusEl = document.getElementById('branding-status');
      try {
        await api('/api/branding', 'POST', {business_name: businessName, logo_data_uri: pendingLogoDataUri});
        statusEl.textContent = 'נשמר. יופיע בכל דוח שיוצא מעכשיו.';
      } catch (err) {
        statusEl.textContent = err.message || 'השמירה נכשלה.';
      }
    }
