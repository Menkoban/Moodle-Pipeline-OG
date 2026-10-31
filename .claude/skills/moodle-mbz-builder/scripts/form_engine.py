#!/usr/bin/env python3
"""Form-Engine: ausfüllbare Arbeitsblätter/Protokolle als selbst-enthaltene
HTML-Datei-Ressource (analog zur Sim-Engine).

Warum eine Datei: Moodle-Seiten sind statisch (HTMLPurifier entfernt <script>
und Formularelemente sind dort nutzlos, weil nichts gespeichert wird). Eine
echte HTML-DATEI aus dem File-Bereich darf JS ausführen — damit bekommen
Lernende Felder, in die sie WIRKLICH schreiben können, mit:

  * Autosave in localStorage (pro Feld, überlebt Seitenwechsel/Neuladen)
  * "Als Textdatei speichern" (Download der Antworten, für die Abgabe)
  * "Drucken / als PDF speichern" (Print-CSS)
  * "Zurücksetzen" (mit Rückfrage)

Spec (dict):
    {
      "title": str, "subtitle": str (optional),
      "storage_key": str (optional; default: Slug des Titels),
      "blocks": [                      # der Reihe nach gerendert
        {"heading": "Berechnung"},                      # Zwischenüberschrift
        {"html": "<table>…</table>"},                   # statischer HTML-Block
        {"field": {"id": "a1", "label": "…", "type": "text"|"textarea"|"number",
                   "unit": "cm²" (opt), "rows": 4 (textarea, opt)}},
      ],
      "note": str (optional, gelber Hinweiskasten),
      "foot": str (optional)
    }

Alle Eingabefelder sind volle Breite (lang genug für Rechenwege) — kein
unterdimensioniertes Lücken-Feld. Und sie sind IMMER LEER: keine Platzhalter,
keine Beispiel-Rechenwege im Feld — die würden den Lösungsweg vorwegnehmen.
Ein "placeholder"-Eintrag im Spec wird ignoriert. Lösungshinweise gehören,
wenn überhaupt, in die "note" oder ins Lehrkräfte-Material.
"""
import json
import re


def _slug(s):
    s = re.sub(r"[^a-zA-Z0-9]+", "_", (s or "formular").strip()).strip("_").lower()
    return s or "formular"


_CSS = """
:root{--bg:#f4f6f8;--card:#fff;--ink:#1a1a1a;--muted:#5f6368;--blue:#185fa5;
--green:#1d7a3f;--line:#c9ccd1;--accent:#1d6e56}
@media(prefers-color-scheme:dark){:root{--bg:#1b1d1f;--card:#26292c;--ink:#e8eaed;--muted:#9aa0a6;--line:#3c4043}}
*{box-sizing:border-box}
body{margin:0;font-family:Arial,Helvetica,sans-serif;background:var(--bg);color:var(--ink)}
.wrap{max-width:860px;margin:0 auto;padding:14px 16px 24px}
h1{font-size:20px;margin:0}
.sub{color:var(--muted);font-size:13px;margin:2px 0 12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 18px}
h2{font-size:15px;color:var(--accent);margin:18px 0 6px;border-bottom:1px solid var(--line);padding-bottom:4px}
h2:first-child{margin-top:0}
.blk{font-size:14px;line-height:1.5;margin:8px 0}
.blk table{border-collapse:collapse;width:100%;font-size:13px}
.blk td,.blk th{border:1px solid var(--line);padding:5px 8px;text-align:left}
.fld{margin:12px 0}
.fld label{display:block;font-size:14px;font-weight:bold;margin-bottom:4px}
.fld .unit{color:var(--blue);font-weight:bold}
.fld input[type=text],.fld input[type=number],.fld textarea{
  width:100%;font:15px/1.45 Arial,Helvetica,sans-serif;color:var(--ink);
  background:var(--card);border:1.5px solid var(--line);border-radius:8px;
  padding:10px 12px;min-height:44px}
.fld textarea{resize:vertical}
.fld input:focus,.fld textarea:focus{outline:2px solid var(--blue);border-color:var(--blue)}
.note{background:#fbeec9;color:#5a4300;border-left:4px solid #ba7517;padding:8px 12px;border-radius:4px;font-size:13px;margin-top:12px}
.bar{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-top:16px}
button{font:bold 14px Arial,Helvetica,sans-serif;border:none;border-radius:8px;
  padding:10px 16px;cursor:pointer;background:var(--blue);color:#fff}
button.secondary{background:transparent;color:var(--blue);border:1.5px solid var(--blue)}
button.danger{background:transparent;color:#a3322f;border:1.5px solid #a3322f}
.status{font-size:12px;color:var(--green);min-height:16px;margin-left:auto}
.foot{color:var(--muted);font-size:11px;margin-top:12px;text-align:center}
@media print{
  body{background:#fff}.bar,.status,.foot{display:none!important}
  .card{border:none;padding:0}
  .fld input,.fld textarea{border:1px solid #999}
}
"""

_JS = """
(function(){
  var KEY='__STORAGEKEY__';
  var fields=Array.prototype.slice.call(document.querySelectorAll('[data-field]'));
  var status=document.getElementById('status');
  function stamp(){
    var d=new Date();
    status.textContent='Automatisch gespeichert '+
      ('0'+d.getHours()).slice(-2)+':'+('0'+d.getMinutes()).slice(-2)+':'+('0'+d.getSeconds()).slice(-2);
  }
  fields.forEach(function(f){
    var k=KEY+'.'+f.getAttribute('data-field');
    try{var v=localStorage.getItem(k); if(v!==null) f.value=v;}catch(e){}
    f.addEventListener('input',function(){
      try{localStorage.setItem(k,f.value); stamp();}catch(e){}
    });
  });
  document.getElementById('btn-save').addEventListener('click',function(){
    var lines=['__TITLE__','='.repeat('__TITLE__'.length),''];
    fields.forEach(function(f){
      var label=f.getAttribute('data-label')||f.getAttribute('data-field');
      lines.push(label); lines.push('  '+(f.value||'(leer)').replace(/\\n/g,'\\n  ')); lines.push('');
    });
    var blob=new Blob([lines.join('\\r\\n')],{type:'text/plain;charset=utf-8'});
    var a=document.createElement('a');
    a.href=URL.createObjectURL(blob);
    a.download='__STORAGEKEY__'+'_antworten.txt';
    document.body.appendChild(a); a.click();
    setTimeout(function(){URL.revokeObjectURL(a.href); a.remove();},500);
  });
  document.getElementById('btn-print').addEventListener('click',function(){window.print();});
  document.getElementById('btn-reset').addEventListener('click',function(){
    if(!confirm('Wirklich alle Eingaben löschen?')) return;
    fields.forEach(function(f){
      f.value='';
      try{localStorage.removeItem(KEY+'.'+f.getAttribute('data-field'));}catch(e){}
    });
    status.textContent='Zurückgesetzt.';
  });
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
<div class="wrap">
  <h1>__TITLE__</h1>
  <p class="sub">__SUBTITLE__</p>
  <div class="card">
__BODY__
__NOTE__
    <div class="bar">
      <button id="btn-save">Als Textdatei speichern</button>
      <button id="btn-print" class="secondary">Drucken / als PDF speichern</button>
      <button id="btn-reset" class="danger">Zurücksetzen</button>
      <span class="status" id="status"></span>
    </div>
  </div>
  <p class="foot">__FOOT__ · Eingaben werden automatisch in diesem Browser gespeichert.</p>
</div>
<script>__JS__</script>
</body>
</html>
"""


def _esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def render(spec):
    """Return the self-contained HTML for a fillable worksheet spec."""
    title = spec.get("title", "Arbeitsblatt")
    storage = _slug(spec.get("storage_key") or title)
    parts = []
    
    blocks = list(spec.get("blocks") or [])
    # Convenience Fallback: Falls 'fields' auf oberster Ebene angegeben wurde
    if not blocks and spec.get("fields"):
        for fld in spec.get("fields"):
            blocks.append({"field": fld})
            
    if not blocks:
        raise ValueError(f"Formular-Fehler: Spec für '{title}' enthält weder 'blocks' noch 'fields' (leeres Formular verhindert)!")
        
    for blk in blocks:
        if "heading" in blk:
            parts.append(f"    <h2>{_esc(blk['heading'])}</h2>")
        elif "html" in blk:
            parts.append(f"    <div class='blk'>{blk['html']}</div>")
        elif "field" in blk:
            f = blk["field"]
            fid = f["id"]
            label = f.get("label", fid)
            unit = f" <span class='unit'>[{_esc(f['unit'])}]</span>" if f.get("unit") else ""
            # BEWUSST keine Platzhalter: im Feld darf NICHTS vorstehen —
            # vorgetippte Beispiel-Rechenwege nehmen die Denkleistung vorweg
            # (ein früherer "placeholder"-Parameter wird ignoriert).
            # Label darf Inline-HTML tragen (z. B. <sub>/<sup> für Indizes wie
            # A<sub>1</sub>); fürs data-label (Textdatei-Export) tag-frei.
            plain_label = re.sub(r"<[^>]+>", "", label)
            data = f"data-field=\"{_esc(fid)}\" data-label=\"{_esc(plain_label)}\""
            if f.get("type") == "textarea":
                rows = int(f.get("rows", 4))
                ctl = f"<textarea {data} rows='{rows}'></textarea>"
            else:
                typ = "number" if f.get("type") == "number" else "text"
                ctl = f"<input type='{typ}' {data}>"
            parts.append(
                f"    <div class='fld'><label>{label}{unit}</label>{ctl}</div>")
    note = spec.get("note", "")
    note_html = f"    <div class='note'>{note}</div>" if note else ""
    js = _JS.replace("__STORAGEKEY__", storage).replace(
        "__TITLE__", title.replace("'", "’").replace('"', "”"))
    html = (_HTML
            .replace("__CSS__", _CSS)
            .replace("__JS__", js)
            .replace("__TITLE__", _esc(title))
            .replace("__SUBTITLE__", _esc(spec.get("subtitle", "")))
            .replace("__BODY__", "\n".join(parts))
            .replace("__NOTE__", note_html)
            .replace("__FOOT__", _esc(spec.get("foot", "Ausfüllbares Arbeitsblatt"))))
    return html


if __name__ == "__main__":
    import sys
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    out = sys.argv[2] if len(sys.argv) > 2 else "formular.html"
    open(out, "w", encoding="utf-8").write(render(spec))
    print(f"Formular geschrieben: {out}")
