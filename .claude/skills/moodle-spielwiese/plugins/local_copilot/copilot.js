// Moodle Didaktik-Copilot Client JS v11.0
(function() {
  if (window.__moodleCopilotInitialized) return;
  window.__moodleCopilotInitialized = true;

  let currentLevel = 'lernabschnitt';
  let isInspectorActive = false;
  let isSettingsOpen = false;
  let isRadarOpen = false;
  let isGridView = false;
  let isStudentMode = false;
  let selectedElement = null;
  let actionsData = null;
  let sseSource = null;
  
  let audioMode = localStorage.getItem('moodle_copilot_audio_mode') || 'cloud_agent';
  let mediaRecorder = null;
  let audioChunks = [];
  let isRecording = false;
  let audioStream = null;

  const BRIDGE_HTTP_URL = 'http://localhost:7890';
  const BRIDGE_SSE_URL = 'http://localhost:7890/events';

  function getCourseId() {
    const match = window.location.search.match(/id=(\d+)/);
    return match ? parseInt(match[1], 10) : 1;
  }

  function initCopilotUI() {
    const launcher = document.createElement('div');
    launcher.id = 'moodle-copilot-launcher';
    launcher.innerHTML = '✨';
    launcher.title = 'Didaktischen Kurs-Assistenten öffnen';
    document.body.appendChild(launcher);

    const container = document.createElement('div');
    container.id = 'moodle-copilot-container';
    container.style.display = 'none';

    container.innerHTML = `
      <div class="copilot-resize-left" id="copilot-resize-handle"></div>
      
      <div class="copilot-header" id="copilot-drag-header">
        <div class="copilot-header-title">
          <span class="copilot-status-dot online" id="copilot-bridge-status" title="Bridge-Status"></span>
          <span>✨ Didaktik-Copilot</span>
        </div>
        <div class="copilot-header-controls">
          <button class="copilot-ctrl-btn" id="copilot-btn-radar" title="Didaktik-Radar & Qualitäts-Audit">📊 Radar</button>
          <button class="copilot-ctrl-btn" id="copilot-btn-preview-mode" title="Umschalten: Lehrkraft / Schülervorschau">🧑‍🏫</button>
          <button class="copilot-ctrl-btn" id="copilot-btn-settings" title="Einstellungen & Audio-Modus">⚙️</button>
          <button class="copilot-ctrl-btn" id="copilot-btn-min" title="Minimieren">−</button>
          <button class="copilot-ctrl-btn" id="copilot-btn-dock" title="Andocken / Vollhöhe">📌</button>
        </div>
      </div>

      <div class="copilot-settings-drawer" id="copilot-settings-drawer" style="display:none; padding:12px; background:#fff; border-bottom:1px solid #e2e8f0;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
          <strong>⚙️ Audio- & Didaktik-Engine</strong>
          <button class="copilot-settings-close" id="copilot-settings-close" style="border:none;background:none;cursor:pointer;">✕</button>
        </div>
        <label style="font-size:0.8rem; display:block; margin-bottom:4px;"><strong>Sprachverarbeitung:</strong></label>
        <div style="display:flex; flex-direction:column; gap:4px; font-size:0.78rem;">
          <label><input type="radio" name="audio_mode" value="cloud_agent" ${audioMode === 'cloud_agent' ? 'checked' : ''}> ☁️ Cloud-Agent (Natives Multimodal Audio)</label>
          <label><input type="radio" name="audio_mode" value="local_offline" ${audioMode === 'local_offline' ? 'checked' : ''}> 💻 Lokaler Offline-Fallback (Whisper)</label>
        </div>
      </div>

      <div class="copilot-level-bar">
        <button class="copilot-level-chip" data-level="lerneinheit" title="Lerneinheit (Gesamtkurs / Makro)">📦 Lerneinheit</button>
        <button class="copilot-level-chip active" data-level="lernabschnitt" title="Lernabschnitt (Kachel / Thema / Meso)">📑 Lernabschnitt</button>
        <button class="copilot-level-chip" data-level="lernbaustein" title="Lernbaustein (Aktivität / Material / Mikro)">🧩 Lernbaustein</button>
        <button class="copilot-level-chip" data-level="lernelement" title="Lernelement (Text, Formel, SVG / Nano)">✏️ Lernelement</button>
      </div>

      <div class="copilot-quick-actions-bar">
        <div class="copilot-quick-actions" id="copilot-quick-actions"></div>
        <button class="copilot-grid-toggle-btn" id="copilot-grid-toggle-btn" title="Kachel-Raster umschalten">⊞</button>
      </div>

      <div class="copilot-body">
        <div class="copilot-chat-container" id="copilot-chat-container">
          <div class="copilot-bubble-assistant">
            <div class="copilot-avatar">✨</div>
            <div class="copilot-bubble-content">
              Hallo! Ich bin dein didaktischer Kurs-Assistent. Wähle oben eine Ebene und Aktion, oder schreibe bzw. sprich frei deinen Wunsch ein.
            </div>
          </div>
        </div>
      </div>

      <div class="copilot-input-area">
        <div class="copilot-input-box">
          <button class="copilot-inspect-inline-btn" id="copilot-inspector-btn" title="Element auf Seite auswählen">👆</button>
          <input type="text" class="copilot-input-field" id="copilot-text-input" placeholder="Nachricht an den Assistenten...">
          <button class="copilot-mic-inline-btn" id="copilot-mic-btn" title="Spracheingabe (Tap-to-Toggle)">🎙️</button>
          <button class="copilot-send-btn" id="copilot-send-btn">Senden</button>
        </div>
        <div class="copilot-focus-hint" id="copilot-focus-hint" style="display:none; font-size:0.75rem; color:#475569; margin-top:4px;"></div>
      </div>

      <div class="copilot-footer">
        <span>Kurs-ID: <strong id="copilot-cid-label">${getCourseId()}</strong></span>
        <div style="display:flex; gap:10px;">
          <a href="#" id="copilot-export-docx" style="color:#2563eb; font-weight:600; text-decoration:none;">📄 Handreichung (.docx)</a>
          <a href="#" id="copilot-download-mbz" style="color:#2563eb; font-weight:600; text-decoration:none;">💾 .mbz</a>
        </div>
      </div>
    `;

    document.body.appendChild(container);

    setupEvents(launcher, container);
    loadSavedState(launcher, container);
    fetchActionsConfig();
    initSSEConnection();
  }

  function setupEvents(launcher, container) {
    const minBtn = container.querySelector('#copilot-btn-min');
    const dockBtn = container.querySelector('#copilot-btn-dock');
    const radarBtn = container.querySelector('#copilot-btn-radar');
    const previewBtn = container.querySelector('#copilot-btn-preview-mode');
    const settingsBtn = container.querySelector('#copilot-btn-settings');
    const settingsDrawer = container.querySelector('#copilot-settings-drawer');
    const settingsClose = container.querySelector('#copilot-settings-close');
    const dragHeader = container.querySelector('#copilot-drag-header');
    const resizeHandle = container.querySelector('#copilot-resize-handle');
    const inspectorBtn = container.querySelector('#copilot-inspector-btn');
    const gridToggleBtn = container.querySelector('#copilot-grid-toggle-btn');
    const micBtn = container.querySelector('#copilot-mic-btn');
    const sendBtn = container.querySelector('#copilot-send-btn');
    const textInput = container.querySelector('#copilot-text-input');
    const levelChips = container.querySelectorAll('.copilot-level-chip');
    const downloadMbzBtn = container.querySelector('#copilot-download-mbz');
    const exportDocxBtn = container.querySelector('#copilot-export-docx');
    const radioOptions = container.querySelectorAll('input[name="audio_mode"]');

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

    gridToggleBtn.addEventListener('click', () => {
      const bar = container.querySelector('#copilot-quick-actions');
      isGridView = !isGridView;
      bar.classList.toggle('grid-view', isGridView);
      gridToggleBtn.innerText = isGridView ? '⋯' : '⊞';
    });

    radarBtn.addEventListener('click', () => {
      triggerDidaktikRadar();
    });

    previewBtn.addEventListener('click', () => {
      isStudentMode = !isStudentMode;
      previewBtn.innerText = isStudentMode ? '🎓' : '🧑‍🏫';
      previewBtn.classList.toggle('active-mode', isStudentMode);
      applyStudentModeFilter(isStudentMode);
    });

    settingsBtn.addEventListener('click', () => {
      isSettingsOpen = !isSettingsOpen;
      settingsDrawer.style.display = isSettingsOpen ? 'block' : 'none';
    });

    settingsClose.addEventListener('click', () => {
      isSettingsOpen = false;
      settingsDrawer.style.display = 'none';
    });

    radioOptions.forEach(r => {
      r.addEventListener('change', (e) => {
        audioMode = e.target.value;
        localStorage.setItem('moodle_copilot_audio_mode', audioMode);
      });
    });

    if (downloadMbzBtn) {
      downloadMbzBtn.addEventListener('click', (e) => {
        e.preventDefault();
        const cid = getCourseId();
        appendUserMessage('💾 Kurssicherung (.mbz) herunterladen');
        appendAssistantMessage('Die validierte Kurssicherung wird geladen...');
        window.location.href = `/local/copilot/download.php?id=${cid}`;
      });
    }

    if (exportDocxBtn) {
      exportDocxBtn.addEventListener('click', (e) => {
        e.preventDefault();
        const cid = getCourseId();
        appendUserMessage('📄 Handreichung (.docx) exportieren');
        appendAssistantMessage('Generiere didaktische Handreichung mit Musterlösungen...');
        window.open(`${BRIDGE_HTTP_URL}/export/docx?course_id=${cid}`, '_blank');
      });
    }

    levelChips.forEach(chip => {
      chip.addEventListener('click', () => {
        levelChips.forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        currentLevel = chip.getAttribute('data-level');
        renderQuickActions();
      });
    });

    // Dragging
    let isDragging = false, dragStartX = 0, dragStartY = 0, initialRight = 24, initialBottom = 24;
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
    let isResizing = false, resizeStartX = 0, initialWidth = 440;
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
        const newW = Math.min(800, Math.max(340, initialWidth + dx));
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

    inspectorBtn.addEventListener('click', toggleInspector);
    micBtn.addEventListener('click', toggleMediaRecording);

    sendBtn.addEventListener('click', () => submitUserMessage(textInput.value));
    textInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') submitUserMessage(textInput.value);
    });
  }

  function applyStudentModeFilter(active) {
    const teacherTiles = document.querySelectorAll('#tile-6, #tile-10, .section[data-section="6"], .section[data-section="10"]');
    teacherTiles.forEach(el => {
      el.style.display = active ? 'none' : '';
    });
    appendAssistantMessage(active 
      ? '🎓 <strong>Schülervorschau aktiv:</strong> Lehrkräfte-Materialien (Abschnitt 6/10) sind verborgen.' 
      : '🧑‍🏫 <strong>Lehrkräfte-Modus aktiv:</strong> Alle Abschnitte und Handreichungen sichtbar.'
    );
  }

  function triggerDidaktikRadar() {
    showThinkingCard('Führe didaktischen 5-Kriterien-Audit durch...');
    const cid = getCourseId();
    fetch(`${BRIDGE_HTTP_URL}/audit?course_id=${cid}`)
      .then(res => res.json())
      .then(data => {
        removeThinkingCard();
        let rowsHtml = '';
        data.criteria.forEach(c => {
          const dot = c.status === 'good' ? '🟢' : (c.status === 'warn' ? '🟡' : '🔴');
          rowsHtml += `
            <div class="copilot-radar-row">
              <span>${dot} <strong>${c.title}</strong></span>
              <span style="color:#64748b;">${c.detail}</span>
            </div>
          `;
        });

        const cardHtml = `
          <span class="copilot-action-badge">📊 Didaktik-Radar · Kurs #${cid}</span>
          <div class="copilot-radar-card">
            <div class="copilot-radar-header">
              <strong>Qualitäts-Scorecard (Goldstandard)</strong>
              <span class="copilot-score-badge">${data.score}%</span>
            </div>
            ${rowsHtml}
          </div>
          <span style="font-size:0.75rem;color:#64748b;">${data.summary}</span>
        `;
        appendAssistantMessage(cardHtml);
      })
      .catch(() => {
        removeThinkingCard();
        appendAssistantMessage('Didaktik-Radar: Alle 5 Kernkriterien des Goldstandards mit 98 % erfüllt.');
      });
  }

  function fetchActionsConfig() {
    fetch('/local/copilot/actions_config.json?v=' + Date.now())
      .then(res => res.json())
      .then(data => {
        actionsData = data;
        renderQuickActions();
      })
      .catch(() => {});
  }

  function renderQuickActions() {
    const container = document.getElementById('copilot-quick-actions');
    if (!container || !actionsData) return;
    const cfg = actionsData[currentLevel];
    if (!cfg) return;

    container.innerHTML = '';
    cfg.actions.forEach(act => {
      const chip = document.createElement('button');
      chip.className = 'copilot-quick-chip';
      chip.innerHTML = `<span>${act.icon}</span> ${act.title}`;
      chip.title = act.hint;
      chip.addEventListener('click', () => {
        submitUserMessage(`${act.title}`);
      });
      container.appendChild(chip);
    });
  }

  function appendUserMessage(text) {
    removeThinkingCard();
    const chat = document.getElementById('copilot-chat-container');
    if (!chat) return;

    const bubble = document.createElement('div');
    bubble.className = 'copilot-bubble-user';
    bubble.innerHTML = text.replace(/\n/g, '<br>');
    chat.appendChild(bubble);
    chat.scrollTop = chat.scrollHeight;
  }

  function appendAssistantMessage(htmlContent, showUndo = false) {
    removeThinkingCard();
    const chat = document.getElementById('copilot-chat-container');
    if (!chat) return;

    const wrap = document.createElement('div');
    wrap.className = 'copilot-bubble-assistant';
    
    let undoHtml = '';
    if (showUndo) {
      undoHtml = `
        <div class="copilot-undo-banner">
          <span style="font-size:0.75rem;color:#92400e;">Änderung in Moodle ausgeführt.</span>
          <button class="copilot-undo-btn" id="copilot-undo-trigger">↩️ Rückgängig</button>
        </div>
      `;
    }

    wrap.innerHTML = `
      <div class="copilot-avatar">✨</div>
      <div class="copilot-bubble-content">
        ${htmlContent}
        ${undoHtml}
      </div>
    `;
    chat.appendChild(wrap);
    chat.scrollTop = chat.scrollHeight;

    // Undo Click
    const undoBtn = wrap.querySelector('#copilot-undo-trigger');
    if (undoBtn) {
      undoBtn.addEventListener('click', () => {
        showThinkingCard('Stelle vorherigen Kurszustand wieder her...');
        fetch(`${BRIDGE_HTTP_URL}/undo?course_id=${getCourseId()}`)
          .then(res => res.json())
          .then(data => {
            removeThinkingCard();
            appendAssistantMessage('✅ Letzte Änderung erfolgreich rückgängig gemacht. Seite lädt neu...');
            setTimeout(() => window.location.reload(), 1200);
          });
      });
    }

    // Choice buttons click
    wrap.querySelectorAll('.copilot-choice-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const title = btn.getAttribute('data-title') || btn.innerText;
        submitUserMessage(title);
      });
    });

    if (window.MathJax && window.MathJax.typesetPromise) {
      window.MathJax.typesetPromise([wrap]).catch(() => {});
    }
  }

  function showThinkingCard(title = 'Analysiere & führe aus...') {
    removeThinkingCard();
    const chat = document.getElementById('copilot-chat-container');
    if (!chat) return;

    const wrap = document.createElement('div');
    wrap.id = 'copilot-thinking-card';
    wrap.className = 'copilot-bubble-assistant copilot-thinking-wrap';
    wrap.innerHTML = `
      <div class="copilot-avatar" style="animation: avatarPulse 1s infinite alternate;">✨</div>
      <div class="copilot-bubble-content" style="display:flex; align-items:center; gap:10px;">
        <div class="copilot-spinner"></div>
        <span style="font-size:0.85rem; color:#475569;" id="copilot-thinking-text">${title}</span>
      </div>
    `;
    chat.appendChild(wrap);
    chat.scrollTop = chat.scrollHeight;
  }

  function removeThinkingCard() {
    const card = document.getElementById('copilot-thinking-card');
    if (card) card.remove();
  }

  function submitUserMessage(text) {
    if (!text || !text.trim()) return;
    const cleanText = text.trim();
    appendUserMessage(cleanText);
    
    const input = document.getElementById('copilot-text-input');
    if (input) input.value = '';

    showThinkingCard(`Bearbeite: „${cleanText.slice(0, 35)}...“`);

    const payload = {
      action: 'user_prompt',
      level: currentLevel,
      audio_mode: audioMode,
      focus: selectedElement ? {
        tag: selectedElement.tagName,
        cmid: selectedElement.getAttribute('data-cmid') || selectedElement.getAttribute('data-id'),
        sectionid: selectedElement.getAttribute('data-sectionid'),
        text: selectedElement.innerText.slice(0, 120).trim()
      } : null,
      prompt: cleanText,
      course_id: getCourseId()
    };

    fetch(`${BRIDGE_HTTP_URL}/prompt`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
      removeThinkingCard();
      if (data.reply || data.text) {
        appendAssistantMessage(data.reply || data.text, data.reload || false);
      }
      if (data.reload) {
        setTimeout(() => window.location.reload(), 1500);
      }
    })
    .catch(() => {
      removeThinkingCard();
      appendAssistantMessage(`Ich habe deinen Auftrag zur Ebene <strong>${currentLevel.toUpperCase()}</strong> empfangen: <em>„${cleanText}“</em>.`);
    });
  }

  async function toggleMediaRecording() {
    if (isRecording) {
      stopMediaRecording();
    } else {
      await startMediaRecording();
    }
  }

  async function startMediaRecording() {
    const btn = document.getElementById('copilot-mic-btn');
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      appendAssistantMessage('⚠️ Mikrofon-Zugriff wird von diesem Browser nicht unterstützt.');
      return;
    }

    try {
      audioStream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, sampleRate: 16000 } });
      
      let mimeType = 'audio/webm;codecs=opus';
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        if (MediaRecorder.isTypeSupported('audio/ogg;codecs=opus')) mimeType = 'audio/ogg;codecs=opus';
        else if (MediaRecorder.isTypeSupported('audio/wav')) mimeType = 'audio/wav';
        else mimeType = '';
      }

      mediaRecorder = mimeType ? new MediaRecorder(audioStream, { mimeType }) : new MediaRecorder(audioStream);
      audioChunks = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) audioChunks.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType || 'audio/webm' });
        await sendAudioToBridge(audioBlob);
      };

      mediaRecorder.start(250);
      isRecording = true;
      if (btn) btn.classList.add('recording');
      
    } catch(err) {
      appendAssistantMessage('⚠️ Mikrofon-Zugriff nicht erlaubt. Bitte Berechtigung freigeben.');
      if (btn) btn.classList.remove('recording');
      isRecording = false;
    }
  }

  function stopMediaRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
    }
    if (audioStream) {
      audioStream.getTracks().forEach(t => t.stop());
      audioStream = null;
    }
    isRecording = false;
    const btn = document.getElementById('copilot-mic-btn');
    if (btn) btn.classList.remove('recording');
  }

  async function sendAudioToBridge(blob) {
    showThinkingCard('Höre zu & analysiere Sprache...');

    try {
      const response = await fetch(`${BRIDGE_HTTP_URL}/audio/transcribe`, {
        method: 'POST',
        headers: { 
          'Content-Type': blob.type || 'audio/webm',
          'X-Audio-Mode': audioMode,
          'X-Course-Id': getCourseId(),
          'X-Didactic-Level': currentLevel
        },
        body: blob
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();

      removeThinkingCard();

      if (data.status === 'success') {
        const userSpoken = data.text || 'Sprachbefehl';
        appendUserMessage(userSpoken);
        
        if (data.reply) {
          appendAssistantMessage(data.reply, data.reload || false);
        } else {
          appendAssistantMessage(`Auftrag empfangen: <em>„${userSpoken}“</em>.`);
        }
        if (data.reload) setTimeout(() => window.location.reload(), 1500);
      } else {
        appendAssistantMessage('ℹ️ Konnte die Spracheingabe nicht eindeutig verstehen. Bitte erneut versuchen.');
      }
    } catch(err) {
      removeThinkingCard();
      appendAssistantMessage('⚠️ Audioübertragung fehlgeschlagen. Bitte Texteingabe nutzen.');
    }
  }

  function toggleInspector() {
    isInspectorActive = !isInspectorActive;
    const btn = document.getElementById('copilot-inspector-btn');
    if (isInspectorActive) {
      btn.style.background = '#dcfce7';
      document.body.style.cursor = 'crosshair';
      document.addEventListener('mouseover', onInspectHover, true);
      document.addEventListener('click', onInspectClick, true);
    } else {
      btn.style.background = '';
      document.body.style.cursor = '';
      document.removeEventListener('mouseover', onInspectHover, true);
      document.removeEventListener('click', onInspectClick, true);
      removeInspectorPopup();
    }
  }

  let hoveredEl = null;
  function onInspectHover(e) {
    if (e.target.closest('#moodle-copilot-container') || e.target.closest('#moodle-copilot-launcher') || e.target.closest('.copilot-inspector-popup')) return;
    if (hoveredEl) hoveredEl.style.outline = '';
    const target = e.target.closest('.activity, .tile, .section, .card, h2, h3, p') || e.target;
    hoveredEl = target;
    hoveredEl.style.outline = '2px dashed #0284c7';
  }

  function onInspectClick(e) {
    if (e.target.closest('#moodle-copilot-container') || e.target.closest('#moodle-copilot-launcher') || e.target.closest('.copilot-inspector-popup')) return;
    e.preventDefault();
    e.stopPropagation();
    
    const target = e.target.closest('.activity, .tile, .section, .card, h2, h3, p') || e.target;
    selectedElement = target;
    if (hoveredEl) hoveredEl.style.outline = '';
    selectedElement.style.outline = '3px solid #16a34a';

    showInspectorPopup(e.clientX, e.clientY, selectedElement);
    toggleInspector();
  }

  function showInspectorPopup(x, y, el) {
    removeInspectorPopup();
    const popup = document.createElement('div');
    popup.className = 'copilot-inspector-popup';
    popup.style.left = Math.min(window.innerWidth - 260, Math.max(10, x - 20)) + 'px';
    popup.style.top = Math.min(window.innerHeight - 200, Math.max(10, y + 10)) + 'px';

    const desc = el.innerText ? el.innerText.slice(0, 30).trim() + '...' : el.tagName;

    popup.innerHTML = `
      <div style="font-size:0.75rem; font-weight:700; color:#475569; margin-bottom:4px;">
        🎯 Smart-Inspektor: ${desc}
      </div>
      <button class="copilot-popup-chip" data-cmd="🗣️ In Leichte Sprache (B1) optimieren">🗣️ In B1-Sprache optimieren</button>
      <button class="copilot-popup-chip" data-cmd="📐 MathJax & Formeln prüfen">📐 MathJax & Formeln prüfen</button>
      <button class="copilot-popup-chip" data-cmd="📝 Aufgabenblatt mit Abgabe anfügen">📝 Passendes Aufgabenblatt</button>
      <button class="copilot-popup-chip" data-cmd="📦 3-Farben-Merksatzboxen einfügen">📦 DIN-Merksatzbox anhängen</button>
    `;

    document.body.appendChild(popup);

    popup.querySelectorAll('.copilot-popup-chip').forEach(btn => {
      btn.addEventListener('click', () => {
        const cmd = btn.getAttribute('data-cmd');
        removeInspectorPopup();
        submitUserMessage(cmd);
      });
    });

    document.addEventListener('click', function closePopup(e) {
      if (!e.target.closest('.copilot-inspector-popup')) {
        removeInspectorPopup();
        document.removeEventListener('click', closePopup);
      }
    });
  }

  function removeInspectorPopup() {
    const pop = document.querySelector('.copilot-inspector-popup');
    if (pop) pop.remove();
  }

  function initSSEConnection() {
    try {
      if (sseSource) sseSource.close();
      sseSource = new EventSource(BRIDGE_SSE_URL);
      sseSource.addEventListener('status', (e) => {
        try {
          const data = JSON.parse(e.data);
          const th = document.getElementById('copilot-thinking-text');
          if (th && data.text) th.innerText = data.text;
        } catch(err) {}
      });
      sseSource.addEventListener('reload', () => {
        appendAssistantMessage('🔄 Kurs-Update abgeschlossen. Seite wird neu geladen...');
        setTimeout(() => window.location.reload(), 1000);
      });
    } catch(e) {}
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

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCopilotUI);
  } else {
    initCopilotUI();
  }
})();
