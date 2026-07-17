    const labels = {
      ready: 'מוכן לשימוש', backed: 'מגובה, דורש אימות נוסף', indexed: 'נסרק, טרם אומת',
      synthesis: 'סיכום שצריך השלמת מקורות', unsupported: 'חסר אסמכתא', contradiction: 'סתירה או חסם אמון'
    };
    const downloadNames = {
      html_report: 'שמור דוח HTML', allowed_sources: 'רשימת מקורות מותרים', source_todo: 'תבנית להשלמת מקורות',
      pulse_markdown: 'דוח טכני', manifest: 'מניפסט מקור', audit_pack: 'הורד Audit Pack',
      preflight_summary: 'סיכום Preflight JSON', remediation_queue: 'תור תיקונים CSV', client_manifest: 'מניפסט לקוח'
    };
    const statusEl = document.getElementById('status');
    const summaryEl = document.getElementById('summary');
    const simpleSummaryEl = document.getElementById('simple-summary');
    const resultsEl = document.getElementById('results');
    const downloadsEl = document.getElementById('downloads');
    const corpusEl = document.getElementById('corpus');
    const wizardEl = document.getElementById('wizard');
    const brainEl = document.getElementById('brain');
    const dropzone = document.getElementById('dropzone');
    const button = document.getElementById('scan');
    const onboardingEl = document.getElementById('onboarding');
    const csrfToken = '__CSRF_TOKEN__';
    let lastReport = null;
    let lastPath = '';
    let latestWatchEvent = '';
    let recentProjects = [];
    const initialView = '__INITIAL_VIEW__';
    const initialPath = __INITIAL_PATH_JSON__;

    function metric(key, value) {
      return `<div class="metric ${key}"><b>${value || 0}</b><span>${labels[key]}</span></div>`;
    }
