#!/usr/bin/env python3
"""Erzeugt ein bearbeitbares Kurs-Editor-Widget (show_widget-Format) aus einer
moodle-mbz-builder Kurs-JSON. Round-Trip: Aktionen senden den vollen Kursstand
als JSON-Envelope via sendPrompt an Claude (siehe SKILL.md, Abschnitt
"Interaktiver Kurs-Editor")."""
import argparse, copy, json, os, re

MAX_WIDGET_CHARS = 300_000
RASTER = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
          ".gif": "image/gif", ".webp": "image/webp"}


def _inline_image_map(act):
    """SVG-Markup / Data-URIs fuer die Bild-Vorschau, unter _-Key (wird beim
    Senden vom Widget entfernt — Bilder reisen nie im Envelope)."""
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
            m[os.path.basename(path)] = (
                f"<img src='data:{RASTER[ext]};base64,{data}' style='max-width:100%'>")
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


TEMPLATE = r"""<h2 class="sr-only" style="position:absolute;left:-9999px">Bearbeitbarer Moodle-Kurs-Editor: Abschnitte und Aktivitaeten aendern, KI-Auftraege ausloesen, Kurs fertigstellen</h2>
<div id="mbz-editor" style="color:var(--text-primary)">
<div id="ed-head" style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:12px">
  <span id="ed-title" style="font-size:16px;font-weight:500"></span>
  <span id="dirty-badge" style="display:none;font-size:12px;background:var(--bg-warning);color:var(--text-warning);padding:2px 10px;border-radius:var(--radius)">ungespeichert</span>
  <span style="flex:1"></span>
  <button onclick="ED.send('save')"><i class="ti ti-device-floppy" aria-hidden="true" style="font-size:16px;vertical-align:-2px;margin-right:5px"></i>Speichern ↗</button>
  <button onclick="ED.send('video_recap')"><i class="ti ti-movie" aria-hidden="true" style="font-size:16px;vertical-align:-2px;margin-right:5px"></i>Video-Recap ↗</button>
  <button onclick="ED.send('finalize')"><i class="ti ti-package-export" aria-hidden="true" style="font-size:16px;vertical-align:-2px;margin-right:5px"></i>Fertigstellen → .mbz ↗</button>
</div>
<div id="ed-sections"></div>
<button style="margin-top:8px" onclick="ED.addSection()"><i class="ti ti-plus" aria-hidden="true" style="font-size:16px;vertical-align:-2px;margin-right:5px"></i>Abschnitt hinzufügen</button>
</div>
<style>
#mbz-editor .sec{border:0.5px solid var(--border);border-radius:12px;margin-bottom:8px;overflow:hidden;background:var(--surface-2)}
#mbz-editor .sec-h{display:flex;align-items:center;gap:8px;padding:9px 12px;background:var(--surface-1);cursor:pointer}
#mbz-editor .act{border-top:0.5px solid var(--border);padding:7px 12px}
#mbz-editor .act-h{display:flex;align-items:center;gap:8px;cursor:pointer;font-size:14px}
#mbz-editor textarea{width:100%;box-sizing:border-box}
#mbz-editor .mini{border:none;background:none;cursor:pointer;font-size:14px;padding:2px 5px;color:var(--text-secondary)}
#mbz-editor .mini:hover{color:var(--text-primary)}
#mbz-editor .chip{font-size:12px;background:var(--surface-1);padding:1px 9px;border-radius:var(--radius);color:var(--text-secondary)}
#mbz-editor .fld{margin:7px 0}
#mbz-editor .fld>label{display:block;font-size:12px;color:var(--text-secondary);margin-bottom:2px}
#mbz-editor .ai-row{display:flex;gap:6px;flex-wrap:wrap;margin-top:9px;padding-top:8px;border-top:0.5px dashed var(--border)}
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
function render(){document.getElementById('ed-title').textContent=(COURSE.course||{}).fullname||'Kurs';}
function addSection(){}
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
