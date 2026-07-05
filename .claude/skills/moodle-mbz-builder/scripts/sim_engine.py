#!/usr/bin/env python3
"""Sim-Engine for the moodle-mbz-builder: turn a compact simulation *spec* into a
single self-contained interactive HTML file (no external assets, offline-safe).

An interactive simulation only makes sense where a **variable relationship** can
be explored (drag a slider -> values/picture update). Not every topic has that —
use it where it fits (Ohm's law, series/parallel circuits, gear ratio, engine
crank, dosage, interest, ...), skip it elsewhere.

Why a file and not a page: Moodle's HTMLPurifier strips <script> from page/book/
database/label content, so inline JS does NOT run there. A real file served from
the file area DOES run JS. So a simulation ships as a `resource` (single .html)
or as SCORM. build_simulation.py wires the generated .html in as a resource.

A spec is a dict:
    {
      "title": str, "subtitle": str,
      "inputs": [ {"id","label","unit","min","max","step","default"} ],
      "kpis":   [ {"id","label","unit","dec"(int), "big"(bool optional)} ],
      "visual": "<svg ...>...</svg>"  # HTML/SVG with id'd elements to update
      "visual_title": str,
      "note": str (optional HTML shown under the visual),
      "compute": "<JS body>  // gets `s` (state), must `return {kpiId: value, ...}`",
      "render":  "<JS body>  // gets (root, s, o); update the visual by element id"
    }
`compute`/`render` are plain JS bodies (strings). Everything else (sliders, KPI
tiles, layout, theme, keyboard use) is generic and identical for every subject.

SIM_LIBRARY holds ready-made specs you can pull by name.
"""

_CSS = """
:root{--bg:#f4f6f8;--card:#fff;--ink:#1a1a1a;--muted:#5f6368;--blue:#185fa5;--green:#1d7a3f;--line:#c9ccd1}
@media(prefers-color-scheme:dark){:root{--bg:#1b1d1f;--card:#26292c;--ink:#e8eaed;--muted:#9aa0a6;--line:#3c4043}}
*{box-sizing:border-box}
body{margin:0;font-family:Arial,Helvetica,sans-serif;background:var(--bg);color:var(--ink)}
.wrap{max-width:900px;margin:0 auto;padding:18px}
h1{font-size:22px;margin:0 0 2px}
.sub{color:var(--muted);font-size:14px;margin:0 0 16px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:720px){.grid{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.card h2{font-size:15px;margin:0 0 10px;color:var(--blue)}
.ctl{margin:12px 0}
.ctl label{display:flex;justify-content:space-between;font-size:14px;font-weight:bold;margin-bottom:4px}
.ctl .val{color:var(--blue)}
input[type=range]{width:100%;accent-color:var(--blue)}
.out{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.kpi{background:rgba(24,95,165,.08);border:1px solid var(--line);border-radius:8px;padding:8px 10px}
.kpi .k{font-size:12px;color:var(--muted)}
.kpi .v{font-size:20px;font-weight:bold}
.kpi.big{grid-column:1/3;background:rgba(29,122,63,.12)}
.kpi.big .v{color:var(--green)}
svg{width:100%;height:auto;display:block}
.bar{height:34px;display:flex;border-radius:6px;overflow:hidden;border:1px solid var(--line);margin-top:6px}
.seg{display:flex;align-items:center;justify-content:center;color:#fff;font-size:12px;font-weight:bold;white-space:nowrap}
.foot{color:var(--muted);font-size:12px;margin-top:14px;text-align:center}
.note{background:#fbeec9;color:#5a4300;border-left:4px solid #ba7517;padding:8px 12px;border-radius:4px;font-size:13px;margin-top:12px}
"""

_ENGINE = """
(function(){
  function el(id){return document.getElementById(id);}
  var cw=el('controls');
  SPEC.inputs.forEach(function(inp){
    var d=document.createElement('div');d.className='ctl';
    d.innerHTML='<label>'+inp.label+' <span class="val"><span id="v_'+inp.id+'"></span> '+(inp.unit||'')+'</span></label>'+
      '<input type="range" id="'+inp.id+'" min="'+inp.min+'" max="'+inp.max+'" step="'+inp.step+'" value="'+inp.default+'">';
    cw.appendChild(d);
  });
  var kw=el('kpis');
  SPEC.kpis.forEach(function(k){
    var d=document.createElement('div');d.className='kpi'+(k.big?' big':'');
    d.innerHTML='<div class="k">'+k.label+'</div><div class="v"><span id="o_'+k.id+'"></span> '+(k.unit||'')+'</div>';
    kw.appendChild(d);
  });
  function fmt(v,dec){return (typeof v==='number' && isFinite(v))?v.toFixed(dec==null?0:dec):v;}
  function state(){var s={};SPEC.inputs.forEach(function(i){s[i.id]=+el(i.id).value;});return s;}
  function update(){
    var s=state();var o=SPEC.compute(s);
    SPEC.inputs.forEach(function(i){el('v_'+i.id).textContent=s[i.id];});
    SPEC.kpis.forEach(function(k){el('o_'+k.id).textContent=fmt(o[k.id],k.dec);});
    if(SPEC.render){try{SPEC.render(el('visual'),s,o);}catch(e){}}
  }
  SPEC.inputs.forEach(function(i){el(i.id).addEventListener('input',update);});
  update();
})();
"""

_HTML = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>__CSS__</style>
</head>
<body>
<div class="wrap" id="sim">
  <h1>__TITLE__</h1>
  <p class="sub">__SUBTITLE__</p>
  <div class="grid">
    <div class="card"><h2>Steuerung</h2><div id="controls"></div></div>
    <div class="card"><h2>Ergebnisse</h2><div class="out" id="kpis"></div>__EXTRA__</div>
  </div>
  <div class="card" style="margin-top:16px">
    <h2>__VISUAL_TITLE__</h2>
    <div id="visual">__VISUAL__</div>
    __NOTE__
  </div>
  <p class="foot">__FOOT__</p>
</div>
<script>
var SPEC = {
  inputs: __INPUTS__,
  kpis: __KPIS__,
  compute: function(s){ __COMPUTE__ },
  render: function(root, s, o){ __RENDER__ }
};
__ENGINE__
</script>
</body>
</html>
"""


def render(spec):
    """Return a single self-contained HTML string for the given spec."""
    import json
    note = spec.get("note", "")
    note_html = ('<div class="note">' + note + "</div>") if note else ""
    html = _HTML
    repl = {
        "__TITLE__": spec.get("title", "Simulation"),
        "__SUBTITLE__": spec.get("subtitle", ""),
        "__CSS__": _CSS,
        "__ENGINE__": _ENGINE,
        "__EXTRA__": spec.get("extra", ""),
        "__VISUAL_TITLE__": spec.get("visual_title", "Ansicht (live)"),
        "__VISUAL__": spec.get("visual", ""),
        "__NOTE__": note_html,
        "__FOOT__": spec.get("foot", "Interaktive Simulation"),
        "__INPUTS__": json.dumps(spec.get("inputs", []), ensure_ascii=False),
        "__KPIS__": json.dumps(spec.get("kpis", []), ensure_ascii=False),
        "__COMPUTE__": spec.get("compute", "return {};"),
        "__RENDER__": spec.get("render", ""),
    }
    for k, v in repl.items():
        html = html.replace(k, v)
    return html


# --------------------------------------------------------------------------- #
# SIM_LIBRARY — ready specs, pull by name via {"type":"simulation","use":"..."}.
# --------------------------------------------------------------------------- #

_SERIES_VISUAL = """
<svg viewBox="0 0 600 300" font-family="Arial,Helvetica,sans-serif">
  <g stroke="#185fa5" stroke-width="3" fill="none">
    <path d="M 70 90 L 150 90"/><path d="M 230 90 L 290 90"/><path d="M 370 90 L 430 90"/><path d="M 510 90 L 540 90"/>
    <path d="M 540 90 L 540 250"/><path d="M 540 250 L 70 250"/><path d="M 70 90 L 70 150"/><path d="M 70 170 L 70 250"/>
  </g>
  <line x1="50" y1="150" x2="90" y2="150" stroke="#888" stroke-width="2"/>
  <line x1="60" y1="170" x2="80" y2="170" stroke="#888" stroke-width="6"/>
  <text id="svgU" x="100" y="165" font-size="15" font-weight="bold" fill="currentColor">U = 24 V</text>
  <rect x="150" y="78" width="80" height="24" fill="none" stroke="#888" stroke-width="2"/>
  <rect x="290" y="78" width="80" height="24" fill="none" stroke="#888" stroke-width="2"/>
  <rect x="430" y="78" width="80" height="24" fill="none" stroke="#888" stroke-width="2"/>
  <text id="svgR1" x="190" y="68" text-anchor="middle" font-size="13" font-weight="bold" fill="currentColor">R1</text>
  <text id="svgR2" x="330" y="68" text-anchor="middle" font-size="13" font-weight="bold" fill="currentColor">R2</text>
  <text id="svgR3" x="470" y="68" text-anchor="middle" font-size="13" font-weight="bold" fill="currentColor">R3</text>
  <text id="svgU1" x="190" y="122" text-anchor="middle" font-size="13" fill="#185fa5">U1</text>
  <text id="svgU2" x="330" y="122" text-anchor="middle" font-size="13" fill="#185fa5">U2</text>
  <text id="svgU3" x="470" y="122" text-anchor="middle" font-size="13" fill="#185fa5">U3</text>
  <text id="svgI" x="300" y="278" text-anchor="middle" font-size="14" font-weight="bold" fill="#185fa5">I</text>
</svg>
"""

_SERIES_RENDER = """
var e=function(id){return document.getElementById(id);};
e('svgU').textContent='U = '+s.u+' V';
e('svgR1').textContent='R1 = '+s.r1+' \\u2126';
e('svgR2').textContent='R2 = '+s.r2+' \\u2126';
e('svgR3').textContent='R3 = '+s.r3+' \\u2126';
e('svgU1').textContent='U1 = '+o.u1.toFixed(1)+' V';
e('svgU2').textContent='U2 = '+o.u2.toFixed(1)+' V';
e('svgU3').textContent='U3 = '+o.u3.toFixed(1)+' V';
e('svgI').textContent='I = '+o.i.toFixed(o.i<100?1:0)+' mA';
var bar=document.getElementById('bar'); if(bar){bar.innerHTML='';
  var cols=['#9ccdf0','#5aa9e6','#185fa5'],ink=['#0d3c66','#0d3c66','#fff'],vals=[o.u1,o.u2,o.u3],lbl=['U1','U2','U3'];
  for(var i=0;i<3;i++){var w=s.u>0?vals[i]/s.u*100:0;var d=document.createElement('div');d.className='seg';
    d.style.width=w+'%';d.style.background=cols[i];d.style.color=ink[i];d.textContent=w>12?(lbl[i]+' '+vals[i].toFixed(1)+' V'):'';bar.appendChild(d);}}
"""

_PARALLEL_VISUAL = """
<svg viewBox="0 0 600 300" font-family="Arial,Helvetica,sans-serif">
  <g stroke="#1a1a1a" stroke-width="2.5" fill="none">
    <path d="M 70 70 L 520 70"/><path d="M 70 250 L 520 250"/><path d="M 70 70 L 70 145"/><path d="M 70 165 L 70 250"/>
  </g>
  <line x1="55" y1="145" x2="85" y2="145" stroke="#888" stroke-width="2"/>
  <line x1="63" y1="165" x2="77" y2="165" stroke="#888" stroke-width="6"/>
  <text id="svgU" x="95" y="162" font-size="14" font-weight="bold" fill="currentColor">U = 12 V</text>
  <g stroke="#185fa5" stroke-width="2.5" fill="none">
    <path d="M 210 70 L 210 120"/><path d="M 210 175 L 210 250"/><path d="M 340 70 L 340 120"/><path d="M 340 175 L 340 250"/><path d="M 470 70 L 470 120"/><path d="M 470 175 L 470 250"/></g>
  <rect x="198" y="120" width="24" height="55" fill="none" stroke="#888" stroke-width="2"/>
  <rect x="328" y="120" width="24" height="55" fill="none" stroke="#888" stroke-width="2"/>
  <rect x="458" y="120" width="24" height="55" fill="none" stroke="#888" stroke-width="2"/>
  <text id="svgR1" x="232" y="150" font-size="12" font-weight="bold" fill="currentColor">R1</text>
  <text id="svgR2" x="362" y="150" font-size="12" font-weight="bold" fill="currentColor">R2</text>
  <text id="svgR3" x="492" y="150" font-size="12" font-weight="bold" fill="currentColor">R3</text>
  <text id="svgI1" x="188" y="105" text-anchor="end" font-size="12" fill="#1d7a3f">I1</text>
  <text id="svgI2" x="318" y="105" text-anchor="end" font-size="12" fill="#1d7a3f">I2</text>
  <text id="svgI3" x="448" y="105" text-anchor="end" font-size="12" fill="#1d7a3f">I3</text>
  <text id="svgIg" x="300" y="278" text-anchor="middle" font-size="14" font-weight="bold" fill="#185fa5">Iges</text>
</svg>
"""

_PARALLEL_RENDER = """
var e=function(id){return document.getElementById(id);};
e('svgU').textContent='U = '+s.u+' V';
e('svgR1').textContent='R1 = '+s.r1+' \\u2126';
e('svgR2').textContent='R2 = '+s.r2+' \\u2126';
e('svgR3').textContent='R3 = '+s.r3+' \\u2126';
e('svgI1').textContent='I1='+o.i1.toFixed(0)+'mA';
e('svgI2').textContent='I2='+o.i2.toFixed(0)+'mA';
e('svgI3').textContent='I3='+o.i3.toFixed(0)+'mA';
e('svgIg').textContent='Iges = '+o.iges.toFixed(0)+' mA';
"""

SIM_LIBRARY = {
    "reihenschaltung": {
        "title": "Interaktive Reihenschaltung",
        "subtitle": "Verändere Spannung und Widerstände – Strom und Teilspannungen rechnen sofort mit.",
        "inputs": [
            {"id": "u", "label": "Spannung U", "unit": "V", "min": 0, "max": 24, "step": 1, "default": 24},
            {"id": "r1", "label": "Widerstand R1", "unit": "Ω", "min": 10, "max": 500, "step": 10, "default": 100},
            {"id": "r2", "label": "Widerstand R2", "unit": "Ω", "min": 10, "max": 500, "step": 10, "default": 200},
            {"id": "r3", "label": "Widerstand R3", "unit": "Ω", "min": 10, "max": 500, "step": 10, "default": 300},
        ],
        "kpis": [
            {"id": "i", "label": "Strom I (überall gleich)", "unit": "mA", "dec": 1, "big": True},
            {"id": "rges", "label": "Gesamtwiderstand", "unit": "Ω", "dec": 0},
            {"id": "usum", "label": "Kontrolle U1+U2+U3", "unit": "V", "dec": 2},
            {"id": "u1", "label": "U1 an R1", "unit": "V", "dec": 2},
            {"id": "u2", "label": "U2 an R2", "unit": "V", "dec": 2},
            {"id": "u3", "label": "U3 an R3", "unit": "V", "dec": 2},
        ],
        "compute": "var Rg=s.r1+s.r2+s.r3;var I=Rg>0?s.u/Rg:0;return {i:I*1000,rges:Rg,u1:I*s.r1,u2:I*s.r2,u3:I*s.r3,usum:I*Rg};",
        "visual_title": "Schaltbild (live)",
        "visual": _SERIES_VISUAL,
        "extra": '<div class="k" style="font-size:12px;color:var(--muted);margin-top:10px">Spannungsteilung</div><div class="bar" id="bar"></div>',
        "render": _SERIES_RENDER,
        "note": "⚠ <b>Regeln:</b> Der Strom I ist an jeder Stelle gleich; die Teilspannungen addieren sich zu U; am größten Widerstand fällt die größte Spannung ab.",
        "foot": "Interaktive Simulation · Elektrotechnik · Reihenschaltung",
    },
    "parallelschaltung": {
        "title": "Interaktive Parallelschaltung",
        "subtitle": "Verändere Spannung und Widerstände – Zweigströme und Gesamtstrom rechnen sofort mit.",
        "inputs": [
            {"id": "u", "label": "Spannung U", "unit": "V", "min": 0, "max": 24, "step": 1, "default": 12},
            {"id": "r1", "label": "Widerstand R1", "unit": "Ω", "min": 10, "max": 500, "step": 1, "default": 60},
            {"id": "r2", "label": "Widerstand R2", "unit": "Ω", "min": 10, "max": 500, "step": 1, "default": 40},
            {"id": "r3", "label": "Widerstand R3", "unit": "Ω", "min": 10, "max": 500, "step": 1, "default": 24},
        ],
        "kpis": [
            {"id": "iges", "label": "Gesamtstrom Iges", "unit": "mA", "dec": 0, "big": True},
            {"id": "rges", "label": "Gesamtwiderstand", "unit": "Ω", "dec": 1},
            {"id": "usum", "label": "Spannung je Zweig", "unit": "V", "dec": 0},
            {"id": "i1", "label": "I1 durch R1", "unit": "mA", "dec": 0},
            {"id": "i2", "label": "I2 durch R2", "unit": "mA", "dec": 0},
            {"id": "i3", "label": "I3 durch R3", "unit": "mA", "dec": 0},
        ],
        "compute": "var g=1/s.r1+1/s.r2+1/s.r3;var Rg=g>0?1/g:0;var I1=s.u/s.r1,I2=s.u/s.r2,I3=s.u/s.r3;return {iges:(I1+I2+I3)*1000,rges:Rg,usum:s.u,i1:I1*1000,i2:I2*1000,i3:I3*1000};",
        "visual_title": "Schaltbild (live)",
        "visual": _PARALLEL_VISUAL,
        "render": _PARALLEL_RENDER,
        "note": "⚠ <b>Regeln:</b> An jedem Zweig liegt die volle Spannung; die Zweigströme addieren sich zum Gesamtstrom; der kleinste Widerstand zieht den größten Strom.",
        "foot": "Interaktive Simulation · Elektrotechnik · Parallelschaltung",
    },
}
