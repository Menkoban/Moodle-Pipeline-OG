#!/usr/bin/env python3
"""Konsolidiert eine Kurs-JSON zu EINEM Markdown-Dossier als NotebookLM-Quelle
(Video-/Audio-Overview). Bewusst gefiltert: keine Quiz-Loesungen/-Feedbacks,
keine verborgenen Sektionen/Aktivitaeten, keine Datei-/Link-/Organisations-
Aktivitaeten (resource/folder/url/forum/choice/feedback). Quizfragen gehen NUR
als Fragetext rein ("Pruefe dich"), damit das Video den Stoff erklaert statt
Testantworten zu verraten."""
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
    for sec in spec.get("sections", []):
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
