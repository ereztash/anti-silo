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
  
