#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""hotspot_engine.py — Interaktive Hotspot-Grafiken (H5P-Stil, offline-safe, responsive)
fuer den Moodle-MBZ-Builder.

Unterstützt SVG-Grafiken und Rasterbilder (PNG/JPG), Pins mit x/y in Prozent,
MathJax-Formeln in Tooltips und Tastaturnavigation.
"""
import base64
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
<script>
window.MathJax = {
  tex: { inlineMath: [['$', '$'], ['\\\\(', '\\\\)']] },
  svg: { fontCache: 'global' }
};
</script>
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
  --pulse-color: rgba(2, 132, 199, 0.6);
  --shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.08);
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

* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  background: var(--bg-primary);
  color: var(--text-main);
  line-height: 1.6;
  padding: 16px;
}

.hotspot-app {
  max-width: 1200px;
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
  border-bottom: 2px solid var(--border);
}

.app-header h1 {
  font-size: 1.4rem;
  color: var(--text-main);
  display: flex;
  align-items: center;
  gap: 8px;
}

.app-header p {
  font-size: 0.95rem;
  color: var(--text-muted);
}

.progress-badge {
  background: var(--primary-light);
  color: var(--primary);
  padding: 6px 14px;
  border-radius: 999px;
  font-size: 0.88rem;
  font-weight: 600;
}

.main-stage {
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: 20px;
  align-items: start;
}

@media (max-width: 900px) {
  .main-stage {
    grid-template-columns: 1fr;
  }
}

.canvas-container {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px;
  overflow-x: auto;
  box-shadow: var(--shadow);
  position: relative;
}

.svg-wrapper {
  position: relative;
  width: 100%;
  max-width: 100%;
  display: block;
}

.svg-wrapper svg, .svg-wrapper img {
  width: 100%;
  height: auto;
  display: block;
  border-radius: 8px;
}

/* Hotspot Pins */
.hotspot-pin {
  position: absolute;
  width: 32px;
  height: 32px;
  transform: translate(-50%, -50%);
  background: var(--primary);
  color: #ffffff;
  border: 3px solid #ffffff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 14px;
  cursor: pointer;
  box-shadow: 0 4px 10px rgba(0,0,0,0.25);
  transition: transform 0.2s, background-color 0.2s;
  z-index: 10;
}

.hotspot-pin::after {
  content: '';
  position: absolute;
  top: -6px; left: -6px; right: -6px; bottom: -6px;
  border-radius: 50%;
  border: 2px solid var(--primary);
  animation: pulse-ring 2s infinite cubic-bezier(0.215, 0.61, 0.355, 1);
  pointer-events: none;
}

@keyframes pulse-ring {
  0% { transform: scale(0.9); opacity: 0.8; }
  70% { transform: scale(1.5); opacity: 0; }
  100% { transform: scale(1.5); opacity: 0; }
}

.hotspot-pin:hover, .hotspot-pin.active {
  transform: translate(-50%, -50%) scale(1.2);
  background: var(--accent);
  border-color: #ffffff;
  z-index: 20;
}

.hotspot-pin.visited {
  background: #10b981;
}

/* Detail Panel */
.detail-panel {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
  box-shadow: var(--shadow);
  min-height: 280px;
}

.panel-title {
  font-size: 1.2rem;
  color: var(--primary);
  margin-bottom: 8px;
}

.panel-desc {
  font-size: 0.95rem;
  color: var(--text-main);
  line-height: 1.6;
}

.nav-buttons {
  display: flex;
  justify-content: space-between;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}

.btn-nav {
  padding: 8px 14px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.88rem;
  color: var(--text-main);
  font-weight: 500;
}

.btn-nav:hover:not(:disabled) {
  background: var(--primary);
  color: #ffffff;
}

.btn-nav:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
</head>
<body>
<div class="hotspot-app">
  <div class="app-header">
    <div>
      <h1><span style="color:var(--primary);">◉</span> {{TITLE}}</h1>
      <p>{{SUBTITLE}}</p>
    </div>
    <div class="progress-badge" id="progress-badge">
      <span id="visited-text">0 von {{TOTAL_COUNT}} Punkten erkundet</span>
    </div>
  </div>

  <div class="main-stage">
    <div class="canvas-container">
      <div class="svg-wrapper" id="svg-wrapper">
        {{SVG_CONTENT}}
      </div>
    </div>

    <div class="detail-panel" id="detail-panel">
      <div id="panel-content">
        <h2 class="panel-title" id="card-title">Titel</h2>
        <div class="panel-desc" id="card-desc">Beschreibungstext</div>
        <div class="nav-buttons">
          <button class="btn-nav" id="btn-prev">◀ Zurück</button>
          <button class="btn-nav" id="btn-next">Weiter ▶</button>
        </div>
      </div>
    </div>
  </div>
</div>

<script>
const DATA = {{DATA_JSON}};
let activeIndex = -1;
const visited = new Set();

const svgWrapper = document.getElementById('svg-wrapper');
const cardTitle = document.getElementById('card-title');
const cardDesc = document.getElementById('card-desc');
const visitedText = document.getElementById('visited-text');
const btnPrev = document.getElementById('btn-prev');
const btnNext = document.getElementById('btn-next');

DATA.hotspots.forEach((hs, idx) => {
  const pin = document.createElement('button');
  pin.className = 'hotspot-pin';
  pin.id = 'pin-' + idx;
  pin.innerHTML = (idx + 1);
  pin.style.left = hs.x + '%';
  pin.style.top = hs.y + '%';
  pin.addEventListener('click', () => selectHotspot(idx));
  svgWrapper.appendChild(pin);
});

function selectHotspot(idx) {
  if (idx < 0 || idx >= DATA.hotspots.length) return;
  activeIndex = idx;
  visited.add(idx);
  
  document.querySelectorAll('.hotspot-pin').forEach((p, i) => {
    p.classList.toggle('active', i === idx);
    if (visited.has(i) && i !== idx) p.classList.add('visited');
  });
  
  const hs = DATA.hotspots[idx];
  cardTitle.innerHTML = hs.title || ('Punkt ' + (idx + 1));
  let descHtml = hs.desc || hs.description || hs.content || '';
  if (hs.details && typeof hs.details === 'object') {
    descHtml += '<div style="margin-top:12px;display:grid;gap:6px;">';
    for (const [k, v] of Object.entries(hs.details)) {
      descHtml += `<div style="font-size:0.88rem;background:var(--bg-secondary);padding:6px 10px;border-radius:6px;border:1px solid var(--border);"><b>${k}:</b> ${v}</div>`;
    }
    descHtml += '</div>';
  }
  if (hs.merksatz) {
    descHtml += `<div style="margin-top:12px;padding:10px 12px;background:var(--accent-light);border-left:4px solid var(--accent);border-radius:4px;font-size:0.88rem;font-weight:500;">💡 <b>Merksatz:</b> ${hs.merksatz}</div>`;
  }
  cardDesc.innerHTML = descHtml;
  visitedText.innerText = visited.size + ' von ' + DATA.hotspots.length + ' Punkten erkundet';
  
  btnPrev.disabled = (idx === 0);
  btnNext.disabled = (idx === DATA.hotspots.length - 1);
  
  if (window.MathJax && window.MathJax.typesetPromise) {
    MathJax.typesetPromise();
  }
}

btnPrev.addEventListener('click', () => { if (activeIndex > 0) selectHotspot(activeIndex - 1); });
btnNext.addEventListener('click', () => { if (activeIndex < DATA.hotspots.length - 1) selectHotspot(activeIndex + 1); });

if (DATA.hotspots.length > 0) {
  selectHotspot(0);
}
</script>
</body>
</html>
"""


def generate_hotspot_html(spec):
    title = spec.get("title", "Interaktive Formel- und Bauteil-Anatomie")
    subtitle = spec.get("subtitle", "Klicken Sie auf die nummerierten Pins, um Details zu erkunden.")
    
    img_ref = spec.get("svg") or spec.get("image") or ""
    svg_content = ""
    
    if img_ref and os.path.exists(img_ref):
        if img_ref.lower().endswith(".svg"):
            with open(img_ref, "r", encoding="utf-8") as f:
                svg_content = f.read()
        elif img_ref.lower().endswith((".png", ".jpg", ".jpeg")):
            with open(img_ref, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
            ext = os.path.splitext(img_ref)[1].lstrip(".").lower()
            mime = "image/jpeg" if ext in ("jpg", "jpeg") else "image/png"
            svg_content = f'<img src="data:{mime};base64,{b64}" alt="{title}" style="width:100%;height:auto;border-radius:8px;" />'
    elif "<svg" in img_ref:
        svg_content = img_ref
    else:
        svg_content = f"""<svg viewBox="0 0 800 450" xmlns="http://www.w3.org/2000/svg" style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px;">
          <rect x="20" y="20" width="760" height="410" rx="8" fill="#ffffff" stroke="#cbd5e1"/>
          <text x="400" y="225" text-anchor="middle" font-family="sans-serif" font-size="20" fill="#0284c7" font-weight="bold">{title}</text>
        </svg>"""

    hotspots = spec.get("hotspots") or spec.get("pins") or []
    
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

    return html


if __name__ == "__main__":
    if len(sys.argv) > 1:
        spec = json.load(open(sys.argv[1], encoding="utf-8"))
        out = sys.argv[2] if len(sys.argv) > 2 else "hotspot.html"
        open(out, "w", encoding="utf-8").write(generate_hotspot_html(spec))
        print(f"Hotspot-Widget geschrieben: {out}")
