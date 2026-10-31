# Editable Course Widget Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ein bearbeitbares Inline-Widget (via `mcp__visualize__show_widget`) für moodle-mbz-builder-Kurse: Struktur-Editor + Feld-Editoren + KI-Assist, Round-Trip via `sendPrompt`-Envelope, `.mbz`-Build nur bei „Fertigstellen". Plus Kursdossier-Export und NotebookLM-Workflow-Doku als Folgeprojekt-Grundlage.

**Architecture:** „Fat Widget" (Ansatz A): `scripts/build_editor_widget.py` bettet die komplette Kurs-JSON in ein selbstständiges Widget-HTML ein; eine client-seitige JS-App rendert Struktur + Editoren aus diesem JSON (kein server-side HTML pro Feld → kleine Datei, keine Duplikation). Aktionen senden einen JSON-Envelope mit dem **vollen** Kursstand an Claude; Claude schreibt `course.json`, verarbeitet die Aktion und rendert das Widget neu. Spec: `docs/superpowers/specs/2026-07-04-editable-course-widget-design.md`.

**Tech Stack:** Python 3.11 (stdlib only für den Generator), Vanilla JS im Widget, pytest für Tests.

## Global Constraints

- Arbeitsverzeichnis ist das Skill-Repo: `C:\Users\User\.claude\skills\moodle-mbz-builder` (eigenes Git-Repo, Branch `master`). Alle Pfade unten relativ dazu; alle Commits dort.
- Widget-HTML: **kein** `<!DOCTYPE>`/`<html>`/`<head>`/`<body>` (show_widget-Format), **keine externen CDNs/Fonts/Icons** (Emoji/Unicode statt Tabler-Icons), Hintergrund transparent, Farben mit Fallback: `var(--text-primary, #1a1a1a)` etc.
- UI-Sprache: **Deutsch**.
- Bilder reisen **nie** als base64/SVG-Markup im Envelope: Preview-Markup wird vom Generator unter `_`-präfixierten Keys eingebettet (`_inline_images`) und beim Senden entfernt.
- Envelope-Format (Widget → Claude), exakt:
  ```
  Kurs-Editor-Aktion:
  ```json
  {"widget":"mbz-course-editor","action":"save|ai_assist|finalize|video_recap","course":{...},"target":{...}?,"instruction":"..."?}
  ```
  ```
- Tests: `python -m pytest tests/ -v` im Skill-Repo. Vor Task 2 einmal `python -m pip install pytest` (falls fehlt).
- Kurs-JSON-Schema: `references/course-spec.md` (Typen: label, page, url, resource, folder, book, assign, forum, glossary, choice, feedback, quiz).

---

### Task 1: Spike — sendPrompt→Re-Render-Loop beweisen (manuell, Orchestrator)

**Files:** keine (Widget-Code inline im Chat).

**Interfaces:**
- Produces: Bestätigung, dass (1) `sendPrompt` aus dem Widget eine Nachricht an Claude auslöst, (2) ein JSON-Codeblock darin robust ankommt, (3) ein erneuter `show_widget`-Aufruf das Widget ersetzt/neu zeigt.

**Dieser Task läuft NICHT als Subagent** — der Orchestrator (Haupt-Session) führt ihn mit dem User aus.

- [ ] **Step 1:** `mcp__visualize__read_me` mit `modules: ["interactive"]` aufrufen (still, nicht narrieren).
- [ ] **Step 2:** Mini-Widget rendern (`show_widget`, title `mbz_editor_spike`):

```html
<div style="padding:12px;border:1px solid var(--border-color,#ccc);border-radius:10px;max-width:420px">
  <b>Spike: Editor-Loop</b>
  <p style="margin:8px 0">Kurstitel:</p>
  <input id="t" value="Testkurs" style="width:100%;padding:6px">
  <button style="margin-top:10px;padding:6px 14px" onclick="
    sendPrompt('Kurs-Editor-Aktion:\n```json\n'+JSON.stringify({widget:'mbz-course-editor',action:'save',course:{course:{fullname:document.getElementById('t').value,shortname:'SPIKE'},sections:[]}})+'\n```')
  ">💾 Speichern</button>
</div>
```

- [ ] **Step 3:** User bitten, den Titel zu ändern und „Speichern" zu klicken.
- [ ] **Step 4:** Prüfen: Envelope kommt als Nachricht an, JSON parsebar → Widget mit dem NEUEN Titel erneut rendern (Loop-Beweis).
- [ ] **Step 5:** Ergebnis (funktioniert / Einschränkungen) als Kommentar in die Spec unter §8 eintragen, committen: `git commit -m "docs(spec): Spike-Ergebnis sendPrompt-Loop"`.

**Gate:** Wenn der Loop NICHT funktioniert, STOPP — zurück zum User, Design anpassen (dann ist Ansatz C/Artifact der Fallback).

---

### Task 2: Generator-Skelett `build_editor_widget.py` + Daten-Roundtrip

**Files:**
- Create: `scripts/build_editor_widget.py`
- Create: `tests/test_editor_widget.py`
- Create: `tests/conftest.py`

**Interfaces:**
- Produces: CLI `python scripts/build_editor_widget.py course.json -o editor_widget.html`; Funktion `build_widget(spec: dict, inline_images: bool = True) -> str`; eingebettetes JSON in `<script type="application/json" id="course-data">`; Konstante `MAX_WIDGET_CHARS = 300_000`; Marker-Kommentare `/*__RENDER__*/`, `/*__EDITORS__*/`, `/*__ACTIONS__*/` im JS (werden von Task 3–5 ersetzt).

- [ ] **Step 1: Failing Tests schreiben** — `tests/conftest.py`:

```python
import json, os, sys
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

@pytest.fixture
def spec():
    p = os.path.join(os.path.dirname(__file__), "..", "assets", "example_course.json")
    return json.load(open(p, encoding="utf-8"))
```

`tests/test_editor_widget.py`:

```python
import json, re
from build_editor_widget import build_widget, MAX_WIDGET_CHARS

def extract_embedded(html_out):
    m = re.search(r'<script type="application/json" id="course-data">(.*?)</script>',
                  html_out, re.S)
    assert m, "eingebettetes Kurs-JSON fehlt"
    return json.loads(m.group(1).replace("<\\/", "</"))

def test_roundtrip_embedded_json_equals_spec(spec):
    out = build_widget(spec)
    embedded = extract_embedded(out)
    # _-Keys (Preview-Anreicherung) entfernen, dann inhaltsgleich
    def strip(o):
        if isinstance(o, dict):
            return {k: strip(v) for k, v in o.items() if not k.startswith("_")}
        if isinstance(o, list):
            return [strip(v) for v in o]
        return o
    assert strip(embedded) == spec

def test_widget_has_no_doctype_and_no_cdn(spec):
    out = build_widget(spec)
    low = out.lower()
    assert "<!doctype" not in low and "<html" not in low and "<head" not in low
    assert "cdn.jsdelivr" not in low and "https://" not in low.split("sendprompt")[0]

def test_idempotent(spec):
    assert build_widget(spec) == build_widget(spec)

def test_size_fallback_disables_inline_images(spec):
    # riesiger Kurs → Generator muss ohne Inline-Bilder ausgeben
    big = json.loads(json.dumps(spec))
    filler = {"type": "page", "name": "F", "content": "<p>" + "x" * 4000 + "</p>"}
    big["sections"].append({"name": "Bulk", "activities": [dict(filler) for _ in range(120)]})
    out = build_widget(big)
    assert len(out) <= MAX_WIDGET_CHARS or "_inline_images" not in out
```

- [ ] **Step 2:** `python -m pytest tests/ -v` → FAIL (`ModuleNotFoundError: build_editor_widget`).
- [ ] **Step 3: Implementierung** — `scripts/build_editor_widget.py`:

```python
#!/usr/bin/env python3
"""Erzeugt ein bearbeitbares Kurs-Editor-Widget (show_widget-Format) aus einer
moodle-mbz-builder Kurs-JSON. Round-Trip: Aktionen senden den vollen Kursstand
als JSON-Envelope via sendPrompt an Claude (siehe SKILL.md, Abschnitt
"Interaktiver Kurs-Editor")."""
import argparse, copy, json, os, re, sys

MAX_WIDGET_CHARS = 300_000
RASTER = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
          ".gif": "image/gif", ".webp": "image/webp"}


def _inline_image_map(act):
    """SVG-Markup / Data-URIs für die Bild-Vorschau, unter _-Key (wird beim
    Senden entfernt, s. Global Constraints)."""
    import base64
    m = {}
    for img in act.get("images", []):
        path = img if isinstance(img, str) else img.get("file")
        if not path or not os.path.exists(path):
            continue
        ext = os.path.splitext(path)[1].lower()
        if ext == ".svg":
            svg = re.sub(r"<\?xml[^>]*\?>", "",
                         open(path, encoding="utf-8").read()).strip()
            m[os.path.basename(path)] = svg
        elif ext in RASTER:
            data = base64.b64encode(open(path, "rb").read()).decode()
            m[os.path.basename(path)] = f"<img src='data:{RASTER[ext]};base64,{data}' style='max-width:100%'>"
    return m


def _enrich(spec, inline_images):
    s = copy.deepcopy(spec)
    if inline_images:
        for sec in s.get("sections", []):
            for act in sec.get("activities", []):
                imap = _inline_image_map(act)
                if imap:
                    act["_inline_images"] = imap
    return s


def build_widget(spec, inline_images=True):
    enriched = _enrich(spec, inline_images)
    data = json.dumps(enriched, ensure_ascii=False).replace("</", "<\\/")
    out = TEMPLATE.replace("__COURSE_JSON__", data)
    if inline_images and len(out) > MAX_WIDGET_CHARS:
        return build_widget(spec, inline_images=False)
    return out


TEMPLATE = r"""<div id="mbz-editor" style="font-family:system-ui,Arial,sans-serif;color:var(--text-primary,#1a1a1a)">
<div id="ed-head" style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:10px">
  <b id="ed-title" style="font-size:16px"></b>
  <span id="dirty-badge" style="display:none;font-size:11px;background:#c8862a;color:#fff;padding:2px 8px;border-radius:8px">ungespeichert</span>
  <span style="flex:1"></span>
  <button class="btn" onclick="ED.send('save')">💾 Speichern</button>
  <button class="btn" onclick="ED.send('video_recap')">🎬 Video-Recap</button>
  <button class="btn btn-p" onclick="ED.send('finalize')">✅ Fertigstellen → .mbz</button>
</div>
<div id="ed-sections"></div>
<button class="btn" style="margin-top:8px" onclick="ED.addSection()">＋ Abschnitt hinzufügen</button>
</div>
<style>
#mbz-editor .btn{border:1px solid var(--border-color,#bbb);background:var(--bg-secondary,#f4f4f2);border-radius:8px;padding:5px 12px;cursor:pointer;font-size:13px}
#mbz-editor .btn:hover{filter:brightness(.96)}
#mbz-editor .btn-p{background:#2f6b4f;color:#fff;border-color:#2f6b4f}
#mbz-editor .sec{border:1px solid var(--border-color,#ccc);border-radius:10px;margin-bottom:8px;overflow:hidden;background:var(--bg-primary,#fff)}
#mbz-editor .sec-h{display:flex;align-items:center;gap:8px;padding:9px 12px;background:var(--bg-secondary,#f3f5f7);cursor:pointer}
#mbz-editor .act{border-top:1px solid var(--border-color,#e2e2e2);padding:7px 12px}
#mbz-editor .act-h{display:flex;align-items:center;gap:8px;cursor:pointer;font-size:13.5px}
#mbz-editor input,#mbz-editor textarea,#mbz-editor select{font:inherit;font-size:13px;border:1px solid var(--border-color,#bbb);border-radius:6px;padding:5px;background:var(--bg-primary,#fff);color:inherit}
#mbz-editor textarea{width:100%;box-sizing:border-box}
#mbz-editor .mini{border:none;background:none;cursor:pointer;font-size:13px;padding:2px 4px}
#mbz-editor .chip{font-size:11px;background:var(--bg-secondary,#eef0f2);padding:1px 8px;border-radius:6px}
#mbz-editor .fld{margin:6px 0}#mbz-editor .fld>label{display:block;font-size:11.5px;color:var(--text-secondary,#777);margin-bottom:2px}
#mbz-editor .ai-row{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;padding-top:6px;border-top:1px dashed var(--border-color,#ccc)}
</style>
<script type="application/json" id="course-data">__COURSE_JSON__</script>
<script>
window.ED = (function(){
const COURSE = JSON.parse(document.getElementById('course-data').textContent);
let dirty = false;
const open = {sec:{}, act:{}};
function setDirty(v){dirty=v;document.getElementById('dirty-badge').style.display=v?'inline-block':'none';}
function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function stripPrivate(o){
  if(Array.isArray(o))return o.map(stripPrivate);
  if(o&&typeof o==='object'){const r={};for(const k in o){if(!k.startsWith('_'))r[k]=stripPrivate(o[k]);}return r;}
  return o;
}
function send(action, extra){
  const env=Object.assign({widget:'mbz-course-editor',action:action,course:stripPrivate(COURSE)},extra||{});
  sendPrompt('Kurs-Editor-Aktion:\n```json\n'+JSON.stringify(env)+'\n```');
  if(action==='save')setDirty(false);
}
/*__RENDER__*/
/*__EDITORS__*/
/*__ACTIONS__*/
render();
return {send:send,addSection:addSection};
})();
</script>"""


def main():
    ap = argparse.ArgumentParser(description="Kurs-Editor-Widget aus course.json erzeugen")
    ap.add_argument("course_json")
    ap.add_argument("-o", "--output")
    args = ap.parse_args()
    spec = json.load(open(args.course_json, encoding="utf-8"))
    out_path = args.output or (os.path.splitext(args.course_json)[0] + "_editor.html")
    html_out = build_widget(spec)
    open(out_path, "w", encoding="utf-8").write(html_out)
    print(f"Editor-Widget geschrieben: {out_path} ({len(html_out)} Zeichen)")


if __name__ == "__main__":
    main()
```

Hinweis: `render`/`addSection` existieren erst nach Task 3 — für Task 2 am Ende des JS **vorläufig** einfügen: `function render(){document.getElementById('ed-title').textContent=(COURSE.course||{}).fullname||'Kurs';}` und `function addSection(){}` direkt über `render();` (Task 3 ersetzt beides).

- [ ] **Step 4:** `python -m pytest tests/ -v` → 4× PASS.
- [ ] **Step 5:** Commit: `git add scripts/build_editor_widget.py tests/ && git commit -m "feat(editor-widget): Generator-Skelett + Daten-Roundtrip (Envelope-sauber, Größen-Fallback)"`

---

### Task 3: Struktur-UI + Struktur-Operationen

**Files:**
- Modify: `scripts/build_editor_widget.py` (Marker `/*__RENDER__*/` ersetzen; Task-2-Provisorium `function render(){...}`/`function addSection(){}` löschen)
- Modify: `tests/test_editor_widget.py` (Tests ergänzen)

**Interfaces:**
- Consumes: `COURSE`, `esc`, `setDirty`, `open` aus Task 2.
- Produces: JS-Funktionen `render()`, `addSection()`, `ED_ops`-Handler via delegiertem Click-Handling; DOM: `.sec`-Blöcke mit `data-si`, `.act`-Blöcke mit `data-si`/`data-ai`; Container `div.act-body` (leer, von Task 4 gefüllt via `renderEditor(si,ai,el)`).

- [ ] **Step 1: Failing Tests ergänzen** (in `tests/test_editor_widget.py`):

```python
def test_structure_ops_present(spec):
    out = build_widget(spec)
    for marker in ["function render()", "function addSection()", "moveSection(",
                   "delSection(", "moveAct(", "delAct(", "addActivity(",
                   "data-si", "data-ai", "renderEditor("]:
        assert marker in out, f"fehlt: {marker}"

def test_all_supported_types_in_add_menu(spec):
    out = build_widget(spec)
    for t in ["label","page","url","resource","folder","book","assign",
              "forum","glossary","choice","feedback","quiz"]:
        assert f'"{t}"' in out
```

- [ ] **Step 2:** `python -m pytest tests/ -v` → 2 neue FAIL.
- [ ] **Step 3:** Marker `/*__RENDER__*/` durch folgenden Block ersetzen (und Task-2-Provisorien löschen):

```javascript
const TYPES=["label","page","url","resource","folder","book","assign","forum","glossary","choice","feedback","quiz"];
const TLABEL={label:"Textfeld",page:"Seite",url:"Link",resource:"Datei",folder:"Ordner",book:"Buch",assign:"Aufgabe",forum:"Forum",glossary:"Glossar",choice:"Abstimmung",feedback:"Feedback",quiz:"Test"};
function secs(){return COURSE.sections=COURSE.sections||[];}
function moveSection(i,d){const s=secs(),j=i+d;if(j<0||j>=s.length)return;[s[i],s[j]]=[s[j],s[i]];setDirty(true);render();}
function delSection(i){if(!confirm('Abschnitt „'+(secs()[i].name||i)+'" löschen?'))return;secs().splice(i,1);setDirty(true);render();}
function addSection(){secs().push({name:"Neuer Abschnitt",summary:"",activities:[]});open.sec[secs().length-1]=true;setDirty(true);render();}
function moveAct(si,ai,d){const a=secs()[si].activities,j=ai+d;if(j<0||j>=a.length)return;[a[ai],a[j]]=[a[j],a[ai]];setDirty(true);render();}
function delAct(si,ai){const a=secs()[si].activities;if(!confirm('Aktivität „'+(a[ai].name||a[ai].type)+'" löschen?'))return;a.splice(ai,1);setDirty(true);render();}
function addActivity(si,type){const a=secs()[si].activities=secs()[si].activities||[];
  const nu={type:type,name:"Neue "+(TLABEL[type]||type)};
  if(type==="page")nu.content="<p></p>";if(type==="quiz")nu.questions=[];
  if(type==="glossary")nu.entries=[];if(type==="choice")nu.options=[];
  if(type==="folder")nu.files=[];if(type==="book")nu.chapters=[];
  if(type==="feedback")nu.items=[];if(type==="url")nu.externalurl="https://";
  if(type==="resource")nu.file="";
  a.push(nu);open.sec[si]=true;open.act[si+"_"+(a.length-1)]=true;setDirty(true);render();}
function render(){
  document.getElementById('ed-title').textContent=(COURSE.course||{}).fullname||'Kurs';
  const root=document.getElementById('ed-sections');root.innerHTML='';
  secs().forEach(function(sec,si){
    const sd=document.createElement('div');sd.className='sec';sd.dataset.si=si;
    const hidden=sec.visible===0?' <span class="chip">verborgen</span>':'';
    sd.innerHTML='<div class="sec-h"><span class="schev">▸</span>'
      +'<input value="'+esc(sec.name||('Abschnitt '+si))+'" data-role="secname" style="flex:1;font-weight:600;border:none;background:transparent">'
      +hidden+'<span class="chip">'+(sec.activities||[]).length+' Akt.</span>'
      +'<button class="mini" data-op="secup" title="hoch">▲</button>'
      +'<button class="mini" data-op="secdown" title="runter">▼</button>'
      +'<button class="mini" data-op="secdel" title="löschen">🗑</button></div>'
      +'<div class="sec-b" style="display:'+(open.sec[si]?'block':'none')+'"></div>';
    const body=sd.querySelector('.sec-b');
    (sec.activities||[]).forEach(function(act,ai){
      const key=si+'_'+ai;
      const ad=document.createElement('div');ad.className='act';ad.dataset.si=si;ad.dataset.ai=ai;
      ad.innerHTML='<div class="act-h"><span class="achev">'+(open.act[key]?'▾':'▸')+'</span>'
        +'<span style="flex:1">'+esc(act.name||act.type)+'</span><span class="chip">'+(TLABEL[act.type]||act.type)+'</span>'
        +'<button class="mini" data-op="actup">▲</button><button class="mini" data-op="actdown">▼</button>'
        +'<button class="mini" data-op="actdel">🗑</button></div>'
        +'<div class="act-body" style="display:'+(open.act[key]?'block':'none')+'"></div>';
      if(open.act[key])renderEditor(si,ai,ad.querySelector('.act-body'));
      body.appendChild(ad);
    });
    const addRow=document.createElement('div');addRow.className='act';
    addRow.innerHTML='<select data-role="addtype">'+TYPES.map(function(t){return '<option value="'+t+'">'+TLABEL[t]+'</option>';}).join('')+'</select> '
      +'<button class="btn" data-op="actadd">＋ Aktivität</button>';
    body.appendChild(addRow);
    root.appendChild(sd);
  });
}
document.getElementById('mbz-editor').addEventListener('click',function(e){
  const op=e.target.dataset&&e.target.dataset.op;
  const secEl=e.target.closest('.sec');if(!secEl)return;
  const si=+secEl.dataset.si;const actEl=e.target.closest('.act[data-ai]');
  const ai=actEl?+actEl.dataset.ai:null;
  if(op==='secup')return moveSection(si,-1);if(op==='secdown')return moveSection(si,1);
  if(op==='secdel')return delSection(si);
  if(op==='actup')return moveAct(si,ai,-1);if(op==='actdown')return moveAct(si,ai,1);
  if(op==='actdel')return delAct(si,ai);
  if(op==='actadd')return addActivity(si,secEl.querySelector('[data-role=addtype]').value);
  if(e.target.closest('.sec-h')&&!e.target.dataset.role){open.sec[si]=!open.sec[si];return render();}
  if(e.target.closest('.act-h')){const k=si+'_'+ai;open.act[k]=!open.act[k];return render();}
});
document.getElementById('mbz-editor').addEventListener('input',function(e){
  const r=e.target.dataset&&e.target.dataset.role;
  if(r==='secname'){const si=+e.target.closest('.sec').dataset.si;secs()[si].name=e.target.value;setDirty(true);}
});
```

Direkt darunter (Übergabe an Task 4) ein Provisorium einfügen, das Task 4 ersetzt: `function renderEditor(si,ai,el){el.innerHTML='';}`

- [ ] **Step 4:** `python -m pytest tests/ -v` → alle PASS.
- [ ] **Step 5:** Commit: `git commit -am "feat(editor-widget): Struktur-UI (Akkordeon, add/del/move für Sektionen+Aktivitäten)"`

---

### Task 4: Feld-Editoren je Aktivitätstyp

**Files:**
- Modify: `scripts/build_editor_widget.py` (Marker `/*__EDITORS__*/` ersetzen; Task-3-Provisorium `function renderEditor...` löschen)
- Modify: `tests/test_editor_widget.py`

**Interfaces:**
- Consumes: `renderEditor(si,ai,el)`-Aufruf aus Task 3; `COURSE`, `esc`, `setDirty`.
- Produces: `renderEditor` vollständig; Hilfsfunktionen `fld`, `bindList`; Editier-Abdeckung: name+intro (alle), page (content, material, material_bullets, Bild-Preview aus `_inline_images`), quiz (Fragen inkl. Antworten/Feedback add/del), assign (intro, grade, duedate), glossary (entries add/del), choice (options add/del), url (externalurl), resource (file-Pfad), folder (files-Liste), book (chapters add/del), forum (forumtype), feedback (items als JSON-Textarea — bewusste v1-Vereinfachung), label (nur intro).

- [ ] **Step 1: Failing Tests ergänzen:**

```python
def test_field_editors_cover_types(spec):
    out = build_widget(spec)
    for marker in ["function renderEditor(", "edPage(", "edQuiz(", "edAssign(",
                   "edGlossary(", "edChoice(", "edBook(", "edFeedback(",
                   "material_bullets", "_inline_images", "overallfeedback"]:
        assert marker in out, f"fehlt: {marker}"
```

- [ ] **Step 2:** pytest → FAIL.
- [ ] **Step 3:** Marker `/*__EDITORS__*/` ersetzen durch:

```javascript
function fld(label,inputHtml){return '<div class="fld"><label>'+label+'</label>'+inputHtml+'</div>';}
function ta(val,rows){return '<textarea rows="'+(rows||4)+'">'+esc(val)+'</textarea>';}
function bind(el,sel,fn){el.querySelectorAll(sel).forEach(fn);}
function edPage(a,el){
  el.insertAdjacentHTML('beforeend',
    fld('Inhalt (HTML)',ta(a.content,8))
    +fld('Infoblatt (material)','<input type="checkbox" '+(a.material?'checked':'')+' data-f="material">')
    +fld('Kernpunkte (eine pro Zeile, optional)',ta((a.material_bullets||[]).join('\n'),3)));
  const tas=el.querySelectorAll('textarea');
  tas[0].addEventListener('input',function(){a.content=this.value;setDirty(true);});
  tas[1].addEventListener('input',function(){a.material_bullets=this.value.split('\n').filter(Boolean);setDirty(true);});
  el.querySelector('[data-f=material]').addEventListener('change',function(){a.material=this.checked;setDirty(true);});
  if(a._inline_images){for(const k in a._inline_images){el.insertAdjacentHTML('beforeend','<div class="fld"><label>Diagramm: '+esc(k)+' (Änderung via KI-Button)</label><div style="max-width:480px">'+a._inline_images[k]+'</div></div>');}}
}
function edQuiz(a,el){
  a.questions=a.questions||[];
  a.questions.forEach(function(q,qi){
    let inner=fld('Frage '+(qi+1)+' ('+(q.type||'multichoice')+')',ta(q.questiontext,2))
      +fld('Erklärung (generalfeedback)',ta(q.generalfeedback,2));
    if(q.type==='truefalse'){
      inner+=fld('Richtig?','<select data-q="correct"><option value="true"'+(q.correct?' selected':'')+'>Wahr</option><option value="false"'+(!q.correct?' selected':'')+'>Falsch</option></select>')
        +fld('Feedback richtig',ta(q.feedbackcorrect,2))+fld('Feedback falsch',ta(q.feedbackwrong,2));
    }else{(q.answers=q.answers||[]).forEach(function(an,ni){
      inner+='<div style="border-left:3px solid '+(an.correct?'#2f6b4f':'#a3322f')+';padding-left:8px;margin:4px 0">'
        +fld('Antwort '+(ni+1)+' <input type="checkbox" data-an="'+ni+'" '+(an.correct?'checked':'')+'> korrekt',ta(an.text,1))
        +fld('Feedback',ta(an.feedback,1))
        +'<button class="mini" data-delan="'+ni+'">🗑 Antwort</button></div>';});
      inner+='<button class="btn" data-addan="1">＋ Antwort</button>';}
    inner+='<button class="mini" data-delq="'+qi+'">🗑 Frage löschen</button><hr>';
    const qd=document.createElement('div');qd.innerHTML=inner;el.appendChild(qd);
    const tas=qd.querySelectorAll('textarea');
    tas[0].addEventListener('input',function(){q.questiontext=this.value;setDirty(true);});
    tas[1].addEventListener('input',function(){q.generalfeedback=this.value;setDirty(true);});
    if(q.type==='truefalse'){
      qd.querySelector('[data-q=correct]').addEventListener('change',function(){q.correct=this.value==='true';setDirty(true);});
      tas[2].addEventListener('input',function(){q.feedbackcorrect=this.value;setDirty(true);});
      tas[3].addEventListener('input',function(){q.feedbackwrong=this.value;setDirty(true);});
    }else{
      q.answers.forEach(function(an,ni){
        const block=qd.children[0].querySelectorAll('div[style*=border-left]')[ni];
        const t=block.querySelectorAll('textarea');
        t[0].addEventListener('input',function(){an.text=this.value;setDirty(true);});
        t[1].addEventListener('input',function(){an.feedback=this.value;setDirty(true);});
        block.querySelector('[data-an]').addEventListener('change',function(){an.correct=this.checked;setDirty(true);});
        block.querySelector('[data-delan]').addEventListener('click',function(){q.answers.splice(ni,1);setDirty(true);render();});
      });
      const addBtn=qd.querySelector('[data-addan]');
      if(addBtn)addBtn.addEventListener('click',function(){q.answers.push({text:'',correct:false,feedback:''});setDirty(true);render();});
    }
    qd.querySelector('[data-delq]').addEventListener('click',function(){a.questions.splice(qi,1);setDirty(true);render();});
  });
  el.insertAdjacentHTML('beforeend','<button class="btn" data-newq="multichoice">＋ Multiple-Choice</button> <button class="btn" data-newq="truefalse">＋ Wahr/Falsch</button>'
    +fld('Gesamtfeedback (overallfeedback, JSON)',ta(JSON.stringify(a.overallfeedback||[]),2)));
  bind(el,'[data-newq]',function(b){b.addEventListener('click',function(){
    a.questions.push(b.dataset.newq==='truefalse'?{type:'truefalse',questiontext:'<p></p>',correct:true}:{type:'multichoice',questiontext:'<p></p>',answers:[{text:'',correct:true,feedback:''}]});setDirty(true);render();});});
  el.lastElementChild.querySelector('textarea').addEventListener('input',function(){
    try{a.overallfeedback=JSON.parse(this.value);this.style.borderColor='';setDirty(true);}catch(e){this.style.borderColor='#a3322f';}});
}
function edAssign(a,el){
  el.insertAdjacentHTML('beforeend',fld('Max. Punkte','<input type="number" value="'+(a.grade||100)+'" data-f="grade">'));
  el.querySelector('[data-f=grade]').addEventListener('input',function(){a.grade=+this.value;setDirty(true);});
}
function edGlossary(a,el){
  (a.entries=a.entries||[]).forEach(function(en,ei){
    const d=document.createElement('div');
    d.innerHTML=fld('Begriff','<input value="'+esc(en.concept)+'" style="width:100%">')+fld('Definition (HTML)',ta(en.definition,2))+'<button class="mini">🗑</button><hr>';
    d.querySelector('input').addEventListener('input',function(){en.concept=this.value;setDirty(true);});
    d.querySelector('textarea').addEventListener('input',function(){en.definition=this.value;setDirty(true);});
    d.querySelector('button').addEventListener('click',function(){a.entries.splice(ei,1);setDirty(true);render();});
    el.appendChild(d);});
  const b=document.createElement('button');b.className='btn';b.textContent='＋ Begriff';
  b.addEventListener('click',function(){a.entries.push({concept:'',definition:''});setDirty(true);render();});el.appendChild(b);
}
function edChoice(a,el){
  el.insertAdjacentHTML('beforeend',fld('Optionen (eine pro Zeile)',ta((a.options||[]).join('\n'),3)));
  el.lastElementChild.querySelector('textarea').addEventListener('input',function(){a.options=this.value.split('\n').filter(Boolean);setDirty(true);});
}
function edBook(a,el){
  (a.chapters=a.chapters||[]).forEach(function(ch,ci){
    const d=document.createElement('div');
    d.innerHTML=fld('Kapitel '+(ci+1),'<input value="'+esc(ch.title)+'" style="width:100%">')+fld('Inhalt (HTML)',ta(ch.content,4))+'<button class="mini">🗑</button><hr>';
    d.querySelector('input').addEventListener('input',function(){ch.title=this.value;setDirty(true);});
    d.querySelector('textarea').addEventListener('input',function(){ch.content=this.value;setDirty(true);});
    d.querySelector('button').addEventListener('click',function(){a.chapters.splice(ci,1);setDirty(true);render();});
    el.appendChild(d);});
  const b=document.createElement('button');b.className='btn';b.textContent='＋ Kapitel';
  b.addEventListener('click',function(){a.chapters.push({title:'',content:'<p></p>'});setDirty(true);render();});el.appendChild(b);
}
function edFeedback(a,el){
  el.insertAdjacentHTML('beforeend',fld('Items (JSON — v1-Vereinfachung)',ta(JSON.stringify(a.items||[],null,1),6)));
  el.lastElementChild.querySelector('textarea').addEventListener('input',function(){
    try{a.items=JSON.parse(this.value);this.style.borderColor='';setDirty(true);}catch(e){this.style.borderColor='#a3322f';}});
}
function simpleField(a,el,key,label){
  el.insertAdjacentHTML('beforeend',fld(label,'<input value="'+esc(a[key]||'')+'" style="width:100%">'));
  el.lastElementChild.querySelector('input').addEventListener('input',function(){a[key]=this.value;setDirty(true);});
}
function renderEditor(si,ai,el){
  const a=secs()[si].activities[ai];el.innerHTML='';
  el.insertAdjacentHTML('beforeend',fld('Name','<input value="'+esc(a.name)+'" data-f="name" style="width:100%">'));
  el.querySelector('[data-f=name]').addEventListener('input',function(){a.name=this.value;setDirty(true);});
  if(a.type!=='page'){el.insertAdjacentHTML('beforeend',fld('Beschreibung / Intro (HTML)',ta(a.intro,3)));
    el.lastElementChild.querySelector('textarea').addEventListener('input',function(){a.intro=this.value;setDirty(true);});}
  if(a.type==='page')edPage(a,el);
  else if(a.type==='quiz')edQuiz(a,el);
  else if(a.type==='assign')edAssign(a,el);
  else if(a.type==='glossary')edGlossary(a,el);
  else if(a.type==='choice')edChoice(a,el);
  else if(a.type==='book')edBook(a,el);
  else if(a.type==='feedback')edFeedback(a,el);
  else if(a.type==='url')simpleField(a,el,'externalurl','Externe URL');
  else if(a.type==='resource')simpleField(a,el,'file','Dateipfad');
  else if(a.type==='folder'){el.insertAdjacentHTML('beforeend',fld('Dateipfade (einer pro Zeile)',ta((a.files||[]).join('\n'),3)));
    el.lastElementChild.querySelector('textarea').addEventListener('input',function(){a.files=this.value.split('\n').filter(Boolean);setDirty(true);});}
  else if(a.type==='forum')simpleField(a,el,'forumtype','Forumtyp (general/news/qanda/eachuser/single)');
  renderAiRow(a,el,si,ai);
}
```

- [ ] **Step 4:** pytest → PASS (Hinweis: `renderAiRow` existiert erst nach Task 5 — für Task 4 Provisorium `function renderAiRow(a,el,si,ai){}` über `render();` einfügen, Task 5 ersetzt es).
- [ ] **Step 5:** Commit: `git commit -am "feat(editor-widget): Feld-Editoren für alle 12 Aktivitätstypen"`

---

### Task 5: KI-Assist + Envelope-Aktionen

**Files:**
- Modify: `scripts/build_editor_widget.py` (Marker `/*__ACTIONS__*/` ersetzen; Task-4-Provisorium löschen)
- Modify: `tests/test_editor_widget.py`

**Interfaces:**
- Consumes: `renderAiRow(a,el,si,ai)`-Aufruf aus Task 4; `send(action, extra)` aus Task 2.
- Produces: `renderAiRow` vollständig; `AI_PRESETS`-Map; jeder Baustein bekommt Preset-Buttons + Freitext-Feld; `ai_assist`-Envelope mit `target:{section,activity}` und `instruction`.

- [ ] **Step 1: Failing Tests ergänzen:**

```python
def test_ai_assist_wiring(spec):
    out = build_widget(spec)
    for marker in ["AI_PRESETS", "renderAiRow(", '"ai_assist"',
                   "Neu schreiben", "Diagramm neu generieren", "Frage ergänzen",
                   "Rubrik generieren", "Begriffe ergänzen", "Eigener KI-Auftrag"]:
        assert marker in out, f"fehlt: {marker}"

def test_envelope_actions_present(spec):
    out = build_widget(spec)
    for a in ["'save'", "'finalize'", "'video_recap'"]:
        assert a in out
```

- [ ] **Step 2:** pytest → FAIL.
- [ ] **Step 3:** Marker `/*__ACTIONS__*/` ersetzen durch:

```javascript
const AI_PRESETS={
  page:[["✍️ Neu schreiben","Schreibe den Inhalt dieser Seite komplett neu, gleiche Kernaussagen, bessere Didaktik."],
        ["✂️ Kürzen","Kürze den Inhalt dieser Seite auf das Wesentliche (ca. 60% der Länge)."],
        ["🪄 Vereinfachen","Vereinfache die Sprache dieser Seite auf A2/B1-Niveau, kurze Sätze."],
        ["📌 Merke-Box ergänzen","Ergänze am Ende eine prägnante Merke-Box mit den 3 wichtigsten Punkten."],
        ["🖼 Diagramm neu generieren","Erzeuge das eingebettete SVG-Diagramm dieser Seite neu (klarer, korrekt beschriftet, deutsch)."]],
  quiz:[["＋ Frage ergänzen","Ergänze eine weitere lernzielorientierte Frage mit vollständigem formativem Feedback."],
        ["🎯 Distraktoren verbessern","Verbessere die falschen Antwortoptionen: plausible, auf echten Fehlvorstellungen basierende Distraktoren."],
        ["💬 Feedback schreiben","Schreibe für jede Antwort dieser Fragen ein kurzes, erklärendes Feedback."]],
  assign:[["🎯 Auftrag schärfen","Schärfe den Arbeitsauftrag: konkrete Schritte, messbares Handlungsprodukt, klare Abgabe."],
          ["📊 Rubrik generieren","Erstelle eine transparente Bewertungsrubrik (Kriterien × Niveaus) und füge sie dem Auftragstext hinzu."]],
  glossary:[["＋ Begriffe ergänzen","Ergänze 5 weitere zentrale Fachbegriffe dieses Kurses mit lernendengerechten Definitionen."]]};
function renderAiRow(a,el,si,ai){
  const row=document.createElement('div');row.className='ai-row';
  (AI_PRESETS[a.type]||[]).forEach(function(p){
    const b=document.createElement('button');b.className='btn';b.textContent=p[0];
    b.addEventListener('click',function(){send('ai_assist',{target:{section:si,activity:ai},instruction:p[1]});});
    row.appendChild(b);});
  const inp=document.createElement('input');inp.placeholder='Eigener KI-Auftrag …';inp.style.flex='1';inp.style.minWidth='160px';
  const go=document.createElement('button');go.className='btn';go.textContent='🤖 Los';
  go.addEventListener('click',function(){if(inp.value.trim())send('ai_assist',{target:{section:si,activity:ai},instruction:inp.value.trim()});});
  row.appendChild(inp);row.appendChild(go);el.appendChild(row);
}
```

- [ ] **Step 4:** pytest → alle PASS. Zusätzlich manueller Smoke: `python scripts/build_editor_widget.py assets/example_course.json -o /tmp-check_editor.html` läuft fehlerfrei; Datei löschen.
- [ ] **Step 5:** Commit: `git commit -am "feat(editor-widget): KI-Assist-Buttons je Typ + Freitext, Envelope-Aktionen komplett"`

---

### Task 6: SKILL.md — Abschnitt „Interaktiver Kurs-Editor" + Claude-Handler-Anleitung

**Files:**
- Modify: `SKILL.md` (neuer Abschnitt nach „Quick start", vor „Supported activity types")

**Interfaces:**
- Consumes: Envelope-Format (Task 2/5), CLI (Task 2).
- Produces: verbindliche Ablauf-Doku für Claude-Sessions.

- [ ] **Step 1:** Folgenden Abschnitt in `SKILL.md` einfügen:

```markdown
## Interaktiver Kurs-Editor (Widget) — Standard-Schritt vor dem Build

Nach der Kurs-Generierung (fertige `course.json`) zeige dem Autor den Kurs im
**bearbeitbaren Widget**, bevor du die `.mbz` baust:

1. Rufe einmalig `mcp__visualize__read_me` (`modules: ["interactive"]`) auf (still).
2. `python <skill-dir>/scripts/build_editor_widget.py course.json -o editor.html`
3. Rendere den Datei-Inhalt via `mcp__visualize__show_widget`
   (title: `mbz_course_editor_<shortname>`).

Der Autor editiert lokal (Struktur + Felder). Aktionen erreichen dich als
Nachricht `Kurs-Editor-Aktion:` mit einem JSON-Envelope:
`{widget:"mbz-course-editor", action, course, target?, instruction?}` —
`course` ist IMMER der vollständige aktuelle Kursstand (ohne `_`-Keys).

**Handler je `action`:**
- `save` — Envelope-`course` als `course.json` speichern (überschreiben),
  kurz plausibilisieren (JSON-Struktur, Pflichtfelder), Widget aus der neuen
  Datei regenerieren und erneut rendern. KEIN Build.
- `ai_assist` — `target` = `{section, activity}`-Indizes. Führe `instruction`
  auf genau diesem Baustein aus (Text/Fragen/SVG generieren und in die
  Kursdefinition einsetzen — bei SVG: neue Datei schreiben, Pfad in `images`
  aktuell halten). Dann wie bei `save`: speichern, regenerieren, rendern.
- `finalize` — volle Pipeline auf dem Envelope-Stand: `autofit_svg` →
  `validate_svg --strict` → `make_materials` → `build_mbz` → `validate_mbz` →
  `preview_mbz`. Deliverables (.mbz + Vorschau) an den User geben.
- `video_recap` — NotebookLM-Flow (siehe
  `references/notebooklm-video-recap.md`); falls in der Session nicht möglich
  (kein Browser-Zugriff / User nicht eingeloggt), erkläre den Stand und lass
  den Platzhalter im Kurs.

**Fehlerfälle:** Unparsebarer Envelope → letzte gültige `course.json` behalten,
Widget daraus neu rendern und den Fehler im Chat erklären. Schlägt `finalize`
in einem Validator fehl → eindeutige Defekte beheben, sonst Widget mit Hinweis
auf den betroffenen Baustein neu rendern.

Zwischenstände bauen NIE eine `.mbz` — nur `finalize` tut das.
```

- [ ] **Step 2:** Konsistenz-Check: Envelope-Felder im Abschnitt == Implementierung (Task 2/5).
- [ ] **Step 3:** Commit: `git commit -am "docs(skill): Editor-Widget-Workflow + Envelope-Handler dokumentiert"`

---

### Task 7: `export_course_dossier.py` — konsolidierter Kurs-Export für NotebookLM

**Files:**
- Create: `scripts/export_course_dossier.py`
- Create: `tests/test_export_dossier.py`

**Interfaces:**
- Produces: CLI `python scripts/export_course_dossier.py course.json -o dossier.md`; Funktion `build_dossier(spec: dict) -> str` (Markdown).
- Filterregeln (aus Spec §9): **rein:** label, page (inkl. material-Seiten), book (Kapitel), glossary (entries), assign (intro), quiz (NUR `questiontext` je Frage, als „Prüfe dich"-Liste); **raus:** Quiz-Antworten/-Feedback/-Lösungen, `visible==0`-Sektionen und -Aktivitäten, resource/folder/url/forum/choice/feedback-Aktivitäten.

- [ ] **Step 1: Failing Tests** — `tests/test_export_dossier.py`:

```python
from export_course_dossier import build_dossier

SPEC = {"course": {"fullname": "Demo"}, "sections": [
    {"name": "Einführung", "activities": [
        {"type": "page", "name": "Handlungssituation", "content": "<p>Der <b>Auftrag</b> kommt rein.</p>"},
        {"type": "quiz", "name": "Selbsttest", "questions": [
            {"type": "multichoice", "questiontext": "<p>Was gilt?</p>",
             "generalfeedback": "GEHEIM-FEEDBACK",
             "answers": [{"text": "GEHEIME-ANTWORT-A", "correct": True, "feedback": "GEHEIM"}]}]},
        {"type": "url", "name": "Externer Link", "externalurl": "https://x"},
        {"type": "glossary", "name": "Glossar", "entries": [{"concept": "Ohm", "definition": "<p>Einheit</p>"}]}]},
    {"name": "Lehrkräfte", "visible": 0, "activities": [
        {"type": "page", "name": "Leitfaden", "content": "<p>NUR-LEHRKRAFT</p>"}]}]}

def test_includes_content_and_glossary():
    d = build_dossier(SPEC)
    assert "Der Auftrag kommt rein." in d and "Ohm" in d and "Einheit" in d

def test_excludes_solutions_and_hidden():
    d = build_dossier(SPEC)
    for banned in ["GEHEIME-ANTWORT-A", "GEHEIM-FEEDBACK", "NUR-LEHRKRAFT", "https://x"]:
        assert banned not in d

def test_question_text_included_without_answers():
    d = build_dossier(SPEC)
    assert "Was gilt?" in d

def test_markdown_headings():
    d = build_dossier(SPEC)
    assert "# Demo" in d and "## Einführung" in d and "### Handlungssituation" in d
```

- [ ] **Step 2:** pytest → FAIL.
- [ ] **Step 3: Implementierung** — `scripts/export_course_dossier.py`:

```python
#!/usr/bin/env python3
"""Konsolidiert eine Kurs-JSON zu EINEM Markdown-Dossier als NotebookLM-Quelle
(Video-/Audio-Overview). Bewusst gefiltert: keine Quiz-Lösungen/-Feedbacks,
keine verborgenen Sektionen, keine Datei-/Link-/Organisations-Aktivitäten."""
import argparse, json, os, re

INCLUDE = {"label", "page", "book", "glossary", "assign", "quiz"}


def strip_html(s):
    s = re.sub(r"<(br|/p|/h[1-6]|/li|/div)[^>]*>", "\n", s or "", flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"[ \t]+", " ", s)
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def activity_md(a):
    t = a.get("type")
    parts = [f"### {a.get('name', t)}"]
    if a.get("intro"):
        parts.append(strip_html(a["intro"]))
    if t == "page":
        parts.append(strip_html(a.get("content", "")))
    elif t == "book":
        for ch in a.get("chapters", []):
            parts.append(f"#### {ch.get('title','')}")
            parts.append(strip_html(ch.get("content", "")))
    elif t == "glossary":
        for e in a.get("entries", []):
            parts.append(f"- **{e.get('concept','')}**: {strip_html(e.get('definition',''))}")
    elif t == "quiz":
        qs = [strip_html(q.get("questiontext", "")) for q in a.get("questions", [])]
        if qs:
            parts.append("Prüfe dich — diese Fragen solltest du danach beantworten können:")
            parts.extend(f"- {q}" for q in qs if q)
    return "\n\n".join(p for p in parts if p)


def build_dossier(spec):
    out = [f"# {spec.get('course', {}).get('fullname', 'Kurs')}"]
    for sec in spec.get("sections", []):
        if sec.get("visible") == 0:
            continue
        acts = [a for a in sec.get("activities", [])
                if a.get("type") in INCLUDE and a.get("visible") != 0]
        if not acts:
            continue
        out.append(f"## {sec.get('name') or 'Abschnitt'}")
        out.extend(activity_md(a) for a in acts)
    return "\n\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description="Kurs-Dossier (Markdown) für NotebookLM erzeugen")
    ap.add_argument("course_json")
    ap.add_argument("-o", "--output")
    args = ap.parse_args()
    spec = json.load(open(args.course_json, encoding="utf-8"))
    out_path = args.output or (os.path.splitext(args.course_json)[0] + "_dossier.md")
    md = build_dossier(spec)
    open(out_path, "w", encoding="utf-8").write(md)
    print(f"Dossier geschrieben: {out_path} ({len(md)} Zeichen)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4:** pytest → PASS.
- [ ] **Step 5:** Commit: `git add scripts/export_course_dossier.py tests/test_export_dossier.py && git commit -m "feat(dossier): konsolidierter Markdown-Kurs-Export für NotebookLM (ohne Lösungen/Verborgenes)"`

---

### Task 8: `references/notebooklm-video-recap.md` — Workflow-Doku (Folgeprojekt-Grundlage)

**Files:**
- Create: `references/notebooklm-video-recap.md`
- Modify: `SKILL.md` (Eintrag unter „Reference files")

**Interfaces:**
- Consumes: `export_course_dossier.py` (Task 7), `video_recap`-Action (Task 5/6).

- [ ] **Step 1:** Datei anlegen:

```markdown
# Video-Recap via NotebookLM (Best-Effort-Workflow)

Automatisiert den bislang manuellen Platzhalter „Videozusammenfassung" im
Kurs-Recap. Status: **Folgeprojekt** — vor Produktivnutzung einen manuell
begleiteten Spike fahren. Auslöser: `video_recap`-Action aus dem Editor-Widget
oder direkte User-Bitte.

## Grundsätze
- **Keine Zugangsdaten an Claude.** Der User loggt sich selbst in Chrome bei
  notebooklm.google.com ein; Claude steuert danach die eingeloggte Session
  über die Browser-Tools (claude-in-chrome). Niemals Passwörter tippen.
- **Best-Effort:** UI-Automatisierung ist fragil (Google-UI ändert sich).
  Fallback ist immer: Platzhalter bleibt im Kurs, User erzeugt das Video
  manuell.

## Ablauf
1. Dossier erzeugen: `python scripts/export_course_dossier.py course.json -o dossier.md`
   (EIN konsolidiertes Markdown — ohne Quiz-Lösungen, ohne Lehrkraft-Sektion).
2. User bitten, sich in Chrome bei NotebookLM einzuloggen; Browser-Tools laden.
3. Neues Notebook anlegen (Titel = Kurs-Shortname), `dossier.md` als Quelle
   hochladen.
4. Video-Overview anfordern (Sprache Deutsch wählen, sofern verfügbar).
5. Generierung dauert Minuten: gedulden/pollen, NICHT eng loopen.
6. MP4 herunterladen → im Kursordner ablegen.
7. In der Kurs-JSON den Recap-Platzhalter ersetzen durch
   `{"type": "resource", "name": "Videozusammenfassung", "file": "<pfad>/recap.mp4"}`
   und (falls Widget offen) das Widget regenerieren; `.mbz` erst bei
   `finalize` bauen.

## Spike-Checkliste (vor erster echter Nutzung)
- [ ] Upload eines Markdown-Dossiers funktioniert
- [ ] Video-Overview auf Deutsch verfügbar und brauchbar
- [ ] Download des MP4 automatisierbar
- [ ] Gesamtdauer akzeptabel (User informieren, dass es Minuten dauert)
```

- [ ] **Step 2:** In `SKILL.md` unter „Reference files" ergänzen:
  `- \`references/notebooklm-video-recap.md\` — Best-Effort-Workflow für die automatische Videozusammenfassung (NotebookLM); Grundlage des Folgeprojekts.`
- [ ] **Step 3:** Commit: `git commit -am "docs(notebooklm): Video-Recap-Workflow als Folgeprojekt-Grundlage"`

---

### Task 9: End-to-End-Verifikation im Chat (Orchestrator, mit User)

**Files:** keine neuen; nutzt `assets/example_course.json`.

**Dieser Task läuft NICHT als Subagent.**

- [ ] **Step 1:** `python scripts/build_editor_widget.py assets/example_course.json -o <scratchpad>/example_editor.html`
- [ ] **Step 2:** Inhalt lesen und via `show_widget` rendern (nach `read_me`, falls noch nicht geschehen).
- [ ] **Step 3:** User bitten: (a) ein Feld ändern + „💾 Speichern", (b) einen KI-Button klicken. Beide Envelopes müssen ankommen und korrekt verarbeitet werden (course.json schreiben → Widget regenerieren → neu rendern; bei ai_assist zusätzlich Instruktion ausführen).
- [ ] **Step 4:** „✅ Fertigstellen" einmal durchspielen: volle Pipeline auf dem Beispielkurs, `validate_mbz` grün.
- [ ] **Step 5:** Befund committen (falls Fixes nötig waren) + `python -m pytest tests/ -v` final grün. Abschluss-Commit: `git commit -am "test(e2e): Editor-Widget-Loop mit Beispielkurs verifiziert"`

---

## Self-Review (durchgeführt)

- **Spec-Abdeckung:** §3 Datenfluss→T2/T6; §4 Envelope→T2/T5/T6; §5 Generator/Struktur/Editoren/KI/Kopf-Aktionen/Dirty→T2–T5 (Abweichung: „🎬 Video-Recap" liegt in der Kopfleiste statt im Recap-Baustein — global immer auffindbar, bewusst); §6 SKILL.md→T6; §7 Fehler+Größe→T2 (Fallback: Inline-Bilder weglassen statt Lazy-Sektionen — einfachere, ausreichende v1-Lösung, in T2-Test verankert) +T6; §8 Tests/Spike→T1/T9 + pytest je Task; §9 Dossier+NotebookLM-Doku→T7/T8.
- **Platzhalter:** keine (Task-2/3/4-Provisorien sind explizit benannte, im Folgetask ersetzte Übergaben).
- **Typ-Konsistenz:** `build_widget(spec, inline_images)`, `send(action, extra)`, `renderEditor(si,ai,el)`, `renderAiRow(a,el,si,ai)`, `build_dossier(spec)` — in Consumes/Produces jeweils identisch verwendet.
