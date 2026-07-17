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
      "inputs": [ {"id","label","unit","min","max","step","default", "type"?} ],
      "kpis":   [ {"id","label","unit","dec"(int), "big"(bool optional)} ],
      "visual": "<svg ...>...</svg>"  # HTML/SVG with id'd elements to update
      "visual_title": str,
      "note": str (optional HTML shown under the visual),
      "compute": "<JS body>  // gets `s` (state), must `return {kpiId: value, ...}`",
      "render":  "<JS body>  // gets (root, s, o); update the visual by element id",
      "animate": "<JS body>"    # OPTIONAL, see below,
      "challenge": { ... }       # OPTIONAL, see below
    }
`compute`/`render` are plain JS bodies (strings). Everything else (sliders, KPI
tiles, layout, theme, keyboard use) is generic and identical for every subject.

Three fields are OPTIONAL and fully BACKWARD-COMPATIBLE — a spec without any of
them renders exactly as it always has (no Play button, no challenge card):

  * `animate`  — a JS body with the signature `(root, s, o, t)`, where `t` is the
    number of seconds since Play (already scaled by the speed control). When
    present, the engine adds a Play/Pause button, a speed control (0.1x-4x) and
    a Reset (t=0), and drives a `requestAnimationFrame` loop that advances
    `t += dt*speed` per frame and calls the body. Playback starts PAUSED. Slider
    changes still call `update()` (which also calls `animate` with the frozen t,
    so a paused picture stays in sync). Use it for anything that runs over time
    (a sine wave, a moving piston, a charging capacitor, flowing current).

  * `inputs[i].type`  — `"range"` (default, unchanged: min/max/step/default),
    `"select"` (needs `options:[{value,label}]` -> a `<select>`) or `"toggle"`
    (a checkbox with `on`/`off` values, default `1`/`0`; `default` truthy = on;
    optional `onLabel`/`offLabel` for the read-out). `state()` reads all three
    the same way — a number for range/toggle, the chosen value for select — so
    `compute`/`render`/`animate` consume them without any per-type special code.
    Lets learners switch a scenario (Schalter offen/geschlossen, Betriebsart)
    instead of only dragging sliders.

  * `challenge`  — OPT-IN task-and-feedback card. Shape:
    `{prompt:str, check:"<JS body> // (s,o) -> return bool", success:str, hint:str}`.
    When present, the engine renders a challenge card (prompt + "Pruefen" button)
    that evaluates `check(s, o)` against the current state and shows `success`
    (green) or `hint` (yellow). Absent -> no card (default behaviour).

SIM_LIBRARY holds ready-made specs you can pull by name.
"""

_CSS = """
:root{--bg:#f4f6f8;--card:#fff;--ink:#1a1a1a;--muted:#5f6368;--blue:#185fa5;--green:#1d7a3f;--line:#c9ccd1}
@media(prefers-color-scheme:dark){:root{--bg:#1b1d1f;--card:#26292c;--ink:#e8eaed;--muted:#9aa0a6;--line:#3c4043}}
*{box-sizing:border-box}
body{margin:0;font-family:Arial,Helvetica,sans-serif;background:var(--bg);color:var(--ink)}
/* Kompakt-Layout: Steuerung+Ergebnisse links, Live-Ansicht rechts — die ganze
   Simulation ist auf einem ueblichen Bildschirm OHNE Scrollen sichtbar. */
.wrap{max-width:1200px;margin:0 auto;padding:10px 16px 6px}
.head{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin:0 0 10px}
h1{font-size:19px;margin:0}
.sub{color:var(--muted);font-size:13px;margin:0}
.grid{display:grid;grid-template-columns:300px minmax(0,1fr);gap:12px;align-items:start}
@media(max-width:820px){.grid{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 14px}
.card+.card{margin-top:12px}
.card h2{font-size:14px;margin:0 0 6px;color:var(--blue)}
.ctl{margin:8px 0}
.ctl label{display:flex;justify-content:space-between;font-size:13px;font-weight:bold;margin-bottom:2px;gap:8px}
.ctl .val{color:var(--blue);white-space:nowrap}
input[type=range]{width:100%;accent-color:var(--blue);margin:0}
.out{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.kpi{background:rgba(24,95,165,.08);border:1px solid var(--line);border-radius:8px;padding:5px 8px}
.kpi .k{font-size:11px;color:var(--muted)}
.kpi .v{font-size:16px;font-weight:bold}
.kpi.big{grid-column:1/3;background:rgba(29,122,63,.12)}
.kpi.big .v{color:var(--green);font-size:19px}
svg{width:100%;height:auto;display:block;max-height:56vh}
.bar{height:20px;display:flex;border-radius:6px;overflow:hidden;border:1px solid var(--line);margin-top:4px}
.seg{display:flex;align-items:center;justify-content:center;color:#fff;font-size:11px;font-weight:bold;white-space:nowrap}
.foot{color:var(--muted);font-size:11px;margin:8px 0 0;text-align:center}
.note{background:#fbeec9;color:#5a4300;border-left:4px solid #ba7517;padding:6px 10px;border-radius:4px;font-size:12px;margin-top:8px}
/* --- Manipulation: select + toggle (Schalter/Betriebsart) --- */
select{width:100%;font:inherit;font-size:13px;padding:4px 6px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--ink)}
.ctl .tgl{cursor:pointer;align-items:center}
.ctl .tgl input[type=checkbox]{width:18px;height:18px;accent-color:var(--blue);margin:0 6px 0 auto}
/* --- Zeit-Animation: Play/Pause, Tempo, Reset --- */
.animbar{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-top:8px;font-size:12px;color:var(--muted)}
.abtn{font:inherit;font-size:12px;font-weight:bold;padding:4px 10px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--ink);cursor:pointer}
.abtn:hover{border-color:var(--blue);color:var(--blue)}
.abtn:focus-visible{outline:2px solid var(--blue);outline-offset:2px}
.aspeed{display:flex;align-items:center;gap:6px}
.aspeed input[type=range]{width:86px}
.atime{margin-left:auto;font-weight:bold;color:var(--ink);font-variant-numeric:tabular-nums}
/* --- Challenge-Karte (opt-in) --- */
.card.challenge{border-color:var(--green)}
.card.challenge h2{color:var(--green)}
.cprompt{font-size:13px;margin:0 0 8px}
.cmsg:empty{display:none}
.cmsg.ok{background:rgba(29,122,63,.14);color:var(--green);border:1px solid var(--green);padding:6px 8px;border-radius:6px;font-size:12px;margin-top:8px}
.cmsg.no{background:#fbeec9;color:#5a4300;border:1px solid #ba7517;padding:6px 8px;border-radius:6px;font-size:12px;margin-top:8px}
"""

# The runtime engine is assembled by render() from a fixed BASE plus two OPTIONAL
# modules (only emitted when the spec has `animate` / `challenge`) and a TAIL.
# That way a legacy spec's HTML contains no Play button / no challenge markup at
# all — the new controls appear only where their spec field is present.
_ENGINE_BASE = """
(function(){
  function el(id){return document.getElementById(id);}
  function mk(tag,cls,html){var d=document.createElement(tag);if(cls)d.className=cls;if(html!=null)d.innerHTML=html;return d;}
  var animT=0, animSpeed=1;   // used by the time-animation module (if present)
  var cw=el('controls');
  SPEC.inputs.forEach(function(inp){
    var type=inp.type||'range';
    var d=mk('div','ctl');
    if(type==='select'){
      var opts='';(inp.options||[]).forEach(function(op){
        opts+='<option value="'+op.value+'">'+(op.label==null?op.value:op.label)+'</option>';});
      d.innerHTML='<label for="'+inp.id+'">'+inp.label+'</label>'+
        '<select id="'+inp.id+'">'+opts+'</select>';
    }else if(type==='toggle'){
      var checked=(inp.default===undefined)?true:!!inp.default;
      d.innerHTML='<label class="tgl" for="'+inp.id+'"><span>'+inp.label+'</span>'+
        '<input type="checkbox" id="'+inp.id+'"'+(checked?' checked':'')+'>'+
        '<span class="val" id="v_'+inp.id+'"></span></label>';
    }else{
      d.innerHTML='<label>'+inp.label+' <span class="val"><span id="v_'+inp.id+'"></span> '+(inp.unit||'')+'</span></label>'+
        '<input type="range" id="'+inp.id+'" min="'+inp.min+'" max="'+inp.max+'" step="'+inp.step+'" value="'+inp.default+'">';
    }
    cw.appendChild(d);
  });
  var kw=el('kpis');
  SPEC.kpis.forEach(function(k){
    var d=mk('div','kpi'+(k.big?' big':''));
    d.innerHTML='<div class="k">'+k.label+'</div><div class="v"><span id="o_'+k.id+'"></span> '+(k.unit||'')+'</div>';
    kw.appendChild(d);
  });
  function fmt(v,dec){return (typeof v==='number' && isFinite(v))?v.toFixed(dec==null?0:dec):v;}
  function state(){
    var s={};
    SPEC.inputs.forEach(function(i){
      var type=i.type||'range',elm=el(i.id);
      if(type==='select'){s[i.id]=elm.value;}
      else if(type==='toggle'){s[i.id]=elm.checked?(i.on==null?1:i.on):(i.off==null?0:i.off);}
      else{s[i.id]=+elm.value;}
    });
    return s;
  }
  function update(){
    var s=state();var o=SPEC.compute(s);
    SPEC.inputs.forEach(function(i){
      var vs=el('v_'+i.id);if(!vs)return;var type=i.type||'range';
      if(type==='toggle'){vs.textContent=el(i.id).checked?(i.onLabel||'ein'):(i.offLabel||'aus');}
      else{vs.textContent=s[i.id];}
    });
    SPEC.kpis.forEach(function(k){el('o_'+k.id).textContent=fmt(o[k.id],k.dec);});
    if(SPEC.render){try{SPEC.render(el('visual'),s,o);}catch(e){}}
    if(SPEC.animate){try{SPEC.animate(el('visual'),s,o,animT);}catch(e){}}
  }
  SPEC.inputs.forEach(function(i){var elm=el(i.id);elm.addEventListener('input',update);elm.addEventListener('change',update);});
"""

# OPTIONAL — readable-rotation helper. Emitted only with `animate`, at <script>
# scope (NOT inside the IIFE), so a SPEC.animate body may call it. Maps a real
# rotational speed (U/min) onto a calm, legible view-speed (max ~2 rev/s), so an
# author never wires raw rpm 1:1 into rotation (n≈600/min = 10 rev/s = a blur).
# The exact figure stays a KPI beside it; the spin only illustrates. t in s.
_ENGINE_HELPERS = """
  function visDeg(rpm, t){
    var rps = Math.min(2, Math.max(0.15, (rpm||0)/300));
    return (t||0) * rps * 360;
  }
"""

# OPTIONAL — time animation (Play/Pause + speed 0.1x-4x + Reset). Emitted only
# when the spec carries `animate`. Runs inside the same IIFE as BASE, so it reads
# animT/animSpeed/state/update/SPEC from the enclosing scope.
_ENGINE_ANIM = """
  (function(){
    var playing=false,raf=null,last=0;
    var bar=mk('div','animbar');
    bar.innerHTML=
      '<button type="button" id="anim_play" class="abtn" aria-pressed="false">\\u25B6 Start</button>'+
      '<button type="button" id="anim_reset" class="abtn">\\u21BB Reset</button>'+
      '<label class="aspeed">Tempo <span id="anim_spdval">1,0\\u00D7</span>'+
      '<input type="range" id="anim_speed" min="0.1" max="4" step="0.05" value="1" aria-label="Geschwindigkeit (0,1x Zeitlupe bis 4x Zeitraffer)"></label>'+
      '<span class="atime">t = <span id="anim_t">0,00</span> s</span>';
    var vis=el('visual');vis.parentNode.insertBefore(bar,vis.nextSibling);
    var play=el('anim_play');
    function frame(ts){
      if(!playing){return;}
      if(!last){last=ts;}
      var dt=(ts-last)/1000;last=ts;
      animT+=dt*animSpeed;
      el('anim_t').textContent=animT.toFixed(2).replace('.',',');
      var s=state(),o=SPEC.compute(s);
      try{SPEC.animate(el('visual'),s,o,animT);}catch(e){}
      raf=requestAnimationFrame(frame);
    }
    function start(){if(playing)return;playing=true;last=0;play.textContent='\\u23F8 Pause';play.setAttribute('aria-pressed','true');raf=requestAnimationFrame(frame);}
    function stop(){playing=false;play.textContent='\\u25B6 Start';play.setAttribute('aria-pressed','false');if(raf){cancelAnimationFrame(raf);}}
    play.addEventListener('click',function(){if(playing){stop();}else{start();}});
    el('anim_reset').addEventListener('click',function(){animT=0;el('anim_t').textContent='0,00';update();});
    el('anim_speed').addEventListener('input',function(){animSpeed=+this.value;el('anim_spdval').textContent=animSpeed.toFixed(2).replace('.',',')+'\\u00D7';update();});
  })();
"""

# OPTIONAL — challenge card (opt-in). Emitted only when the spec carries
# `challenge`. Adds a task + "Pruefen" button below the results in the left col.
_ENGINE_CHALLENGE = """
  (function(){
    var c=SPEC.challenge;
    var card=mk('div','card challenge');
    card.innerHTML='<h2>Aufgabe</h2><p class="cprompt">'+c.prompt+'</p>'+
      '<button type="button" id="ch_check" class="abtn">Prüfen</button>'+
      '<div id="ch_msg" class="cmsg" role="status" aria-live="polite"></div>';
    var results=el('kpis').parentNode;     // the Ergebnisse card
    results.parentNode.appendChild(card);  // -> stays in the left column
    el('ch_check').addEventListener('click',function(){
      var s=state(),o=SPEC.compute(s),ok=false;
      try{ok=!!c.check(s,o);}catch(e){ok=false;}
      var m=el('ch_msg');
      if(ok){m.className='cmsg ok';m.textContent=c.success||'Richtig!';}
      else{m.className='cmsg no';m.textContent=c.hint||'Noch nicht \\u2013 versuche es weiter.';}
    });
  })();
"""

_ENGINE_TAIL = """
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
  <div class="head"><h1>__TITLE__</h1><p class="sub">__SUBTITLE__</p></div>
  <div class="grid">
    <div>
      <div class="card"><h2>Steuerung</h2><div id="controls"></div></div>
      <div class="card"><h2>Ergebnisse</h2><div class="out" id="kpis"></div>__EXTRA__</div>
    </div>
    <div class="card">
      <h2>__VISUAL_TITLE__</h2>
      <div id="visual">__VISUAL__</div>
      __NOTE__
    </div>
  </div>
  <p class="foot">__FOOT__</p>
</div>
<script>
var SPEC = {
  __SPEC_BODY__
};
__ENGINE__
</script>
</body>
</html>
"""


def _spec_body(spec):
    """Build the `var SPEC = { … }` object body. `inputs`/`kpis`/`compute`/
    `render` are always emitted (as before); `animate`/`challenge` only when the
    spec carries them, so a legacy spec keeps the exact old shape."""
    import json
    fields = [
        "inputs: " + json.dumps(spec.get("inputs", []), ensure_ascii=False),
        "kpis: " + json.dumps(spec.get("kpis", []), ensure_ascii=False),
        "compute: function(s){ " + spec.get("compute", "return {};") + " }",
        "render: function(root, s, o){ " + spec.get("render", "") + " }",
    ]
    if spec.get("animate"):
        fields.append("animate: function(root, s, o, t){ " + spec["animate"] + " }")
    ch = spec.get("challenge")
    if ch:
        fields.append(
            "challenge: { prompt: " + json.dumps(ch.get("prompt", ""), ensure_ascii=False)
            + ", check: function(s, o){ " + ch.get("check", "return false;") + " }"
            + ", success: " + json.dumps(ch.get("success", ""), ensure_ascii=False)
            + ", hint: " + json.dumps(ch.get("hint", ""), ensure_ascii=False) + " }")
    return ",\n  ".join(fields)


def render(spec):
    """Return a single self-contained HTML string for the given spec."""
    note = spec.get("note", "")
    note_html = ('<div class="note">' + note + "</div>") if note else ""
    # Assemble the runtime: BASE + optional modules (only where the spec opts in).
    engine = _ENGINE_BASE
    if spec.get("animate"):
        engine += _ENGINE_ANIM
    if spec.get("challenge"):
        engine += _ENGINE_CHALLENGE
    engine += _ENGINE_TAIL
    if spec.get("animate"):
        # visDeg at <script> scope (before the IIFE) so a SPEC.animate body can call it
        engine = _ENGINE_HELPERS + engine
    html = _HTML
    repl = {
        "__TITLE__": spec.get("title", "Simulation"),
        "__SUBTITLE__": spec.get("subtitle", ""),
        "__CSS__": _CSS,
        "__ENGINE__": engine,
        "__EXTRA__": spec.get("extra", ""),
        "__VISUAL_TITLE__": spec.get("visual_title", "Ansicht (live)"),
        "__VISUAL__": spec.get("visual", ""),
        "__NOTE__": note_html,
        "__FOOT__": spec.get("foot", "Interaktive Simulation"),
        "__SPEC_BODY__": _spec_body(spec),
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
  <!-- Stromfluss: unsichtbarer Leiter-Pfad, die Punkte laufen darauf (animate). -->
  <path id="flowpath" d="M 70 90 L 540 90 L 540 250 L 70 250 Z" fill="none" stroke="none"/>
  <circle class="flowdot" r="4" fill="#f5a623"/><circle class="flowdot" r="4" fill="#f5a623"/>
  <circle class="flowdot" r="4" fill="#f5a623"/><circle class="flowdot" r="4" fill="#f5a623"/>
  <circle class="flowdot" r="4" fill="#f5a623"/><circle class="flowdot" r="4" fill="#f5a623"/>
  <circle class="flowdot" r="4" fill="#f5a623"/><circle class="flowdot" r="4" fill="#f5a623"/>
</svg>
"""

_SERIES_ANIMATE = """
var fp=root.querySelector('#flowpath'); if(!fp){return;}
var len=fp.getTotalLength();
var dots=root.querySelectorAll('.flowdot');
var v=Math.min(400,o.i*0.5);            // px/s ~ Strom (mA): mehr Strom = schneller
var off=(t*v)%len; if(off<0){off+=len;}
var n=dots.length;
for(var k=0;k<n;k++){
  var d=(off+k*len/n)%len; var p=fp.getPointAtLength(d);
  dots[k].setAttribute('cx',p.x); dots[k].setAttribute('cy',p.y);
  dots[k].style.opacity=(o.i>0.5)?1:0;   // Schalter offen / I=0 -> kein Fluss
}
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
  <!-- Stromfluss je Zweig (Punkte laufen ~ Zweigstrom) + Hauptleitung. -->
  <path id="fp1" d="M 210 70 L 210 250" fill="none" stroke="none"/>
  <path id="fp2" d="M 340 70 L 340 250" fill="none" stroke="none"/>
  <path id="fp3" d="M 470 70 L 470 250" fill="none" stroke="none"/>
  <path id="fpm" d="M 70 70 L 520 70" fill="none" stroke="none"/>
  <circle class="fd1" r="3.5" fill="#1d7a3f"/><circle class="fd1" r="3.5" fill="#1d7a3f"/><circle class="fd1" r="3.5" fill="#1d7a3f"/>
  <circle class="fd2" r="3.5" fill="#1d7a3f"/><circle class="fd2" r="3.5" fill="#1d7a3f"/><circle class="fd2" r="3.5" fill="#1d7a3f"/>
  <circle class="fd3" r="3.5" fill="#1d7a3f"/><circle class="fd3" r="3.5" fill="#1d7a3f"/><circle class="fd3" r="3.5" fill="#1d7a3f"/>
  <circle class="fdm" r="4" fill="#185fa5"/><circle class="fdm" r="4" fill="#185fa5"/>
  <circle class="fdm" r="4" fill="#185fa5"/><circle class="fdm" r="4" fill="#185fa5"/>
</svg>
"""

_PARALLEL_ANIMATE = """
function flow(sel,pathId,speed){
  var fp=root.querySelector('#'+pathId); if(!fp){return;}
  var len=fp.getTotalLength(); var dots=root.querySelectorAll(sel); var n=dots.length;
  var off=(t*speed)%len; if(off<0){off+=len;}
  for(var k=0;k<n;k++){
    var d=(off+k*len/n)%len; var p=fp.getPointAtLength(d);
    dots[k].setAttribute('cx',p.x); dots[k].setAttribute('cy',p.y);
    dots[k].style.opacity=(speed>0.5)?1:0;
  }
}
flow('.fd1','fp1',Math.min(300,o.i1*0.5));
flow('.fd2','fp2',Math.min(300,o.i2*0.5));
flow('.fd3','fp3',Math.min(300,o.i3*0.5));
flow('.fdm','fpm',Math.min(300,o.iges*0.25));
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

# --- Wechselspannung (time-based master sim): running sine + rotating phasor -- #
_WECHSEL_VISUAL = """
<svg viewBox="0 0 600 300" font-family="Arial,Helvetica,sans-serif">
  <!-- Zeiger (Phasor) links -->
  <circle cx="110" cy="150" r="70" fill="none" stroke="#c9ccd1" stroke-width="1.5"/>
  <line x1="40" y1="150" x2="180" y2="150" stroke="#c9ccd1" stroke-width="1"/>
  <line x1="110" y1="80" x2="110" y2="220" stroke="#c9ccd1" stroke-width="1"/>
  <line id="phasor" x1="110" y1="150" x2="180" y2="150" stroke="#185fa5" stroke-width="3"/>
  <circle id="phdot" cx="180" cy="150" r="5" fill="#185fa5"/>
  <circle cx="110" cy="150" r="3" fill="#888"/>
  <text x="110" y="238" text-anchor="middle" font-size="12" fill="currentColor">Zeiger (rotiert)</text>
  <!-- Oszilloskop rechts -->
  <line x1="210" y1="150" x2="590" y2="150" stroke="#888" stroke-width="1.5"/>
  <line x1="210" y1="75" x2="210" y2="225" stroke="#888" stroke-width="1.5"/>
  <line id="posamp" x1="210" y1="120" x2="590" y2="120" stroke="#ba7517" stroke-width="1" stroke-dasharray="4 4"/>
  <line id="negamp" x1="210" y1="180" x2="590" y2="180" stroke="#ba7517" stroke-width="1" stroke-dasharray="4 4"/>
  <polyline id="wave" points="" fill="none" stroke="#1d7a3f" stroke-width="2.5"/>
  <circle id="wdot" cx="590" cy="150" r="4" fill="#1d7a3f"/>
  <text x="202" y="72" text-anchor="end" font-size="12" fill="currentColor">u</text>
  <text x="588" y="168" text-anchor="end" font-size="12" fill="currentColor">t</text>
  <text id="uval" x="400" y="288" text-anchor="middle" font-size="13" font-weight="bold" fill="#1d7a3f">u(t) = 0 V</text>
</svg>
"""

_WECHSEL_COMPUTE = "var T=1000/s.f;var w=2*Math.PI*s.f;return {T:T,ueff:s.uhat/Math.SQRT2,omega:w};"

_WECHSEL_RENDER = """
var mid=150, sc=2.5;
var a=root.querySelector('#posamp'), b=root.querySelector('#negamp');
if(a){var yp=mid-s.uhat*sc;a.setAttribute('y1',yp);a.setAttribute('y2',yp);}
if(b){var yn=mid+s.uhat*sc;b.setAttribute('y1',yn);b.setAttribute('y2',yn);}
"""

_WECHSEL_ANIMATE = """
var mid=150, sc=2.5, x0=210, x1=590;
var w=2*Math.PI*s.f;
// rotierender Zeiger
var cx=110, cy=150, R=70, ang=w*t;
var px=cx+R*Math.cos(ang), py=cy-R*Math.sin(ang);
var ph=root.querySelector('#phasor'); if(ph){ph.setAttribute('x2',px.toFixed(1));ph.setAttribute('y2',py.toFixed(1));}
var pd=root.querySelector('#phdot'); if(pd){pd.setAttribute('cx',px.toFixed(1));pd.setAttribute('cy',py.toFixed(1));}
// Oszilloskop: rechte Kante = jetzt, ca. 3 Perioden im Fenster
var win=3/s.f, pxs=(x1-x0)/win, pts=[];
for(var x=x0;x<=x1;x+=3){var tt=t-(x1-x)/pxs;var u=s.uhat*Math.sin(w*tt);pts.push(x.toFixed(0)+','+(mid-u*sc).toFixed(1));}
var wv=root.querySelector('#wave'); if(wv){wv.setAttribute('points',pts.join(' '));}
var unow=s.uhat*Math.sin(w*t);
var wd=root.querySelector('#wdot'); if(wd){wd.setAttribute('cx',x1);wd.setAttribute('cy',(mid-unow*sc).toFixed(1));}
var uv=root.querySelector('#uval'); if(uv){uv.textContent='u(t) = '+unow.toFixed(1)+' V';}
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
            {"id": "schalter", "label": "Schalter", "type": "toggle", "on": 1, "off": 0,
             "default": True, "onLabel": "geschlossen", "offLabel": "offen"},
        ],
        "kpis": [
            {"id": "i", "label": "Strom I (überall gleich)", "unit": "mA", "dec": 1, "big": True},
            {"id": "rges", "label": "Gesamtwiderstand", "unit": "Ω", "dec": 0},
            {"id": "usum", "label": "Kontrolle U1+U2+U3", "unit": "V", "dec": 2},
            {"id": "u1", "label": "U1 an R1", "unit": "V", "dec": 2},
            {"id": "u2", "label": "U2 an R2", "unit": "V", "dec": 2},
            {"id": "u3", "label": "U3 an R3", "unit": "V", "dec": 2},
        ],
        "compute": "var Rg=s.r1+s.r2+s.r3;var I=(Rg>0&&s.schalter)?s.u/Rg:0;return {i:I*1000,rges:Rg,u1:I*s.r1,u2:I*s.r2,u3:I*s.r3,usum:I*Rg};",
        "visual_title": "Schaltbild (live)",
        "visual": _SERIES_VISUAL,
        "extra": '<div class="k" style="font-size:12px;color:var(--muted);margin-top:10px">Spannungsteilung</div><div class="bar" id="bar"></div>',
        "render": _SERIES_RENDER,
        "animate": _SERIES_ANIMATE,
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
        "animate": _PARALLEL_ANIMATE,
        "note": "⚠ <b>Regeln:</b> An jedem Zweig liegt die volle Spannung; die Zweigströme addieren sich zum Gesamtstrom; der kleinste Widerstand zieht den größten Strom.",
        "foot": "Interaktive Simulation · Elektrotechnik · Parallelschaltung",
    },
    "wechselspannung": {
        "title": "Wechselspannung (Sinus)",
        "subtitle": "Verändere Scheitelwert û und Frequenz f – Sinuskurve und Zeiger laufen mit (auf Start drücken).",
        "inputs": [
            {"id": "uhat", "label": "Scheitelwert û", "unit": "V", "min": 1, "max": 24, "step": 1, "default": 12},
            {"id": "f", "label": "Frequenz f", "unit": "Hz", "min": 1, "max": 100, "step": 1, "default": 25},
        ],
        "kpis": [
            {"id": "T", "label": "Periodendauer T", "unit": "ms", "dec": 1, "big": True},
            {"id": "ueff", "label": "Effektivwert U_eff", "unit": "V", "dec": 2},
            {"id": "omega", "label": "Kreisfrequenz ω", "unit": "1/s", "dec": 0},
        ],
        "compute": _WECHSEL_COMPUTE,
        "visual_title": "Zeiger & Oszilloskop (live)",
        "visual": _WECHSEL_VISUAL,
        "render": _WECHSEL_RENDER,
        "animate": _WECHSEL_ANIMATE,
        "challenge": {
            "prompt": "Stelle die Frequenz f so ein, dass die Periodendauer T = 20 ms beträgt (Netzfrequenz).",
            "check": "return Math.abs(o.T-20)<0.5;",
            "success": "Richtig! Bei f = 50 Hz ist T = 1/f = 20 ms – das ist die Netzfrequenz in Europa.",
            "hint": "Noch nicht. Es gilt T = 1/f. Für T = 20 ms = 0,02 s brauchst du f = 50 Hz.",
        },
        "note": "⚠ <b>Merke:</b> u(t) = û · sin(2·π·f·t). Die Periodendauer ist T = 1/f, der Effektivwert U_eff = û/√2 ≈ 0,707·û. Mehr Frequenz → kürzere Periode; höheres û → größere Amplitude.",
        "foot": "Interaktive Simulation · Elektrotechnik · Wechselspannung",
    },
}
