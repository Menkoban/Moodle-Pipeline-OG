#!/usr/bin/env python3
"""Indexes all Moodle courses in Moodle-Kurse and mirrors them into the Vault."""

import os
import json
import glob
import re
from pathlib import Path

WORKSPACE = r"C:\Users\User\OneDrive - HSOS\Desktop\Moodle-Kurse"
VAULT_DIR = r"C:\Users\User\OneDrive - HSOS\Desktop\Unterrichtsmaterialien\30_Moodle_Kurse_Index"

FACHBEREICHE = {
    "Elektrotechnik": [
        "elektrische-ladung", "frequenzumrichter-drehzahl", "gis1-ausschaltung",
        "gis2-serienschaltung", "gis3-wechselschaltung", "gis4-sparwechselschaltung",
        "gis5-kreuzschaltung", "induktive_naeherungsschalter", "motorschutz-diagnose",
        "ohmdemo", "parallelschaltung-widerstaende", "reihenschaltung-widerstaende",
        "wechselstrom", "wendeschuetz_schaltplaene"
    ],
    "Metalltechnik": [
        "bohrmaschine-standbohrmaschine", "kurs_drehen_fraesen", "mag_schweissen",
        "grundlagen-der-hydraulik", "hydraulik-adaptiv"
    ],
    "Gastronomie & Ernährung": [
        "kuechenhygiene-haccp"
    ],
    "IT, KI & Medien": [
        "ki-skills-fuer-einsteiger", "kuenstliche-neuronale-netze", "prompt-engineering-lehrkraefte"
    ]
}

def get_fachbereich(slug):
    for fb, slugs in FACHBEREICHE.items():
        if slug in slugs:
            return fb
    return "Allgemein"

def scan_courses():
    courses = []
    for item in os.listdir(WORKSPACE):
        p = os.path.join(WORKSPACE, item)
        if not os.path.isdir(p) or item.startswith((".", "_")) or item in ["assets", "simulationen"]:
            continue
        
        # Skip completely empty directories
        contents = os.listdir(p)
        if not contents:
            continue

        course_json = os.path.join(p, "course.json")
        data = {}
        if os.path.exists(course_json):
            try:
                with open(course_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass
        
        c_info = data.get("course", {})
        sections = data.get("sections", [])
        title = c_info.get("fullname", item.replace("-", " ").replace("_", " ").title())
        shortname = c_info.get("shortname", item)
        fmt = c_info.get("format", "tiles")
        
        # Word count
        words = 0
        act_types = {}
        for s in sections:
            for a in s.get("activities", []):
                t = a.get("type", "unknown")
                act_types[t] = act_types.get(t, 0) + 1
                for k in ["content", "intro", "summary"]:
                    if k in a:
                        words += len(re.sub(r"<[^>]+>", " ", str(a[k])).split())

        # MBZ & Preview
        mbzs = sorted(glob.glob(os.path.join(p, "*.mbz")))
        mbz_file = os.path.basename(mbzs[0]) if mbzs else "-"
        previews = sorted(glob.glob(os.path.join(p, "*_vorschau.html")), key=lambda x: (1 if "editor" in os.path.basename(x) else 0, x))
        preview_file = os.path.basename(previews[0]) if previews else "-"

        courses.append({
            "slug": item,
            "title": title,
            "shortname": shortname,
            "format": fmt,
            "fachbereich": get_fachbereich(item),
            "sections_count": len(sections),
            "words_approx": words,
            "act_types": act_types,
            "mbz": mbz_file,
            "preview": preview_file,
            "dir": p
        })
    return sorted(courses, key=lambda x: (x["fachbereich"], x["title"]))

def generate_workspace_index(courses):
    md = [
        "# 🎓 Zentraler Moodle-Kurse Katalog\n",
        f"Insgesamt **{len(courses)} Kurse** im Workspace erfasst und einsatzbereit.\n",
        "| Fachbereich | Kurs-Titel | Format | Kacheln | Wörter | Vorschau | MBZ Kurssicherung |",
        "|---|---|---|---|---|---|---|"
    ]
    for c in courses:
        if c['preview'] != "-":
            prev_link = f"[{c['preview']}]({c['slug']}/{c['preview']})"
        elif c['slug'] == "parallelschaltung-widerstaende":
            prev_link = f"[Module 1-4]({c['slug']}/modul-1-grundlagen/modul1_vorschau.html)"
        elif c['slug'] == "wendeschuetz_schaltplaene":
            prev_link = f"[Labor]({c['slug']}/index.html)"
        else:
            prev_link = "-"

        mbz_link = f"`{c['mbz']}`" if c['mbz'] != "-" else "-"
        md.append(f"| **{c['fachbereich']}** | **{c['title']}**<br>`{c['slug']}` | `{c['format']}` | {c['sections_count']} | ~{c['words_approx']} | {prev_link} | {mbz_link} |")

    out_file = os.path.join(WORKSPACE, "KURSE_INDEX.md")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print(f"OK: Workspace Index geschrieben -> {out_file}")

MOC_MAP = {
    "Elektrotechnik": "MOC_Elektrotechnik",
    "Metalltechnik": "MOC_Metalltechnik",
    "Gastronomie & Ernährung": "MOC_Gastronomie_Ernaehrung",
    "IT, KI & Medien": "MOC_IT_und_KI",
    "Allgemein": "MOC_Allgemeinbildung"
}

def generate_vault_cards(courses):
    os.makedirs(VAULT_DIR, exist_ok=True)
    
    # Root MOC in Vault
    moc = [
        "---",
        "title: \"MOC Moodle Kurse\"",
        "created: 2026-08-20",
        "updated: 2026-08-20",
        "type: moc",
        "tags: [moc, moodle, kurse, mbz]",
        "---",
        "\n# 🎓 MOC Moodle-Kurse (.mbz Katalog)\n",
        f"Zentrale Übersicht aller **{len(courses)} Moodle-Kurse** mit direktem Zugriff auf HTML-Vorschauen, MBZ-Dateien und didaktische Steckbriefe.\n",
        "## 📑 Kurse nach Fachbereich\n"
    ]
    
    current_fb = ""
    for c in courses:
        if c["fachbereich"] != current_fb:
            current_fb = c["fachbereich"]
            moc.append(f"\n### {current_fb}\n")
        
        card_name = f"Kurs_{c['slug'].replace('-', '_')}"
        moc.append(f"* **[[{card_name}|{c['title']}]]** (`{c['slug']}`) — {c['sections_count']} Kacheln, Format `{c['format']}`")

        moc_target = MOC_MAP.get(c['fachbereich'], 'MOC_Unterrichtsmaterialien')

        # Special previews
        prev_link_md = ""
        if c['preview'] != "-":
            prev_link_md = f"* **HTML-Vorschau:** [Vorschau ansehen](file:///{os.path.join(c['dir'], c['preview']).replace(chr(92), '/')})"
        elif c['slug'] == "parallelschaltung-widerstaende":
            prev_link_md = f"* **HTML-Vorschauen (Module 1-4):** [Modul 1](file:///{c['dir'].replace(chr(92), '/')}/modul-1-grundlagen/modul1_vorschau.html) | [Modul 2](file:///{c['dir'].replace(chr(92), '/')}/modul-2-berechnung/modul2_vorschau.html) | [Modul 3](file:///{c['dir'].replace(chr(92), '/')}/modul-3-messen-fehlersuche/modul3_vorschau.html) | [Modul 4](file:///{c['dir'].replace(chr(92), '/')}/modul-4-reihe-vs-parallel/modul4_vorschau.html)"
        elif c['slug'] == "wendeschuetz_schaltplaene":
            prev_link_md = f"* **Interaktive Labor-Vorschau:** [Labor öffnen](file:///{c['dir'].replace(chr(92), '/')}/index.html)"

        # Create single card note
        card_md = [
            "---",
            f"title: \"{c['title']}\"",
            f"slug: \"{c['slug']}\"",
            f"shortname: \"{c['shortname']}\"",
            f"fachbereich: \"{c['fachbereich']}\"",
            f"format: \"{c['format']}\"",
            f"kacheln: {c['sections_count']}",
            f"woerter: {c['words_approx']}",
            "type: moodle-kurs",
            "tags: [moodle, kurs, bbs]",
            "---",
            f"\n# 🎓 Moodle-Kurs: {c['title']}\n",
            f"* **Fachbereich:** [[{moc_target}|{c['fachbereich']}]]",
            f"* **Format:** `{c['format']}`",
            f"* **Umfang:** {c['sections_count']} Kacheln / ~{c['words_approx']} Wörter",
            f"* **MBZ-Datei:** `{c['mbz']}`",
            f"* **Pfad:** [Ordner öffnen](file:///{c['dir'].replace(chr(92), '/')})",
            prev_link_md,
            "\n## 🧩 Enthaltene Aktivitäten\n",
            "\n".join([f"- **{t}:** {cnt}x" for t, cnt in c["act_types"].items()]),
            "\n---\n*Zurück zur Übersicht:* [[MOC_Moodle_Kurse]]"
        ]
        # Remove empty lines from card_md
        card_md = [line for line in card_md if line]
        
        card_file = os.path.join(VAULT_DIR, f"{card_name}.md")
        with open(card_file, "w", encoding="utf-8") as f:
            f.write("\n".join(card_md) + "\n")

    moc_file = os.path.join(VAULT_DIR, "MOC_Moodle_Kurse.md")
    with open(moc_file, "w", encoding="utf-8") as f:
        f.write("\n".join(moc) + "\n")
    print(f"OK: Vault MOC und {len(courses)} Kurs-Karten geschrieben -> {VAULT_DIR}")

def main():
    courses = scan_courses()
    generate_workspace_index(courses)
    generate_vault_cards(courses)

if __name__ == "__main__":
    main()
