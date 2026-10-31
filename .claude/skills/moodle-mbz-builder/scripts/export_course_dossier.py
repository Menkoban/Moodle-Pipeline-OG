#!/usr/bin/env python3
"""Konsolidiert eine Kurs-JSON zu EINEM Markdown-Dossier als NotebookLM-Quelle
(Video-/Audio-Overview). Bewusst gefiltert: keine Quiz-Loesungen/-Feedbacks,
keine verborgenen Sektionen/Aktivitaeten, keine Datei-/Link-/Organisations-
Aktivitaeten (resource/folder/url/forum/choice/feedback). Quizfragen gehen NUR
als Fragetext rein ("Pruefe dich"), damit das Video den Stoff erklaert statt
Testantworten zu verraten.

Zusaetzlich (Strang O1): fuer jede Seite mit eingebetteten SVG-Diagrammen
(`images`-Liste, `*.svg`) wird pro Abschnitt ein Block "Abbildungen in diesem
Modul" mit einer kurzen Textbeschreibung je Diagramm angehaengt (<title>/<desc>
> sichtbare Textlabels > Dateiname). NotebookLM "sieht" das Dossier nur als
Text, kann die Diagramme also nicht selbst beschreiben — die Beschreibung gibt
dem Video etwas zum Referenzieren. Rein additiv: Kurse ohne Diagramme erzeugen
denselben Output wie zuvor."""
import argparse, json, os, re

try:  # optionale Abhaengigkeit (reportlab) - siehe build_mbz.py fuer denselben
    # Degradationspfad; ohne reportlab bleibt describe_svg() beim
    # Dateiname-Fallback statt den ganzen Export zu blockieren.
    import svg_geometry
except Exception:  # noqa: BLE001
    svg_geometry = None

INCLUDE = {"label", "page", "book", "glossary", "assign", "quiz"}
DIAGRAM_HEADING = "Abbildungen in diesem Modul"


def strip_html(s):
    s = re.sub(r"<(br|/p|/h[1-6]|/li|/div)[^>]*>", "\n", s or "", flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"[ \t]+", " ", s)
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def _svg_local(tag):
    return tag.split("}", 1)[1] if "}" in tag else tag


def describe_svg(path):
    """Kurze Textbeschreibung eines eingebetteten SVG-Diagramms fuer das
    Dossier: <title>/<desc> falls vorhanden, sonst eine Handvoll sichtbarer
    Textlabels, sonst der lesbar gemachte Dateiname. Gibt None zurueck, wenn
    die Datei fehlt (der Aufrufer laesst das Diagramm dann einfach weg —
    kein Crash, keine Erwaehnung von etwas Nicht-Existierendem)."""
    if not path or not os.path.exists(path):
        return None
    base = os.path.splitext(os.path.basename(path))[0].replace("_", " ").replace("-", " ").strip()
    if svg_geometry is None:
        return base or None
    try:
        root, _raw = svg_geometry.load(path)
    except Exception:  # noqa: BLE001 - malformed/unreadable SVG
        return base or None
    title = desc = None
    for child in root:
        name = _svg_local(child.tag)
        if name == "title" and title is None:
            title = "".join(child.itertext()).strip()
        elif name == "desc" and desc is None:
            desc = "".join(child.itertext()).strip()
    if title or desc:
        return " — ".join(p for p in (title, desc) if p)
    try:
        boxes = svg_geometry.collect_boxes(root)
    except Exception:  # noqa: BLE001
        boxes = []
    labels = []
    for b in boxes:
        if b.tag == "text" and b.label and b.label not in labels:
            labels.append(b.label)
        if len(labels) >= 6:
            break
    if labels:
        return ", ".join(labels)
    return base or None


def section_diagrams_md(acts):
    """Sammelt Diagramm-Beschreibungen aller `page`-Aktivitaeten eines
    Abschnitts (nur `.svg`-Eintraege aus `images`, andere Bildtypen sind
    i.d.R. Kachel-/Deko-Fotos, keine Diagramme). Liefert "" wenn keine
    Diagramme vorhanden sind, damit build_dossier() nichts anhaengt."""
    items = []
    for a in acts:
        if a.get("type") != "page":
            continue
        for img in a.get("images", []) or []:
            path = img if isinstance(img, str) else (img or {}).get("file")
            if not path or not str(path).lower().endswith(".svg"):
                continue
            desc = describe_svg(path)
            if not desc:
                continue
            items.append(f"- **{os.path.basename(path)}** ({a.get('name', 'Seite')}): {desc}")
    if not items:
        return ""
    return f"### {DIAGRAM_HEADING}\n\n" + "\n".join(items)


def activity_md(a):
    t = a.get("type")
    parts = [f"### {a.get('name', t)}"]
    if a.get("intro"):
        parts.append(strip_html(a["intro"]))
    if t == "page":
        parts.append(strip_html(a.get("content", "")))
    elif t == "label":
        pass  # intro ist bereits der Inhalt
    elif t == "book":
        for ch in a.get("chapters", []):
            parts.append(f"#### {ch.get('title', '')}")
            parts.append(strip_html(ch.get("content", "")))
    elif t == "glossary":
        for e in a.get("entries", []):
            parts.append(f"- **{e.get('concept', '')}**: {strip_html(e.get('definition', ''))}")
    elif t == "quiz":
        qs = [strip_html(q.get("questiontext", "")) for q in a.get("questions", [])]
        if qs:
            parts.append("Prüfe dich — diese Fragen solltest du danach beantworten können:")
            parts.extend(f"- {q}" for q in qs if q)
    return "\n\n".join(p for p in parts if p)


def build_dossier(spec):
    out = [f"# {spec.get('course', {}).get('fullname', 'Kurs')}"]
    summary = strip_html(spec.get("course", {}).get("summary", ""))
    if summary:
        out.append(summary)
    sections = spec.get("sections") or spec.get("course", {}).get("sections") or []
    for sec in sections:
        if sec.get("visible") == 0:
            continue
        acts = [a for a in sec.get("activities", [])
                if a.get("type") in INCLUDE and a.get("visible") != 0]
        if not acts:
            continue
        out.append(f"## {sec.get('name') or 'Abschnitt'}")
        sec_summary = strip_html(sec.get("summary", ""))
        if sec_summary:
            out.append(sec_summary)
        out.extend(activity_md(a) for a in acts)
        diagrams = section_diagrams_md(acts)
        if diagrams:
            out.append(diagrams)
    return "\n\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description="Kurs-Dossier (Markdown) fuer NotebookLM erzeugen")
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
