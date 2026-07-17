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

