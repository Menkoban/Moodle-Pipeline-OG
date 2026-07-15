# moodle-adaptive-mbz-builder

> **Was dieser Skill zusätzlich kann:** Er ist der **adaptive Fork** von
> [`moodle-mbz-builder`](https://github.com/Menkoban/moodle-mbz-builder) und
> erzeugt **verzweigte Kurse mit Niveaupfaden** — Einstufung, durchlässiges
> Auf-/Absteigen, Wiederhol-Schleife und ein niveaugewichteter Dokumentations-
> Score. Er erbt die **komplette lineare Toolchain** (Kacheln, Quizze, Glossar,
> Kachelfotos, Simulationen, Formulare) — die folgende Beschreibung gilt für
> diese gemeinsame Basis. Für reine lineare Kurse den Basis-Skill nehmen.

**Didaktischer Kurs-Generator für Moodle.** Aus einer einfachen JSON-Kursdefinition
entsteht eine importfertige **Moodle-Sicherung (`.mbz`)** für Moodle 4.1+ — inklusive
selbstgezeichneter Fachdiagramme, interaktiver Simulationen, druckbarer Materialien
(PDF/PPTX), einer bearbeitbaren Vorschau und eines KI-erzeugten Recap-Videos.

Der Skill ist als [Claude-Code-Skill](https://docs.claude.com/en/docs/claude-code)
gebaut: Man beschreibt der KI einen Kurs, sie schreibt die `course.json`, zeichnet
die Diagramme und durchläuft die Bau-Pipeline. Man kann die Skripte aber auch
**eigenständig** von Hand ausführen.

---

## Was am Ende herauskommt

| Datei | Inhalt |
|---|---|
| `<kurs>.mbz` | Die Kurssicherung — in Moodle über *Kursverwaltung → Wiederherstellen* importierbar |
| `<kurs>_vorschau.html` | Interaktive Komplettvorschau im Browser (ohne Moodle) |
| `materials/` | Pro Infoblatt ein Druck-**PDF** und eine editierbare **PPTX** |
| `sims/` | Interaktive HTML-Simulationen (Schieberegler → Werte live) |
| `assets/` | Die selbstgezeichneten SVG-Diagramme |

Didaktisch folgt jeder Kurs dem **5-Ebenen-Modell nach Henning Rode**
(Lernelement → Lernbaustein → Lernabschnitt → Modul → Lernkurs) mit fester
Abschnitts-Sequenz: *Einführung → Grundlagen → Vertiefung → Anwendung →
Kurs-Recap → Glossar → Material für Lehrkräfte*.

---

## Herunterladen & installieren

Dies ist ein **[Claude-Code-Skill](https://docs.claude.com/en/docs/claude-code)** —
du klonst ihn in den Skills-Ordner deiner Claude-Code-Installation
(`~/.claude/skills/`); danach findet Claude ihn automatisch. Voraussetzung:
**Git** und **Python 3.11+**.

**Linux / macOS** (auch Windows Git-Bash):

```bash
git clone https://github.com/Menkoban/moodle-adaptive-mbz-builder ~/.claude/skills/moodle-adaptive-mbz-builder
python3 -m pip install -r ~/.claude/skills/moodle-adaptive-mbz-builder/requirements.txt
```

**Windows (PowerShell):**

```powershell
git clone https://github.com/Menkoban/moodle-adaptive-mbz-builder "$HOME\.claude\skills\moodle-adaptive-mbz-builder"
python -m pip install -r "$HOME\.claude\skills\moodle-adaptive-mbz-builder\requirements.txt"
```

> **Privates Repo?** Vorher anmelden — am einfachsten mit der GitHub-CLI:
> `gh auth login`, dann `gh repo clone Menkoban/moodle-adaptive-mbz-builder <zielpfad>`.
> Alternativ per SSH: `git clone git@github.com:Menkoban/moodle-adaptive-mbz-builder <zielpfad>`.
> Ist das Repo öffentlich, funktioniert der HTTPS-Befehl oben direkt.

**Aktualisieren:** `git -C ~/.claude/skills/moodle-adaptive-mbz-builder pull`
(Windows: `git -C "$HOME\.claude\skills\moodle-adaptive-mbz-builder" pull`).

Der Skill ist self-contained: alle Skripte finden einander relativ zum Ordner,
egal wohin er installiert wird. Kein Moodle nötig, um die `.mbz` zu bauen.

---

## Schnellstart

**1. Kursdefinition schreiben** (`course.json`, minimal):

```json
{
  "course": {"fullname": "Mein Kurs", "shortname": "MK-1", "format": "topics"},
  "sections": [
    {"name": "Einführung", "summary": "<p>Worum es geht</p>", "activities": [
      {"type": "label", "name": "Hinweis", "intro": "<p>Zuerst lesen</p>"},
      {"type": "page",  "name": "Lektion 1", "content": "<h3>Thema</h3><p>…</p>"}
    ]}
  ]
}
```

**2. Pipeline durchlaufen** (Standard für jeden Kurs):

```bash
SK=<skill-dir>/scripts

python $SK/autofit_svg.py       assets/                         # SVG-viewBox passgenau (kein Clipping)
python $SK/validate_svg.py      course.json --strict            # Diagramme prüfen (Überlappung/Textüberlauf)
python $SK/build_simulation.py  course.json -o course.sim.json  # nur falls Simulationen enthalten
python $SK/make_materials.py    course.sim.json -o course.materialized.json   # PDF/PPTX erzeugen
python $SK/build_mbz.py         course.materialized.json -o mein-kurs.mbz --wwwroot https://moodle.example.edu
python $SK/validate_mbz.py      mein-kurs.mbz                   # Archiv + XML + Querverweise prüfen
python $SK/preview_mbz.py       course.materialized.json -o mein-kurs_vorschau.html
```

Ohne Simulationen entfällt `build_simulation.py` (dann direkt `make_materials.py course.json …`).
Ohne Infoblätter (`material:true`) entfällt `make_materials.py`.

**3. In Moodle importieren:** *Kursverwaltung → Wiederherstellen → `.mbz` hochladen →*
als neuen Kurs wiederherstellen. Enthält der Kurs Glossar-Einträge, beim Restore
„Nutzerdaten einbeziehen" aktiviert lassen.

---

## Unterstützte Bausteine

**Arbeitsmaterialien:** `label`, `page`, `url`, `resource` (Datei-Download),
`folder`, `book`.
**Aktivitäten:** `assign` (Aufgabe mit Rubrik), `quiz` (Wahr/Falsch + Multiple-Choice,
je mit formativem Feedback), `forum`, `glossary`, `choice`, `feedback`, `simulation`.

Das vollständige Feld-Schema steht in
[`references/course-spec.md`](references/course-spec.md).

---

## Kernfunktionen

- **Infoblatt-Bauplan.** Jede `page` mit `"material": true` wird zum Infoblatt
  (Kopfleiste + Erklär-Fließtext + Diagramm + Stichpunkte + Merke-Box) und
  automatisch als PDF + PPTX exportiert.
- **Selbstgezeichnete Diagramme.** Beschriftete SVG-Fachdiagramme werden als
  Bilddateien eingebettet; `autofit_svg.py`/`validate_svg.py` messen echte
  Textbreiten und verhindern abgeschnittene Ränder, Überlappungen und
  Pfeil-über-Label-Defekte.
- **Interaktive Simulationen.** Wo ein Thema einen veränderlichen Zusammenhang
  hat (Schieberegler → Werte/Bild aktualisieren live), liefert `build_simulation.py`
  eine self-contained HTML-Datei (offline, CSP-sicher, Dark-Mode).
- **Formatives Feedback.** Quizze tragen Antwort-, Allgemein- und Gesamtfeedback.
- **Bearbeitbare Vorschau (Editor-Widget).** `build_editor_widget.py` erzeugt eine
  WYSIWYG-Ansicht, in der man Struktur und Inhalte direkt editiert und KI-gestützt
  überarbeiten lässt.
- **Video-Recap (Pflicht-Schritt).** Am Ende jedes Kurses wird die
  „Videozusammenfassung" über NotebookLM erzeugt (`export_course_dossier.py` →
  Video → `set_recap_video.py`). Details:
  [`references/notebooklm-video-recap.md`](references/notebooklm-video-recap.md).
- **Pflicht-Attribution.** Jeder Kurs trägt den Hinweis, dass er mit Hilfe von
  künstlicher Intelligenz und in Kooperation mit dem *Labor Didaktik der Technik*
  der *Hochschule Osnabrück* entstanden ist.

---

## Projektstruktur

```
moodle-mbz-builder/
├── SKILL.md                  # Vollständige Anleitung für die KI (Startpunkt)
├── README.md                 # Diese Bedienungsanleitung
├── requirements.txt          # Python-Abhängigkeiten
├── scripts/                  # Die Bau-Pipeline
│   ├── build_mbz.py          #   Kern-Generator (JSON → .mbz)
│   ├── make_materials.py     #   PDF/PPTX pro Infoblatt
│   ├── build_simulation.py   #   Simulations-Specs → HTML-Ressourcen
│   ├── sim_engine.py         #   generische Simulations-Engine + Bibliothek
│   ├── autofit_svg.py        #   viewBox passgenau wachsen lassen
│   ├── validate_svg.py       #   Diagramm-Lint (Clipping/Überlappung/…)
│   ├── svg_geometry.py       #   Textbreiten-Messung (Basis der SVG-Prüfung)
│   ├── validate_mbz.py       #   .mbz-Strukturprüfung
│   ├── preview_mbz.py        #   HTML-Komplettvorschau
│   ├── build_editor_widget.py#   bearbeitbare WYSIWYG-Vorschau
│   ├── export_course_dossier.py  # NotebookLM-Quelle (Markdown)
│   └── set_recap_video.py    #   Recap-Video in den Kurs einbauen
├── references/               # Nachschlagewerke
│   ├── course-design.md      #   Didaktik-Playbook (5-Ebenen-Modell, Bauplan)
│   ├── course-spec.md        #   JSON-Schema aller Felder
│   ├── activity-types.md     #   Feld-Schemata je Aktivitätstyp
│   ├── mbz-format.md         #   das .mbz-Format im Detail
│   └── notebooklm-video-recap.md  # Video-Recap-Workflow
├── assets/                   # Few-Shot-Kurs + Beispiel-Diagramme
│   ├── fewshot_bohrmaschine.json  # didaktisches Gold-Standard-Beispiel
│   └── *.svg
└── tests/                    # pytest-Suite
```

---

## Weiterführende Dokumentation

- **[`SKILL.md`](SKILL.md)** — die vollständige Anleitung (Intake, Pipeline,
  Editor-Widget-Workflow, Kompatibilitätshinweise). Startpunkt für die KI.
- **[`references/course-design.md`](references/course-design.md)** — das
  didaktische „Gehirn": 5-Ebenen-Modell, Pflicht-Sequenz, Infoblatt-Bauplan,
  Lernziel-Operatoren, SVG-Autorenregeln, Qualitäts-Checkliste.
- **[`assets/fewshot_bohrmaschine.json`](assets/fewshot_bohrmaschine.json)** — ein
  voll ausgearbeiteter Beispielkurs als Vorlage.

Tests laufen mit `python -m pytest tests/ -v`.

---

*Erstellt mit Hilfe von künstlicher Intelligenz, in Kooperation mit dem Labor
Didaktik der Technik der Hochschule Osnabrück.*
