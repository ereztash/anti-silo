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
