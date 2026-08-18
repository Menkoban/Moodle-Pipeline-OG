#!/usr/bin/env python3
"""hotspot_engine.py — Interaktive Hotspot-Grafiken (H5P-Stil, offline-safe)
fuer den Moodle-MBZ-Builder.

Verwandelt SVG-Vektorgrafiken (Schaltplaene, Schaltschraenke, Maschinen,
anatomische Modelle, Geschaeftsprozesse) in interaktive, responsive
Erkundungs-Widgets mit pulsierenden Markern, Detail-Karten und Fortschritts-Tracker.
"""

import json
import os
import re
import sys

HOTSPOT_TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{TITLE}}</title>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
<style>
:root {
  --bg-primary: #ffffff;
  --bg-secondary: #f8fafc;
  --bg-card: #ffffff;
  --text-main: #0f172a;
  --text-muted: #64748b;
  --border: #e2e8f0;
  --primary: #0284c7;
  --primary-hover: #0369a1;
  --primary-light: #e0f2fe;
  --accent: #f59e0b;
  --accent-light: #fef3c7;
  --success: #10b981;
  --pulse-color: rgba(2, 132, 199, 0.6);
  --shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.08), 0 8px 10px -6px rgba(0, 0, 0, 0.04);
  --radius: 12px;
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg-primary: #0f172a;
    --bg-secondary: #1e293b;
    --bg-card: #1e293b;
    --text-main: #f8fafc;
    --text-muted: #94a3b8;
    --border: #334155;
    --primary: #38bdf8;
    --primary-hover: #7dd3fc;
    --primary-light: rgba(56, 189, 248, 0.15);
    --accent: #fbbf24;
    --accent-light: rgba(251, 191, 36, 0.15);
    --pulse-color: rgba(56, 189, 248, 0.6);
    --shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
  }
}

body.light-theme {
  --bg-primary: #ffffff;
  --bg-secondary: #f8fafc;
  --bg-card: #ffffff;
  --text-main: #0f172a;
  --text-muted: #64748b;
  --border: #e2e8f0;
  --primary: #0284c7;
  --primary-hover: #0369a1;
  --primary-light: #e0f2fe;
  --accent: #f59e0b;
  --accent-light: #fef3c7;
  --pulse-color: rgba(2, 132, 199, 0.6);
  --shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.08);
}

body.dark-theme {
  --bg-primary: #0f172a;
  --bg-secondary: #1e293b;
  --bg-card: #1e293b;
  --text-main: #f8fafc;
  --text-muted: #94a3b8;
  --border: #334155;
  --primary: #38bdf8;
  --primary-hover: #7dd3fc;
  --primary-light: rgba(56, 189, 248, 0.15);
  --accent: #fbbf24;
  --accent-light: rgba(251, 191, 36, 0.15);
  --pulse-color: rgba(56, 189, 248, 0.6);
  --shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
}

* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  background: var(--bg-primary);
  color: var(--text-main);
  line-height: 1.6;
  padding: 16px;
}

.hotspot-app {
  max-width: 1280px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}

.title-wrap h1 {
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--text-main);
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-wrap p {
  font-size: 0.9rem;
  color: var(--text-muted);
  margin-top: 4px;
}

.header-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.progress-badge {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--primary);
  display: flex;
  align-items: center;
  gap: 6px;
}

.theme-toggle-btn {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  color: var(--text-main);
  padding: 6px 12px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 600;
  transition: all 0.2s ease;
}
.theme-toggle-btn:hover { background: var(--border); }

/* Main Interactive Canvas Area */
.main-stage {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(360px, 1fr);
  gap: 20px;
  align-items: stretch;
}

@media (max-width: 960px) {
  .main-stage { grid-template-columns: 1fr; }
}

.canvas-container {
  position: relative;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  box-shadow: var(--shadow);
  padding: 16px;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 440px;
}

.svg-wrapper {
  position: relative;
  width: 100%;
  max-width: 100%;
  display: block;
  line-height: 0;
}

.svg-wrapper svg {
  width: 100%;
  height: auto;
  display: block;
  border-radius: 8px;
}

/* Highlight Glow in SVG */
.highlight-glow {
  filter: drop-shadow(0 0 10px var(--accent));
  transition: all 0.3s;
  stroke: var(--accent) !important;
  stroke-width: 3px !important;
}

/* Hotspot Pins */
.hotspot-pin {
  position: absolute;
  width: 34px;
  height: 34px;
  transform: translate(-50%, -50%);
  background: var(--primary);
  color: #ffffff;
  border: 2.5px solid #ffffff;
  border-radius: 50%;
  display: flex;
  justify-content: center;
  align-items: center;
  font-weight: 700;
  font-size: 14px;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
  transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1), background 0.2s ease, box-shadow 0.2s;
  z-index: 10;
  outline: none;
}

.hotspot-pin:hover, .hotspot-pin:focus-visible {
  transform: translate(-50%, -50%) scale(1.25);
  background: var(--primary-hover);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.35);
  z-index: 20;
}

.hotspot-pin.active {
  background: var(--accent);
  color: #0f172a;
  transform: translate(-50%, -50%) scale(1.3);
  box-shadow: 0 0 0 4px rgba(245, 158, 11, 0.3), 0 8px 20px rgba(0, 0, 0, 0.3);
  z-index: 25;
}

.hotspot-pin.visited::after {
  content: "";
  position: absolute;
  top: -2px;
  right: -2px;
  width: 9px;
  height: 9px;
  background: var(--success);
  border: 1.5px solid #ffffff;
  border-radius: 50%;
}

.hotspot-pin .pulse {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  border-radius: 50%;
  animation: pulse-animation 2s infinite cubic-bezier(0.24, 0, 0.38, 1);
  pointer-events: none;
}

@keyframes pulse-animation {
  0% { transform: scale(1); box-shadow: 0 0 0 0 var(--pulse-color); }
  70% { transform: scale(1.8); box-shadow: 0 0 0 12px rgba(0, 0, 0, 0); }
  100% { transform: scale(2.2); box-shadow: 0 0 0 0 rgba(0, 0, 0, 0); }
}

/* Detail Card Panel */
.detail-panel {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 22px;
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
  gap: 14px;
  overflow-y: auto;
  max-height: 80vh;
}

.panel-empty {
  color: var(--text-muted);
  text-align: center;
  padding: 60px 20px;
  font-size: 1rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}
.panel-empty .icon {
  font-size: 2.5rem;
  color: var(--primary);
  opacity: 0.7;
}

.panel-category {
  display: inline-block;
  align-self: flex-start;
  background: var(--primary-light);
  color: var(--primary);
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  padding: 4px 10px;
  border-radius: 6px;
}

.panel-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-main);
  line-height: 1.35;
  margin-top: 2px;
}

.panel-desc {
  font-size: 0.95rem;
  color: var(--text-main);
  line-height: 1.6;
}

.panel-desc p { margin-bottom: 8px; }

.panel-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 6px;
  font-size: 0.88rem;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid var(--border);
}

.panel-table td {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
}

.panel-table tr:nth-child(even) {
  background: var(--bg-secondary);
}

.panel-table td.key {
  font-weight: 600;
  color: var(--text-muted);
  width: 38%;
  vertical-align: top;
}

.panel-table td.val {
  color: var(--text-main);
  font-family: inherit;
  font-weight: 500;
}

.callout-box {
  background: var(--accent-light);
  border-left: 4px solid var(--accent);
  padding: 12px 14px;
  border-radius: 0 8px 8px 0;
  font-size: 0.88rem;
  color: var(--text-main);
  line-height: 1.5;
}
.callout-box b { color: #b45309; }

.nav-buttons {
  display: flex;
  justify-content: space-between;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}

.btn-nav {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  color: var(--text-main);
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.88rem;
  font-weight: 600;
  transition: all 0.2s ease;
}
.btn-nav:hover:not(:disabled) {
  background: var(--primary);
  color: #ffffff;
  border-color: var(--primary);
}
.btn-nav:disabled { opacity: 0.35; cursor: not-allowed; }
</style>
</head>
<body>
<div class="hotspot-app">
  <div class="app-header">
    <div class="title-wrap">
      <h1><span style="color:var(--primary);">◉</span> {{TITLE}}</h1>
      <p>{{SUBTITLE}}</p>
    </div>
    <div class="header-controls">
      <div class="progress-badge" id="progress-badge">
        <span id="visited-text">0 von {{TOTAL_COUNT}} Punkten erkundet</span>
      </div>
      <button class="theme-toggle-btn" id="theme-btn" aria-label="Farbschema umschalten">🌓 Farbmodus</button>
    </div>
  </div>

  <div class="main-stage">
    <!-- Interactive SVG Container -->
    <div class="canvas-container">
      <div class="svg-wrapper" id="svg-wrapper">
        {{SVG_CONTENT}}
        <!-- Hotspot Pins injected via JS -->
      </div>
    </div>

    <!-- Detail Info Sidebar -->
    <div class="detail-panel" id="detail-panel" aria-live="polite">
      <div class="panel-empty" id="panel-empty">
        <div class="icon">🔍</div>
        <p><b>Interaktives Bauteil-Labor</b><br/>Klicke auf eine pulsierende Markierung in der Grafik, um die Funktionsweise, Werkstoffdaten und Praxistipps anzuzeigen.</p>
      </div>
      <div id="panel-content" style="display:none; flex-direction:column; gap:12px;">
        <span class="panel-category" id="card-cat">Kategorie</span>
        <h2 class="panel-title" id="card-title">Titel</h2>
        <div class="panel-desc" id="card-desc">Beschreibungstext</div>
        
        <table class="panel-table" id="card-table">
          <tbody id="card-table-body"></tbody>
        </table>

        <div class="callout-box" id="card-callout" style="display:none;">
          <b>Praxistipp / Werkstatt-Regel:</b> <span id="callout-text"></span>
        </div>

        <div class="nav-buttons">
          <button class="btn-nav" id="btn-prev" aria-label="Vorheriger Hotspot">◀ Zurück</button>
          <button class="btn-nav" id="btn-next" aria-label="Nächster Hotspot">Weiter ▶</button>
        </div>
      </div>
    </div>
  </div>
</div>

<script>
const DATA = {{DATA_JSON}};
const SVG_VB = {{VIEWBOX_JSON}};

let activeIndex = -1;
const visited = new Set();

const svgWrapper = document.getElementById('svg-wrapper');
const panelEmpty = document.getElementById('panel-empty');
const panelContent = document.getElementById('panel-content');
const cardCat = document.getElementById('card-cat');
const cardTitle = document.getElementById('card-title');
const cardDesc = document.getElementById('card-desc');
const cardTableBody = document.getElementById('card-table-body');
const cardCallout = document.getElementById('card-callout');
const calloutText = document.getElementById('callout-text');
const visitedText = document.getElementById('visited-text');
const btnPrev = document.getElementById('btn-prev');
const btnNext = document.getElementById('btn-next');
const themeBtn = document.getElementById('theme-btn');

// Theme Switcher
themeBtn.addEventListener('click', () => {
  if (document.body.classList.contains('dark-theme')) {
    document.body.classList.remove('dark-theme');
    document.body.classList.add('light-theme');
  } else {
    document.body.classList.remove('light-theme');
    document.body.classList.add('dark-theme');
  }
});

// Render Hotspots onto SVG Wrapper with 100% responsive percent coordinates
DATA.hotspots.forEach((hs, idx) => {
  const pin = document.createElement('button');
  pin.className = 'hotspot-pin';
  pin.id = 'pin-' + idx;
  pin.setAttribute('aria-label', hs.title || ('Hotspot ' + (idx + 1)));
  
  let leftPct = hs.x;
  let topPct = hs.y;
  
  // Normalize pixel coordinates against SVG viewBox width and height
  if (typeof hs.x === 'number') {
    if (hs.x > 100 && SVG_VB && SVG_VB.w > 0) {
      leftPct = ((hs.x - SVG_VB.x) / SVG_VB.w) * 100;
    }
    pin.style.left = leftPct + '%';
  } else {
    pin.style.left = hs.x;
  }
  
  if (typeof hs.y === 'number') {
    if (hs.y > 100 && SVG_VB && SVG_VB.h > 0) {
      topPct = ((hs.y - SVG_VB.y) / SVG_VB.h) * 100;
    }
    pin.style.top = topPct + '%';
  } else {
    pin.style.top = hs.y;
  }
  
  pin.innerHTML = (hs.number || (idx + 1)) + '<span class="pulse"></span>';

  pin.addEventListener('click', () => selectHotspot(idx));
  pin.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      selectHotspot(idx);
    }
  });

  svgWrapper.appendChild(pin);
});

function selectHotspot(idx) {
  if (idx < 0 || idx >= DATA.hotspots.length) return;
  activeIndex = idx;
  const hs = DATA.hotspots[idx];
  visited.add(idx);
  visitedText.textContent = visited.size + " von " + DATA.hotspots.length + " Punkten erkundet";

  // Update pin active states
  DATA.hotspots.forEach((h, i) => {
    const p = document.getElementById('pin-' + i);
    if (!p) return;
    p.classList.remove('active');
    if (visited.has(i)) p.classList.add('visited');
    if (i === idx) p.classList.add('active');
    
    // Manage SVG highlights
    if (h.id) {
      const svgEl = document.getElementById(h.id);
      if (svgEl) {
        if (i === idx) {
          svgEl.classList.add('highlight-glow');
        } else {
          svgEl.classList.remove('highlight-glow');
        }
      }
    }
  });

  // Populate Details
  panelEmpty.style.display = 'none';
  panelContent.style.display = 'flex';

  cardCat.textContent = hs.category || 'Bauteil / Komponente';
  cardTitle.textContent = hs.title;
  cardDesc.innerHTML = hs.content;

  // Key-Value Table
  cardTableBody.innerHTML = '';
  if (hs.details && Object.keys(hs.details).length > 0) {
    for (const [k, v] of Object.entries(hs.details)) {
      const row = document.createElement('tr');
      row.innerHTML = `<td class="key">${k}</td><td class="val">${v}</td>`;
      cardTableBody.appendChild(row);
    }
  }

  // Callout Box
  const tip = hs.praxistipp || hs.merksatz || hs.regel;
  if (tip) {
    cardCallout.style.display = 'block';
    calloutText.innerHTML = tip;
  } else {
    cardCallout.style.display = 'none';
  }

  // Nav buttons
  btnPrev.disabled = (idx === 0);
  btnNext.disabled = (idx === DATA.hotspots.length - 1);
  
  if (window.MathJax) {
    MathJax.typesetPromise();
  }
}

btnPrev.addEventListener('click', () => { if (activeIndex > 0) selectHotspot(activeIndex - 1); });
btnNext.addEventListener('click', () => { if (activeIndex < DATA.hotspots.length - 1) selectHotspot(activeIndex + 1); });

// Auto-select first hotspot on initial load for instant engagement
if (DATA.hotspots.length > 0) {
  selectHotspot(0);
}
</script>
</body>
</html>
"""


def _extract_viewbox(svg_content):
    """Extrahiert x, y, w, h aus einem viewBox-Attribut eines SVGs."""
    m = re.search(r'viewBox\s*=\s*["\']\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*["\']', svg_content, re.I)
    if m:
        return {
            "x": float(m.group(1)),
            "y": float(m.group(2)),
            "w": float(m.group(3)),
            "h": float(m.group(4))
        }
    # Fallback auf width/height
    mw = re.search(r'width\s*=\s*["\']\s*([\d.]+)', svg_content, re.I)
    mh = re.search(r'height\s*=\s*["\']\s*([\d.]+)', svg_content, re.I)
    if mw and mh:
        return {"x": 0.0, "y": 0.0, "w": float(mw.group(1)), "h": float(mh.group(1))}
    return {"x": 0.0, "y": 0.0, "w": 800.0, "h": 450.0}


def generate_hotspot_html(spec):
    """Erzeugt eine vollstaendige HTML-Datei aus einem Hotspot-Spezifikations-Dict."""
    title = spec.get("title", "Interaktive Hotspot-Grafik")
    subtitle = spec.get("subtitle", "Klicke auf die pulsierenden Markierungen, um Details zu erkunden.")
    
    # SVG-Content ermitteln
    svg_raw = spec.get("svg", "")
    if svg_raw.endswith(".svg") and os.path.exists(svg_raw):
        with open(svg_raw, "r", encoding="utf-8") as f:
            svg_content = f.read()
    elif "<svg" in svg_raw:
        svg_content = svg_raw
    else:
        # Fallback Standard-SVG Box
        svg_content = f"""<svg viewBox="0 0 800 500" xmlns="http://www.w3.org/2000/svg" style="background:#ffffff; border:1px solid #cbd5e1;">
          <rect x="50" y="50" width="700" height="400" rx="8" fill="#f8fafc" stroke="#94a3b8" stroke-width="3"/>
          <text x="400" y="250" text-anchor="middle" font-family="sans-serif" font-size="20" fill="#64748b">{title}</text>
        </svg>"""

    viewbox = _extract_viewbox(svg_content)
    hotspots = spec.get("hotspots", [])
    data_payload = {
        "title": title,
        "subtitle": subtitle,
        "hotspots": hotspots
    }

    html = HOTSPOT_TEMPLATE
    html = html.replace("{{TITLE}}", title)
    html = html.replace("{{SUBTITLE}}", subtitle)
    html = html.replace("{{TOTAL_COUNT}}", str(len(hotspots)))
    html = html.replace("{{SVG_CONTENT}}", svg_content)
    html = html.replace("{{DATA_JSON}}", json.dumps(data_payload, ensure_ascii=False))
    html = html.replace("{{VIEWBOX_JSON}}", json.dumps(viewbox))

    return html


if __name__ == "__main__":
    if len(sys.argv) > 1:
        spec = json.load(open(sys.argv[1], encoding="utf-8"))
        out = sys.argv[2] if len(sys.argv) > 2 else "hotspot.html"
        open(out, "w", encoding="utf-8").write(generate_hotspot_html(spec))
        print(f"Hotspot-Widget geschrieben: {out}")
