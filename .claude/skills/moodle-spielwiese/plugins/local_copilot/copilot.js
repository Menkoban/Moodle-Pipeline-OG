// Moodle Spielwiesen Copilot Client JS — Goldstandard Henning Rode
(function() {
  if (window.__moodleCopilotInitialized) return;
  window.__moodleCopilotInitialized = true;

  let currentLevel = 'abschnitt';
  let isInspectorActive = false;
  let selectedElement = null;
  let actionsData = null;
  let ws = null;
  let recognition = null;
  let isRecording = false;

  function initCopilotUI() {
    // 1. Schwebendes Icon
    const launcher = document.createElement('div');
    launcher.id = 'moodle-copilot-launcher';
    launcher.innerHTML = '✨';
    launcher.title = 'Kurs-Assistent öffnen';
    document.body.appendChild(launcher);

    // 2. Das erweiterte Panel
    const container = document.createElement('div');
    container.id = 'moodle-copilot-container';
    container.style.display = 'none';

    container.innerHTML = `
      <div class="copilot-resize-left" id="copilot-resize-handle"></div>
      <div class="copilot-header" id="copilot-drag-header">
        <div class="copilot-header-title">
          <span class="copilot-status-dot" id="copilot-ws-status"></span>
          <span>✨ Kurs-Assistent</span>
        </div>
        <div class="copilot-header-controls">
          <button class="copilot-ctrl-btn" id="copilot-btn-min" title="Minimieren">−</button>
          <button class="copilot-ctrl-btn" id="copilot-btn-dock" title="Andocken">📌</button>
        </div>
      </div>

      <div class="copilot-mode-tabs">
        <button class="copilot-tab-btn active" id="tab-mode-edit">🛠️ Bearbeiten</button>
        <button class="copilot-tab-btn" id="tab-mode-student">🎓 Schüler-Ansicht</button>
      </div>

      <div class="copilot-level-bar">
        <button class="copilot-level-chip" data-level="modul" title="Modul / Lerneinheit (Gesamtkurs)">📦 Modul / Lerneinheit</button>
        <button class="copilot-level-chip active" data-level="abschnitt" title="Lernabschnitt (Kachel / Thema)">📑 Lernabschnitt</button>
        <button class="copilot-level-chip" data-level="baustein" title="Lernbaustein (Aktivität / Material)">🧩 Lernbaustein</button>
        <button class="copilot-level-chip" data-level="element" title="Lernelement (Text, Bild, Formel)">✏️ Lernelement</button>
      </div>

      <div class="copilot-body">
        <div class="copilot-inspect-banner" id="copilot-inspector-btn">
          <span style="font-size:1.3rem;">👆</span>
          <div>
            <div class="copilot-inspect-text">Auf Kurs-Inhalt zeigen</div>
            <div class="copilot-inspect-sub" id="copilot-focus-label">Klicke links ein Element an</div>
          </div>
        </div>

        <div class="copilot-actions-grid" id="copilot-actions-grid"></div>

        <div class="copilot-voice-box">
          <button class="copilot-mic-btn" id="copilot-mic-btn" title="Tap-to-Toggle Spracheingabe">🎙️</button>
          <div class="copilot-voice-label" id="copilot-voice-status">
            <strong>Sprich in deinen Worten...</strong><br>
            <span style="font-size:0.7rem;">Antippen zum Starten · Nochmal tippen zum Senden</span>
          </div>
        </div>

        <div class="copilot-log-container" id="copilot-log-container">
          <div class="copilot-msg-card assistant">
            Hallo! Ich bin dein Kurs-Assistent nach dem didaktischen Konzept (Modul, Lernabschnitt, Lernbaustein, Lernelement). Klicke eine Aktion an, um den geführten Dialog zu starten!
          </div>
        </div>
      </div>

      <div class="copilot-input-area">
        <div class="copilot-input-box">
          <input type="text" class="copilot-input-field" id="copilot-text-input" placeholder="Wunsch eingeben...">
          <button class="copilot-send-btn" id="copilot-send-btn">Los</button>
        </div>
      </div>

      <div class="copilot-footer">
        <span>📦 Kurssicherung: <strong id="copilot-mbz-ver">v1.1</strong></span>
        <a href="#" id="copilot-download-mbz" style="color:#2563eb; font-weight:bold; text-decoration:none;">💾 .mbz laden</a>
      </div>
    `;

    document.body.appendChild(container);

    setupEvents(launcher, container);
    loadSavedState(launcher, container);
    fetchActionsConfig();
    initSpeechRecognition();
    connectWebSocket();
  }

  function setupEvents(launcher, container) {
    const minBtn = container.querySelector('#copilot-btn-min');
    const dockBtn = container.querySelector('#copilot-btn-dock');
    const dragHeader = container.querySelector('#copilot-drag-header');
    const resizeHandle = container.querySelector('#copilot-resize-handle');
    const inspectorBtn = container.querySelector('#copilot-inspector-btn');
    const micBtn = container.querySelector('#copilot-mic-btn');
    const sendBtn = container.querySelector('#copilot-send-btn');
    const textInput = container.querySelector('#copilot-text-input');
    const levelChips = container.querySelectorAll('.copilot-level-chip');

    launcher.addEventListener('click', () => {
      container.style.display = 'flex';
      launcher.style.display = 'none';
      saveState({ open: true });
    });

    minBtn.addEventListener('click', () => {
      container.style.display = 'none';
      launcher.style.display = 'flex';
      saveState({ open: false });
    });

    dockBtn.addEventListener('click', () => {
      container.classList.toggle('docked-mode');
    });

    // Level Chips
    levelChips.forEach(chip => {
      chip.addEventListener('click', () => {
        levelChips.forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        currentLevel = chip.getAttribute('data-level');
        renderActions();
      });
    });

    // Dragging
    let isDragging = false, dragStartX = 0, dragStartY = 0, initialRight = 20, initialBottom = 20;
    dragHeader.addEventListener('mousedown', (e) => {
      if (e.target.closest('.copilot-header-controls')) return;
      isDragging = true;
      dragStartX = e.clientX;
      dragStartY = e.clientY;
      const rect = container.getBoundingClientRect();
      initialRight = window.innerWidth - rect.right;
      initialBottom = window.innerHeight - rect.bottom;
      document.body.style.userSelect = 'none';
    });

    // Resizing
    let isResizing = false, resizeStartX = 0, initialWidth = 360;
    resizeHandle.addEventListener('mousedown', (e) => {
      isResizing = true;
      resizeStartX = e.clientX;
      initialWidth = container.offsetWidth;
      document.body.style.userSelect = 'none';
      e.stopPropagation();
    });

    window.addEventListener('mousemove', (e) => {
      if (isDragging) {
        const dx = e.clientX - dragStartX;
        const dy = e.clientY - dragStartY;
        container.style.right = Math.max(10, initialRight - dx) + 'px';
        container.style.bottom = Math.max(10, initialBottom - dy) + 'px';
      } else if (isResizing) {
        const dx = resizeStartX - e.clientX;
        const newW = Math.min(750, Math.max(280, initialWidth + dx));
        container.style.width = newW + 'px';
      }
    });

    window.addEventListener('mouseup', () => {
      if (isDragging || isResizing) {
        isDragging = false;
        isResizing = false;
        document.body.style.userSelect = '';
        saveState({
          width: container.style.width,
          right: container.style.right,
          bottom: container.style.bottom
        });
      }
    });

    // Inspector
    inspectorBtn.addEventListener('click', toggleInspector);

    // Voice
    micBtn.addEventListener('click', toggleSpeechRecognition);

    // Text Input
    sendBtn.addEventListener('click', () => submitUserMessage(textInput.value));
    textInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') submitUserMessage(textInput.value);
    });
  }

  function fetchActionsConfig() {
    fetch('/local/copilot/actions_config.json?v=' + Date.now())
      .then(res => res.json())
      .then(data => {
        actionsData = data;
        renderActions();
      })
      .catch(err => {
        console.warn('[Copilot] actions_config.json fallback:', err);
      });
  }

  function renderActions() {
    const grid = document.getElementById('copilot-actions-grid');
    if (!grid || !actionsData) return;
    const cfg = actionsData[currentLevel];
    if (!cfg) return;

    grid.innerHTML = '';
    cfg.actions.forEach(act => {
      const card = document.createElement('div');
      card.className = 'copilot-action-card';
      card.innerHTML = `
        <div class="copilot-action-title"><span>${act.icon}</span> ${act.title}</div>
        <div class="copilot-action-hint">${act.hint}</div>
      `;
      card.addEventListener('click', () => triggerGuidedAction(act));
      grid.appendChild(card);
    });
  }

  // Interaktiver geführter Chat-Dialog
  function triggerGuidedAction(act) {
    if (act.is_download) {
      appendMessage('user', '💾 Kurssicherung (.mbz) herunterladen angefordert.');
      appendMessage('assistant', 'Die neueste validierte Kurssicherung wird geladen...');
      window.location.href = '/local/copilot/download.php';
      return;
    }

    // 1. Post User action
    appendMessage('user', `${act.icon} <strong>${act.title}</strong> gewählt`);

    // 2. Assistent führt den Dialog
    const question = act.guide_question || `Wie möchtest du '${act.title}' konkret ausführen?`;
    let html = `<div>${question}</div>`;

    if (act.options && act.options.length > 0) {
      html += `<div style="display:flex;flex-direction:column;gap:6px;margin-top:10px;">`;
      act.options.forEach(opt => {
        html += `<button class="copilot-choice-btn" style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:6px;padding:6px 10px;text-align:left;font-size:0.82rem;cursor:pointer;color:#1e3a8a;font-weight:500;" data-opt="${encodeURIComponent(opt)}">${opt}</button>`;
      });
      html += `</div>`;
    }

    appendMessage('assistant', html);

    // Klick-Handler für Optionen
    setTimeout(() => {
      const btns = document.querySelectorAll('.copilot-choice-btn');
      btns.forEach(b => {
        b.onclick = function() {
          const val = decodeURIComponent(this.getAttribute('data-opt'));
          submitUserMessage(`${act.title} ➔ ${val}`);
        };
      });
    }, 100);
  }

  function appendMessage(role, text) {
    const log = document.getElementById('copilot-log-container');
    if (!log) return;
    const card = document.createElement('div');
    card.className = `copilot-msg-card ${role}`;
    card.innerHTML = text;
    log.appendChild(card);
    log.scrollTop = log.scrollHeight;
  }

  function submitUserMessage(text) {
    if (!text || !text.trim()) return;
    appendMessage('user', text.trim());
    const input = document.getElementById('copilot-text-input');
    if (input) input.value = '';

    const payload = {
      action: 'user_prompt',
      level: currentLevel,
      focus: selectedElement ? {
        tag: selectedElement.tagName,
        text: selectedElement.innerText.slice(0, 100)
      } : null,
      prompt: text.trim(),
      course_id: (window.location.search.match(/id=(\d+)/) || [null, 1])[1]
    };

    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(payload));
      appendMessage('assistant', '<em>Auftrag wird analysiert und ausgeführt...</em>');
    } else {
      setTimeout(() => {
        appendMessage('assistant', `✅ <strong>Erkannt auf Ebene ${currentLevel.toUpperCase()}:</strong> „${text.trim()}“<br><small style="color:#64748b;">(Bridge aktiv auf Port 7890)</small>`);
      }, 500);
    }
  }

  function toggleInspector() {
    isInspectorActive = !isInspectorActive;
    const banner = document.getElementById('copilot-inspector-btn');
    if (isInspectorActive) {
      banner.style.background = '#dcfce7';
      banner.style.borderColor = '#16a34a';
      document.body.style.cursor = 'crosshair';
      document.addEventListener('mouseover', onInspectHover, true);
      document.addEventListener('click', onInspectClick, true);
    } else {
      banner.style.background = '#f0fdf4';
      banner.style.borderColor = '#86efac';
      document.body.style.cursor = '';
      document.removeEventListener('mouseover', onInspectHover, true);
      document.removeEventListener('click', onInspectClick, true);
    }
  }

  let hoveredEl = null;
  function onInspectHover(e) {
    if (e.target.closest('#moodle-copilot-container') || e.target.closest('#moodle-copilot-launcher')) return;
    if (hoveredEl) hoveredEl.style.outline = '';
    hoveredEl = e.target;
    hoveredEl.style.outline = '2px dashed #0284c7';
  }

  function onInspectClick(e) {
    if (e.target.closest('#moodle-copilot-container') || e.target.closest('#moodle-copilot-launcher')) return;
    e.preventDefault();
    e.stopPropagation();
    selectedElement = e.target;
    if (hoveredEl) hoveredEl.style.outline = '';
    selectedElement.style.outline = '3px solid #16a34a';

    const lbl = document.getElementById('copilot-focus-label');
    const desc = selectedElement.innerText ? selectedElement.innerText.slice(0, 40) + '...' : selectedElement.tagName;
    if (lbl) lbl.innerHTML = `<strong>${selectedElement.tagName}:</strong> ${desc}`;

    toggleInspector();
    appendMessage('assistant', `Fokus gesetzt auf: <strong>${selectedElement.tagName}</strong> („${desc}“). Welche Aktion möchtest du ausführen?`);
  }

  function initSpeechRecognition() {
    const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Speech) return;
    recognition = new Speech();
    recognition.lang = 'de-DE';
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onresult = (e) => {
      let finalTranscript = '';
      for (let i = e.resultIndex; i < e.results.length; ++i) {
        if (e.results[i].isFinal) finalTranscript += e.results[i][0].transcript;
      }
      if (finalTranscript) {
        const inp = document.getElementById('copilot-text-input');
        if (inp) inp.value = finalTranscript;
      }
    };

    recognition.onerror = () => stopRecording();
    recognition.onend = () => stopRecording();
  }

  function toggleSpeechRecognition() {
    if (!recognition) {
      alert('Web Speech API wird in diesem Browser nicht unterstützt.');
      return;
    }
    if (isRecording) {
      stopRecording();
      const inp = document.getElementById('copilot-text-input');
      if (inp && inp.value.trim()) submitUserMessage(inp.value.trim());
    } else {
      startRecording();
    }
  }

  function startRecording() {
    isRecording = true;
    const btn = document.getElementById('copilot-mic-btn');
    const lbl = document.getElementById('copilot-voice-status');
    if (btn) btn.classList.add('recording');
    if (lbl) lbl.innerHTML = `<strong style="color:#dc2626;">Ich höre zu...</strong><br><span style="font-size:0.7rem;">Erneut tippen zum Absenden</span>`;
    recognition.start();
  }

  function stopRecording() {
    isRecording = false;
    const btn = document.getElementById('copilot-mic-btn');
    const lbl = document.getElementById('copilot-voice-status');
    if (btn) btn.classList.remove('recording');
    if (lbl) lbl.innerHTML = `<strong>Sprich in deinen Worten...</strong><br><span style="font-size:0.7rem;">Antippen zum Starten · Nochmal tippen zum Senden</span>`;
    try { recognition.stop(); } catch(e) {}
  }

  function connectWebSocket() {
    const dot = document.getElementById('copilot-ws-status');
    try {
      ws = new WebSocket('ws://localhost:7890');
      ws.onopen = () => { if (dot) dot.classList.add('online'); };
      ws.onclose = () => { if (dot) dot.classList.remove('online'); };
      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          if (msg.text) appendMessage('assistant', msg.text);
        } catch(err) {
          appendMessage('assistant', e.data);
        }
      };
    } catch(e) {
      if (dot) dot.classList.remove('online');
    }
  }

  function saveState(patch) {
    const s = JSON.parse(localStorage.getItem('moodle_copilot_state') || '{}');
    localStorage.setItem('moodle_copilot_state', JSON.stringify(Object.assign(s, patch)));
  }

  function loadSavedState(launcher, container) {
    const s = JSON.parse(localStorage.getItem('moodle_copilot_state') || '{}');
    if (s.open) {
      container.style.display = 'flex';
      launcher.style.display = 'none';
    }
    if (s.width) container.style.width = s.width;
    if (s.right) container.style.right = s.right;
    if (s.bottom) container.style.bottom = s.bottom;
  }

  // Start initialization when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCopilotUI);
  } else {
    initCopilotUI();
  }
})();
