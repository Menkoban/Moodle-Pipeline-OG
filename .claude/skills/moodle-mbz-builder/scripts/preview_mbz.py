#!/usr/bin/env python3
"""Generate a self-contained, interactive HTML preview of a course defined in a
moodle-mbz-builder course JSON.

The preview renders EVERY section and activity. It is a two-level accordion:
click a section (Kachel) to expand its activity list, then click an individual
activity to expand its FULL content — pages with their HTML + embedded diagrams,
books, quizzes with answers and feedback, assignments with rubrics, forums,
glossaries, choices, feedback activities, and file resources/folders. This lets
the author review (and spot needed changes in) each activity without importing
into Moodle. Produce it alongside every .mbz.

Usage:
    python preview_mbz.py course.json [-o preview.html]

Images referenced via a page's `images` field (and @@PLUGINFILE@@/<name> in the
content) are inlined: SVG as markup, raster images as base64 data URIs, so the
file is fully self-contained.
"""
import argparse, base64, html, json, os, re, sys

ICON = {"label": "ti-tag", "page": "ti-file-text", "quiz": "ti-help-circle",
        "assign": "ti-upload", "forum": "ti-messages", "choice": "ti-chart-bar",
        "glossary": "ti-book-2", "resource": "ti-file", "folder": "ti-folder",
        "url": "ti-link", "book": "ti-book", "feedback": "ti-clipboard-check"}
TYPELABEL = {"label": "Textfeld", "page": "Seite", "quiz": "Test", "assign": "Aufgabe",
             "forum": "Forum", "choice": "Abstimmung", "glossary": "Glossar",
             "resource": "Datei", "folder": "Ordner", "url": "Link", "book": "Buch",
             "feedback": "Feedback"}
RASTER = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
          ".gif": "image/gif", ".webp": "image/webp"}


def build_image_map(act):
    m = {}
    for img in act.get("images", []):
        path = img if isinstance(img, str) else img.get("file")
        if path:
            m[os.path.basename(path)] = path
    return m


def inline_images(content, imgmap):
    def repl(m):
        name = m.group(1)
        path = imgmap.get(name)
        if path and os.path.exists(path):
            ext = os.path.splitext(path)[1].lower()
            if ext == ".svg":
                svg = re.sub(r"<\?xml[^>]*\?>", "", open(path, encoding="utf-8").read()).strip()
                return f"<div style='text-align:center;margin:10px 0;'>{svg}</div>"
            if ext in RASTER:
                data = base64.b64encode(open(path, "rb").read()).decode()
                return (f"<div style='text-align:center;margin:10px 0;'>"
                        f"<img src='data:{RASTER[ext]};base64,{data}' style='max-width:100%;height:auto;'></div>")
        return m.group(0)
    return re.sub(r"<img[^>]*?@@PLUGINFILE@@/([^'\"]+?)['\"][^>]*?>", repl, content or "")


def render_quiz(a):
    out = [f"<div class='qz-intro'>{a.get('intro','')}</div>"]
    for i, q in enumerate(a.get("questions", []), 1):
        out.append(f"<div class='qz-q'><b>Frage {i}:</b> {q.get('questiontext','')}")
        if q.get("type") == "truefalse":
            corr = "Wahr" if q.get("correct") else "Falsch"
            out.append(f"<div class='ans ok'><i class='ti ti-check'></i> Richtige Antwort: <b>{corr}</b></div>")
            if q.get("feedbackcorrect"): out.append(f"<div class='fb'>✓ {q['feedbackcorrect']}</div>")
            if q.get("feedbackwrong"): out.append(f"<div class='fb'>✗ {q['feedbackwrong']}</div>")
        else:
            for an in q.get("answers", []):
                cls = "ok" if an.get("correct") else "no"
                ic = "ti-check" if an.get("correct") else "ti-x"
                out.append(f"<div class='ans {cls}'><i class='ti {ic}'></i> {html.escape(an.get('text',''))}"
                           f"<div class='fb'>{an.get('feedback','')}</div></div>")
        if q.get("generalfeedback"):
            out.append(f"<div class='gfb'><b>Erklärung:</b> {q['generalfeedback']}</div>")
        out.append("</div>")
    if a.get("overallfeedback"):
        bands = " · ".join(f"ab {b['min']}%: {re.sub('<[^>]+>','',b['text'])}" for b in a["overallfeedback"])
        out.append(f"<div class='gfb'><b>Gesamtfeedback:</b> {bands}</div>")
    return "".join(out)


def render_feedback_items(a):
    rows = [f"<div>{a.get('intro','')}</div>"]
    for it in a.get("items", []):
        t = it.get("type")
        if t == "label":
            rows.append(f"<div>{it.get('text','')}</div>")
        elif t == "multichoice":
            opts = "".join(f"<li>{html.escape(o)}</li>" for o in it.get("options", []))
            rows.append(f"<div><b>{html.escape(it.get('name',''))}</b> (Auswahl)<ul>{opts}</ul></div>")
        else:
            rows.append(f"<div><b>{html.escape(it.get('name',''))}</b> ({t})</div>")
    return "".join(rows)


def activity_body(a):
    t = a.get("type")
    imgmap = build_image_map(a)
    if t == "label":
        return a.get("intro", "")
    if t == "page":
        return inline_images(a.get("content", ""), imgmap)
    if t == "book":
        parts = [a.get("intro", "")]
        for ch in a.get("chapters", []):
            parts.append(f"<h4>{html.escape(ch.get('title',''))}</h4>{inline_images(ch.get('content',''), imgmap)}")
        return "".join(parts)
    if t == "quiz":
        return render_quiz(a)
    if t == "feedback":
        return render_feedback_items(a)
    if t == "assign":
        return f"{a.get('intro','')}<div class='chip'>Bewertung: {a.get('grade',100)} Punkte</div>"
    if t == "forum":
        return f"{a.get('intro','')}<div class='chip'>Forumtyp: {a.get('forumtype','general')}</div>"
    if t == "choice":
        opts = "".join(f"<li>{html.escape(o)}</li>" for o in a.get("options", []))
        return f"{a.get('intro','')}<ul>{opts}</ul>"
    if t == "glossary":
        rows = "".join(f"<div class='gl'><b>{html.escape(e.get('concept',''))}</b> – {e.get('definition','')}</div>"
                       for e in a.get("entries", []))
        return f"{a.get('intro','')}{rows}"
    if t == "url":
        return f"{a.get('intro','')}<div class='chip'><i class='ti ti-link'></i> {html.escape(a.get('externalurl',''))}</div>"
    if t == "resource":
        return f"{a.get('intro','')}<div class='chip'><i class='ti ti-download'></i> {html.escape(os.path.basename(a.get('file','')))}</div>"
    if t == "folder":
        files = "".join(f"<li>{html.escape(os.path.basename(f))}</li>" for f in a.get("files", []))
        return f"{a.get('intro','')}<ul>{files}</ul>"
    return a.get("intro", "")


def render_activity(a):
    t = a.get("type")
    name = html.escape(a.get("name", t or "Aktivität"))
    icon = ICON.get(t, "ti-square")
    tlabel = TYPELABEL.get(t, t)
    body = activity_body(a)
    return (f"<div class='act'><div class='act-h'><i class='ti ti-chevron-right achev'></i>"
            f"<i class='ti {icon}' style='color:#6b7177'></i><span class='an'>{name}</span>"
            f"<span class='chip'>{tlabel}</span></div>"
            f"<div class='act-b collapsed'><div class='cc'>{body}</div></div></div>")


def build_html(spec):
    course = spec.get("course", {})
    title = html.escape(course.get("fullname", "Kurs"))
    secs = []
    n_act = 0
    for idx, s in enumerate(spec.get("sections", [])):
        acts = "".join(render_activity(a) for a in s.get("activities", []))
        n_act += len(s.get("activities", []))
        hidden = " · verborgen" if s.get("visible") == 0 else ""
        secs.append(f"<div class='sec'><div class='sec-h'><i class='ti ti-chevron-right schev'></i>"
                    f"<span class='st'>{html.escape(s.get('name') or f'Abschnitt {idx}')}{hidden}</span>"
                    f"<span class='cnt'>{len(s.get('activities', []))} Akt.</span></div>"
                    f"<div class='sec-b'>{acts}</div></div>")
    meta = (f"{len(spec.get('sections', []))} Abschnitte · {n_act} Aktivitäten · "
            f"Format: {course.get('format','topics')}")
    return TEMPLATE.format(title=title, meta=html.escape(meta), sections="".join(secs))


TEMPLATE = """<!DOCTYPE html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kursvorschau – {title}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.0.0/dist/tabler-icons.min.css">
<style>
body{{font-family:Arial,Helvetica,sans-serif;max-width:840px;margin:0 auto;padding:18px;background:#faf9f5;color:#1a1a1a}}
.ti{{font-style:normal}}
h1{{font-size:20px;font-weight:500;margin-bottom:2px}}.lead{{font-size:13px;color:#5f5e5a;margin-bottom:14px}}
.sec{{border:1px solid rgba(0,0,0,.12);border-radius:12px;background:#fff;margin-bottom:10px;overflow:hidden}}
.sec-h{{display:flex;align-items:center;gap:10px;padding:12px 14px;cursor:pointer;background:#f3f5f7}}
.sec-h:hover{{background:#eaedf0}}
.st{{font-weight:500;flex:1}}.cnt{{font-size:12px;color:#888}}
.sec-b{{padding:0 14px}}.sec-b.collapsed{{display:none}}
.act{{border-top:1px solid rgba(0,0,0,.08)}}
.act-h{{display:flex;align-items:center;gap:8px;padding:10px 0;cursor:pointer;font-size:14px;font-weight:500}}
.act-h:hover .an{{text-decoration:underline}}
.an{{flex:1}}
.chip{{display:inline-block;font-size:12px;padding:2px 9px;border-radius:6px;background:#eef0f2;color:#3c3c3c;margin:0 0 0 4px}}
.act-b{{padding:2px 0 12px 26px}}.act-b.collapsed{{display:none}}
.cc{{font-size:13px;line-height:1.55;color:#333}}
.cc table{{border-collapse:collapse;font-size:12px;margin:6px 0;width:100%}}.cc td,.cc th{{border:1px solid rgba(0,0,0,.15);padding:4px 7px;text-align:left}}
.cc ul,.cc ol{{margin:4px 0;padding-left:18px}}.cc svg,.cc img{{max-width:100%;height:auto}}
.qz-q{{margin:8px 0;padding:8px;border:1px solid rgba(0,0,0,.12);border-radius:6px}}
.ans{{display:flex;gap:6px;align-items:flex-start;margin:4px 0;font-size:12.5px}}
.ans.ok{{color:#1d6e56}}.ans.no{{color:#a3322f}}.fb{{font-size:12px;color:#777;margin-left:18px}}
.gfb{{font-size:12px;background:#f3f3ef;padding:6px 8px;border-radius:6px;margin-top:4px}}
.gl{{padding:3px 0;border-bottom:1px dotted rgba(0,0,0,.15)}}
.achev,.schev{{transition:transform .15s;color:#6b7177}}
</style></head><body>
<h1>{title}</h1><div class="lead">{meta} · Kachel anklicken → Aktivitätsliste; Aktivität anklicken → voller Inhalt.</div>
{sections}
<script>
document.querySelectorAll('.sec-h').forEach(function(h){{
  var b=h.nextElementSibling,c=h.querySelector('.schev');
  if(c)c.style.transform='rotate(90deg)';
  h.addEventListener('click',function(){{var col=b.classList.toggle('collapsed');if(c)c.style.transform=col?'rotate(0deg)':'rotate(90deg)';}});
}});
document.querySelectorAll('.act-h').forEach(function(h){{
  var b=h.nextElementSibling,c=h.querySelector('.achev');
  h.addEventListener('click',function(){{var op=!b.classList.toggle('collapsed');if(c)c.style.transform=op?'rotate(90deg)':'rotate(0deg)';}});
}});
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser(description="Render an interactive HTML preview of a course JSON.")
    ap.add_argument("course_json")
    ap.add_argument("-o", "--output")
    args = ap.parse_args()
    spec = json.load(open(args.course_json, encoding="utf-8"))
    out = args.output or (os.path.splitext(args.course_json)[0] + "_vorschau.html")
    open(out, "w", encoding="utf-8").write(build_html(spec))
    n = sum(len(s.get("activities", [])) for s in spec.get("sections", []))
    print(f"Vorschau geschrieben: {out}  ({len(spec.get('sections', []))} Abschnitte, {n} Aktivitäten)")


if __name__ == "__main__":
    main()
