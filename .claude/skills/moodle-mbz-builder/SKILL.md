---
name: moodle-mbz-builder
description: >-
  Generates valid Moodle backup files (.mbz) for Moodle 4.1+ from a simple JSON
  course definition — including sections, resources (label, page, url, file,
  folder, book) and activities (assign, quiz with questions, forum, glossary,
  choice, feedback), with real file attachments. Use this skill whenever the
  user wants to create, build, generate, or assemble a Moodle course/backup/
  .mbz file, restore-ready Moodle content, a "Sicherung" / "Kurssicherung", or
  asks to turn course material into something importable into Moodle — even if
  they don't say ".mbz" explicitly. Also use it to add individual learning
  materials ("Arbeitsmaterialien") or activities ("Aktivitäten") into a Moodle
  backup.
---

# Moodle .mbz Builder

Generate restore-ready Moodle 2 backup files (`.mbz`) for **Moodle 4.1+** from a
high-level JSON course definition. No Moodle installation is required to build
the file; you import it via *Course administration → Restore* in Moodle.

A `.mbz` is just a **gzip-compressed tar archive** of XML files (the "moodle2"
backup format). The hard part is that the XML files cross-reference each other
through several parallel ID spaces and a dozen near-empty-but-required helper
files. This skill's generator handles all of that for you.

## When to use this

Trigger this skill when the user wants to **produce a Moodle course or backup
file** they can restore/import — phrasings like "erstelle eine mbz", "generiere
einen Moodle-Kurs", "Kurssicherung bauen", "create a Moodle backup", "package
this material for Moodle", or "add these activities into a Moodle course". If
they only want to *understand* an existing `.mbz`, read `references/mbz-format.md`
instead of running the generator.

## Where finished courses live — output folder & reference library (project convention)

**Collection folder (Sammelordner):**
`C:\Users\User\OneDrive - HSOS\Desktop\Moodle-Kurse`
The path **contains a space** — always quote it in shell commands
(`"C:/Users/User/OneDrive - HSOS/Desktop/Moodle-Kurse"`).

**One subfolder per course**, named after a slug of the course (the `.mbz`
basename / course shortname). At the **end of every build**, copy the complete
package into that subfolder — this is a standard delivery step, not optional:

```
Moodle-Kurse\
  <kurs-slug>\
    <kurs-slug>.mbz            ← the backup to import into Moodle
    <kurs>_vorschau.html       ← the HTML preview
    materials\                 ← auto-generated PDF + PPTX (+ PNG)
    assets\                    ← the source SVG diagrams
    course.json                ← source definition, with RELATIVE assets/… image paths
```

Write the stored `course.json` with **relative** `assets/<file>.svg` image paths
(not absolute scratch paths) and copy `assets/` next to it, so every course
folder is **self-contained and rebuildable**: running the pipeline with that
folder as the working directory reproduces the `.mbz`. You may build in a
scratch/working directory first; only the final deliverables get copied here.

**This folder is also a REFERENCE library (knowledge extension).** Before
authoring a new course, list `"…/Moodle-Kurse"` and — when relevant — read the
`course.json` (and skim the `_vorschau.html`) of the courses already there. Treat
them as worked examples **alongside** `assets/fewshot_bohrmaschine.json`: match
the structure, wording, section sequence, Infoblatt/HTML styling, SVG conventions
and depth the user has already established. The built-in few-shot sets the
baseline; the user's own courses in this folder refine and extend it. If the
folder is empty, fall back to the built-in few-shot only.

## Authoring high-quality courses — read this first for real courses

Producing a *structurally valid* `.mbz` is the easy part. Producing a **didactically
strong, fully fleshed-out course** — especially for **vocational education
(berufliche Bildung)** — is the goal. Do not emit thin, placeholder content.

**Before writing the course JSON, read `references/course-design.md`** (the
didactic playbook) and open `assets/fewshot_bohrmaschine.json` as a worked
gold-standard example. The course-design playbook is built on the **5-level
structure model** (Lernelement → Lernbaustein → Lernabschnitt → Lerneinheit/Modul
→ Lernkurs) with a fixed section sequence. The short version of the method:

1. **Intake first — ASK the user before building (Kurs-Steckbrief).** Before
   writing any course JSON, run a short structured intake and *ask* the briefing
   questions that make sense for this request. **Always as a selection menu:** each
   point is a question with **2–4 concrete suggested options**, the best one marked
   `(empfohlen)` — the user just clicks, and the built-in free-text option covers
   any custom answer; use **multi-select** where several answers can apply (e.g.
   activity types). Batch 2–4 questions at a time via the clarifying-questions UI,
   **skip** anything already given or with a safe obvious default, and never
   interrogate. Cover, where relevant:
   - **Thema & Curriculum:** topic, trade/Fach + **Lernfeld**, position in the curriculum;
   - **Zielgruppe & Vorwissen:** Bildungsgang, Ausbildungsjahr, prior knowledge, Sprachniveau;
   - **Umfang & Einsatzform:** time budget (one module ≈ 2 Unterrichtsstunden), single module vs. Lernkurs, Präsenz / Flipped / Selbstlernen;
   - **Schwerpunkt:** theory / calculation / measuring / assembly …;
   - **Handlungssituation & Handlungsprodukt:** real operational context + what learners produce (offer to invent a realistic one);
   - **Lernziele:** given by the user, or "please derive";
   - **Verbindliche Fachdaten:** formulas, values, norms, safety facts, correct worked examples;
   - **Vorhandenes Material:** own scripts/PDFs/images to embed (paths); which diagrams to draw; photos (placeholders only — cannot generate);
   - **Aktivitäten & Prüfung:** activity types, formative vs. graded, rubric wishes;
   - **Struktur & Kachelzahl (IMMER fragen):** wie viele inhaltliche
     Kacheln/Lernabschnitte der Kurs bekommen soll — als Auswahlfrage mit
     konkreten, aus Thema + Zeitbudget abgeleiteten Vorschlägen, z. B.
     „5 Kacheln: Einstieg / Theorie / Praxis / Anwendung / Recap (empfohlen)"
     vs. kompakter (3–4) vs. ausführlicher (6–7). Die Pflicht-Sequenz unten
     bleibt das Gerüst; die Kachelzahl entscheidet, wie fein Grundlagen/
     Vertiefung aufgeteilt werden. Glossar + Lehrkraft-Sektion zählen extra;
   - **Stil & Metadaten:** Du/Sie, course name + **unique shortname**, category, format.
   Then apply the playbook defaults below for everything the user leaves open —
   ask to sharpen the fit, don't block on it.
   **Vorschlags-Steckbrief (PFLICHT, vor der Content-Produktion):** Lege dem
   Autor nach dem Intake einen konkreten Kursvorschlag zur Bestätigung vor —
   benannte Kacheln mit je einem Satz Inhalt, geplante Aktivitäten je Kachel
   (Infoblätter/Quiz/Auftrag/Simulation/Formular), **Kachelfoto-Motiv je
   Kachel** (ein Motiv-Stichwort pro Kachel, siehe „Kachel-Bilder"),
   Handlungssituation in 2 Sätzen und die Lernziele. Erst wenn der Autor
   bestätigt (oder gezielt umbaut), wird Content geschrieben und gebaut.
2. **Define competence-based learning outcomes:** "Die Lernenden können
   [observable verb] [content] [context/criterion]" — never "kennen/verstehen".
3. **Follow the fixed Lernabschnitt sequence:** Einführung → Grundlagen →
   Vertiefung → Anwendung/Handlungsprodukt → Kurs-Recap → Glossar → Material für
   Lehrkräfte (the complete-action model / AVIVA is the *rationale* behind the
   Anwendung section). Anchor everything in one **Handlungssituation**.
4. **Build each Infoblatt to the Bauplan:** intro + explanatory prose + an
   embedded self-drawn SVG diagram + key points + a Merke box; mark it
   `material: true` for auto PDF/PPTX.
5. **Write rich content** with the patterns in `course-design.md`: case-based
   intro, info sheets for input, a practice assignment with steps + a transparent
   rubric, a **formative self-test with per-answer feedback**, reflection + transfer.
6. **Generate materials → build → validate → preview → restore.**

**Pflicht-Attribution (jeder Kurs):** Jeder generierte Kurs trägt den
Entstehungs-Hinweis „mit Hilfe von künstlicher Intelligenz erstellt, in
Kooperation mit dem Labor Didaktik der Technik der Hochschule Osnabrück" — in
`course.summary` **und** als „Hinweis zur Entstehung"-`label` am Ende des
Kurs-Recap. **Zusätzlich hängt `build_mbz.py` den Satz automatisch als
Seitenfuß an das Ende JEDER Seite und jedes Buch-Kapitels** (auch in Vorschau
und Druck-PDFs; idempotent, Override/Abschalten via `course.attribution`).
Exakter Wortlaut + HTML in `references/course-design.md`, Abschnitt 3
(„Pflicht-Attribution"). Nie weglassen.

When the user asks for a vocational course "step by step", walk these phases and
produce content at the level of the few-shot — not a shell.

## The core question: do you need per-type templates?

**~90% of every backup is generic** and does not depend on the activity type:
`moodle_backup.xml`, `files.xml`, all `course/*` and `sections/*` files, and per
activity the wrapper files `module.xml`, `inforef.xml`, `roles.xml`, `grades.xml`,
`grade_history.xml`, `calendar.xml`, `filters.xml`. Only **one** file per
activity is type-specific: the main `<modulename>.xml` (e.g. `page.xml`,
`quiz.xml`).

So: you need exactly **one small template per activity type**, for that single
file. This generator already **bundles** those templates for the common types
(see below). You do **not** need to supply any templates yourself — you only
write a JSON course definition. You only need a *new* template if you want an
activity type that isn't yet covered (see "Extending" below).

## Setup (once, after copying the skill)

The skill is self-contained: everything travels in this folder. Install the
Python dependencies once so the material pipeline **and the automatic diagram
quality check** work:

```bash
python -m pip install -r <skill-dir>/requirements.txt
```

Diagram QA is built in and runs automatically — `make_materials.py` and
`build_mbz.py` lint every embedded SVG (clipping, overlaps, `<tspan>` traps, tofu
glyphs, lines crossing labels, text spilling out of its box) on every run, so a
broken diagram cannot ship unnoticed. If the dependencies above are missing,
`build_mbz.py` still builds but prints `NOTE: SVG diagram check skipped` — install
them to keep the check active. No paths are hard-coded; the scripts find each
other relative to the skill folder wherever it is installed.

## Quick start

1. Write a course definition JSON. Minimal example:

```json
{
  "course": {"fullname": "My Course", "shortname": "MYC", "format": "topics"},
  "sections": [
    {"name": "Intro", "summary": "<p>Welcome</p>", "activities": [
      {"type": "label", "name": "Note", "intro": "<p>Read this first</p>"},
      {"type": "page", "name": "Lesson 1", "content": "<h3>Topic</h3><p>...</p>"}
    ]}
  ]
}
```

2. **Auto-generate downloadable materials** (PDF + PowerPoint per Infoblatt) and
   wire them into the course. Mark each Infoblatt page with `"material": true`
   (see "Downloadable materials" below).

   **First, if the course embeds any hand-authored SVG diagrams, lint and
   auto-fit them** — this prevents clipped edges and overlapping labels (the
   diagrams flow into the course, PDF and PPTX, so fix them once, up front):

```bash
python <skill-dir>/scripts/autofit_svg.py  course.json          # grow each viewBox to fit its content
python <skill-dir>/scripts/validate_svg.py course.json --strict # measure text: catch overflow, overlap, styled <tspan>
```

   `autofit_svg.py` measures real text widths and enlarges each `viewBox` (and
   its background rect) so nothing is clipped; `validate_svg.py` reports any
   remaining overlaps, styling `<tspan>` traps, tofu glyphs, or lines crossing a
   label. Both accept `.svg` files, a directory, or a `course.json`.

   You still run `autofit_svg.py` yourself (it *edits* the SVGs). The **check**
   also runs **automatically**: `make_materials.py` lints the diagrams before
   rasterising them, and `build_mbz.py` lints them on every build (warn-only by
   default; add `--strict-svg` to abort on defects, `--no-svg-check` to skip). So
   a broken diagram cannot ship unnoticed even if you forget this step. Then
   generate the materials:

```bash
python <skill-dir>/scripts/make_materials.py course.json -o course.materialized.json
```

This writes, for every `material` page, a print PDF that mirrors the **full
Infoblatt** (header bar, prose, diagram, tables/lists, Merke box) and an editable
PPTX, and collects all PDFs + PPTX into the hidden teacher section as two folders.
The PDF is **not** inserted after the page — the Infoblatt stays alone at its
spot. Then build from the **materialized** JSON. (Skip this step only for a course
with no Infoblätter to export.)

3. Build the `.mbz` (from the materialized JSON if you ran step 2):

```bash
python <skill-dir>/scripts/build_mbz.py course.materialized.json -o backup.mbz \
    --wwwroot https://moodle.example.edu
```

4. **Always validate** the output before handing it over:

```bash
python <skill-dir>/scripts/validate_mbz.py backup.mbz
```

It checks the archive is a valid gzip tar, every XML is well-formed, and the
cross-references in `moodle_backup.xml` line up with the files actually
present — **plus deep content checks** (all < 1 s): the complete glossary
user-data chain (settings, userref, author with `mnethosturl=$@NULL@$`,
approved entries, import fallback aboard), tiles Kachelfoto wiring
(option ↔ file ↔ blob ↔ plugin element), the attribution footer on every
page/book chapter, empty formular fields (no placeholder = no pre-typed
Lösungsweg) with autosave/save button, and the compact no-scroll sim layout.
Exit 1 on errors; warnings don't fail.

**Timing/Parallelität:** start the NotebookLM video FIRST (it only needs the
dossier from `course.json` and takes 5–10 min), then run the whole
build+validation pipeline WHILE the video generates — validators never add
wall-clock time. See the pipeline block in `references/course-design.md`.

5. **Always generate a visual preview** alongside the `.mbz` so the author can
   review the whole course (every section + every activity with its full
   content) without importing into Moodle:

```bash
python <skill-dir>/scripts/preview_mbz.py course.json -o course_vorschau.html
```

This writes a self-contained, interactive HTML file (open in any browser): each
section expands to show pages with their embedded diagrams, books, quizzes with
answers + feedback, assignments with rubrics, forums, glossaries, choices,
feedback items, and file resources/folders. Images are inlined (SVG as markup,
raster as base64), so the file stands alone. Treat this as a standard output of
every build — deliver the preview together with the `.mbz`.

6. **Video-Recap erzeugen — PFLICHT-SCHRITT bei jedem Kurs.** Der Kurs enthält
   im Kurs-Recap den Platzhalter „Videozusammenfassung". **Fülle ihn immer**,
   sofern technisch möglich: Führe den NotebookLM-Flow aus
   `references/notebooklm-video-recap.md` aus (Dossier via
   `export_course_dossier.py` → Browser via claude-in-chrome → Quelle als
   „Kopierter Text" → Videoübersicht „Anpassen": Deutsch + **Rückblick-Brief** →
   ~5 min pollen → herunterladen → `set_recap_video.py --file` → **Kurs neu
   bauen**). Das ist kein optionaler Zusatz mehr, sondern gehört zu jedem
   fertigen Kurs.
   **Reihenfolge/Parallelität:** Da NotebookLM nur das Dossier braucht und
   5–10 min rechnet, den Video-Flow so FRÜH wie möglich anstoßen (direkt nach
   fertiger `course.json`) und die Schritte 2–5 (Materialien, Build,
   Validatoren, Vorschau, Browser-Checks) WÄHREND der Wartezeit ausführen —
   die Wartezeit wird so vollständig als Prüfzeit genutzt und die
   Kursherstellung nicht verlängert. Nach dem Video-Einbau nur der kurze
   Rebuild + `validate_mbz` erneut.
   **Einzige Ausnahme (Fallback):** Ist in der Session kein Browser verbunden
   (`list_connected_browsers` leer) oder der Nutzer bei NotebookLM nicht
   eingeloggt, kann der Schritt nicht laufen — dann den Platzhalter im Kurs
   lassen, den Nutzer bitten, sich einzuloggen, und das Video nachziehen,
   sobald der Zugang steht. Niemals einfach überspringen ohne Hinweis.

7. In Moodle: *Course → Restore → upload `backup.mbz` →* restore as a new course
   (or merge into an existing one).

A full demo spec covering every supported type lives at
`assets/example_course.json` — build it to see all types at once.

## Interaktiver Kurs-Editor (Widget) — Standard-Schritt vor dem Build

Nach der Kurs-Generierung (fertige `course.json`) zeige dem Autor den Kurs im
**bearbeitbaren Widget**, bevor du die `.mbz` baust. Das Widget ist die
**bearbeitbare Vorschau**: Es rendert den Kurs in Vorschau-Optik (Titel +
Meta-Zeile, Abschnitts-Kacheln, Diagramme **inline im Inhalt**, Quiz mit
Antworten und Feedback) und macht genau diese Ansicht direkt editierbar
(WYSIWYG). Inline-Diagramme sind als `svgwrap`-Marker geschützt und werden
beim Senden automatisch zurück zu `@@PLUGINFILE@@`-`img`-Tags serialisiert —
das Kurs-HTML bleibt sauber:

1. Rufe einmalig `mcp__visualize__read_me` (`modules: ["interactive"]`) auf (still).
2. `python <skill-dir>/scripts/build_editor_widget.py course.json -o editor.html`
3. Rendere den Datei-Inhalt via `mcp__visualize__show_widget`
   (title: `mbz_course_editor_<shortname>`).
4. **Erzeuge IMMER auch die Lese-Vorschau und liefere sie mit** (sie ist billig
   und das Standard-Review-Werkzeug — nicht erst bei `finalize`):
   `python <skill-dir>/scripts/preview_mbz.py course.json -o <kurs>_vorschau.html`,
   dann als Datei an den User senden (render). Nach jedem `save`/`ai_assist`
   mit inhaltlichen Änderungen: Vorschau mit-regenerieren.

Der Autor editiert lokal (Struktur + Felder). Aktionen erreichen dich als
Nachricht `Kurs-Editor-Aktion:` mit einem JSON-Envelope:
`{widget:"mbz-course-editor", action, course, target?, instruction?}` —
`course` ist IMMER der vollständige aktuelle Kursstand (ohne `_`-Keys; Bilder
bleiben Pfad-Referenzen).

**Handler je `action`:**
- `save` — Envelope-`course` als `course.json` speichern (überschreiben),
  kurz plausibilisieren (JSON-Struktur, Pflichtfelder), Widget aus der neuen
  Datei regenerieren und erneut rendern. KEIN Build.
- `ai_assist` — `target` = `{section, activity}`-Indizes. Führe `instruction`
  auf genau diesem Baustein aus (Text/Fragen/SVG generieren und in die
  Kursdefinition einsetzen — bei SVG: neue Datei schreiben und
  `autofit_svg.py`/`validate_svg.py` laufen lassen, Pfad in `images` aktuell
  halten). Dann wie bei `save`: speichern, regenerieren, rendern.
  **Nur `{section}` (ohne `activity`)** = Abschnitts-Auftrag: auf den ganzen
  Abschnitt anwenden (z. B. neue Aktivität hineingenerieren, Abschnitt
  überarbeiten).
- `quality_check` — kursweiter Konsistenz-Check auf dem Envelope-Stand:
  (a) Constructive Alignment: Lernziele ↔ Testfragen ↔ Praxisauftrag decken
  sich (Verb-Konsistenz!), (b) Pflicht-Sequenz vollständig (Einführung /
  Vertiefung / Anwendung / Recap), (c) Zeitbudget ~25 Wörter/Lernminute je
  Abschnitt, (d) Infoblatt-Bauplan (Fließtext ≥120 Wörter, Diagramm, Merke),
  (e) Feedback-Vollständigkeit in Quizzes. Befunde kompakt je Baustein im Chat
  melden, konkrete Fixes vorschlagen und auf Wunsch als `ai_assist` anwenden.
  KEIN Build.
- `finalize` — volle Pipeline auf dem Envelope-Stand: `autofit_svg` →
  `validate_svg --strict` → `make_materials` → `build_mbz` → `validate_mbz` →
  `preview_mbz`. Deliverables (.mbz + Vorschau) an den User geben.
- `video_recap` — erprobter NotebookLM-Flow, Schritt für Schritt in
  `references/notebooklm-video-recap.md` (Dossier via
  `export_course_dossier.py` → Browser via claude-in-chrome → Quelle als
  „Kopierter Text" → Videoübersicht „Anpassen" mit Sprache Deutsch +
  **Rückblick-Brief** (Vorlage in der Referenz — sonst wirkt das Video wie
  ein Einstieg statt wie das Recap) → ~5 min pollen → ⋮/Herunterladen →
  `set_recap_video.py --file` → Rebuild). Falls in der Session kein
  Browser-Zugriff besteht oder der User nicht eingeloggt ist: Stand erklären,
  Platzhalter im Kurs lassen.

**Fehlerfälle:** Unparsebarer Envelope → letzte gültige `course.json` behalten,
Widget daraus neu rendern und den Fehler im Chat erklären. Schlägt `finalize`
in einem Validator fehl → eindeutige Defekte beheben, sonst Widget mit Hinweis
auf den betroffenen Baustein neu rendern.

Zwischenstände bauen NIE eine `.mbz` — nur `finalize` tut das.

## Supported activity types

The `type` field of each activity selects a builder. Supported today:

**Arbeitsmaterialien (resources):** `label`, `page`, `url`, `resource` (file
download), `folder`, `book`.
**Aktivitäten (activities):** `assign`, `quiz` (with `truefalse` /
`multichoice` questions), `forum`, `glossary` (with pre-filled `entries`),
`choice`, `feedback` (with pre-filled `items`).

Quizzes carry **formative feedback** for real didactic value: each question
takes `generalfeedback`; `multichoice` answers take per-answer `feedback`;
`truefalse` takes `feedbackcorrect`/`feedbackwrong`; and a quiz takes
`overallfeedback` (grade-boundary bands). See `references/course-design.md`.

`glossary` entries are **user data** in Moodle, so a glossary with `entries`
makes the generator emit a minimal `users.xml` (one author), a `<userref>` in
the glossary's `inforef.xml`, and set `users=1` + the matching `*_userinfo`
settings. On restore, keep "include user data" enabled so the entries appear.
The author user is written with `mnethosturl = $@NULL@$` — **never** a real
URL: a set URL that differs from the target site makes Moodle treat the author
as a foreign MNet remote user it may not create, the user is dropped and the
glossary arrives **empty** (this was a real bug). As a belt-and-braces
fallback, `make_materials.py` additionally writes a **glossary import XML**
(`materials/<slug>_import.xml`, Moodle's Glossar → „Einträge importieren"
format) and attaches it in the hidden teacher section — so even a restore
without user data can re-fill the glossary in two clicks.
`feedback` items are part of the activity definition (no user data needed).

Per-type fields are documented in `references/activity-types.md`. Common
optional fields on any activity: `visible` (0/1), `completion` (0/1/2),
`showdescription`, `indent`, `idnumber`.

## Attaching real files

`resource` takes a `file` (path on disk); `folder` takes a `files` list. The
generator reads the bytes, computes the SHA-1 content hash, stores the file at
`files/<xx>/<hash>`, writes the `files.xml` record (plus the required directory
record) and links it from the activity's `inforef.xml`.

```json
{"type": "resource", "name": "Script", "file": "C:/path/to/script.pdf"}
{"type": "folder", "name": "Handouts", "files": ["C:/a.pdf", "C:/b.docx"]}
```

**Path caveat:** the path goes inside the JSON, so it must be a real path the
Python process can open. On Windows use a full path with forward slashes or
escaped backslashes (e.g. `C:/Users/.../file.pdf`). Don't rely on shell shims
like `/tmp/...` — those are only rewritten for command-line arguments, not for
strings inside the JSON.

## Embedding images inline in a page (diagrams, illustrations)

A `page` can carry images shown **inline in the content** (not just as a
download). Add an `images` list of file paths and reference each by filename in
the HTML via `@@PLUGINFILE@@/<filename>`:

```json
{"type": "page", "name": "Aufbau",
 "images": ["C:/.../assets/diagram.svg"],
 "content": "<p>...</p><img src='@@PLUGINFILE@@/diagram.svg' style='max-width:100%'>"}
```

The generator stores each file in the page's `content` filearea and Moodle
rewrites `@@PLUGINFILE@@` on restore. **Why a file and not inline `<svg>`:**
Moodle's HTMLPurifier strips inline `<svg>` from page content, so author/generate
diagrams as **SVG (or PNG) files** and embed them as `<img>` — that renders
reliably. SVG is ideal for labelled technical diagrams; you can hand-author it
(no rasteriser needed). `image/svg+xml`, `png`, `jpg`, `gif`, `webp` are
recognised. (Book-chapter inline images are not yet supported — use pages.)

## Kachel-Bilder (section images) — Standard für jeden Kurs

Every visible content section (Kachel) gets an image: set `"image"` (one
path) or `"images"` (list) on the section. What the generator does depends on
`course.format`:

**`format: "tiles"` (echte Kachel-Fotos, format_tiles):** the image becomes
the REAL tile photo of the Kachel — exactly as if uploaded in the tiles UI.
The generator stores the file as `format_tiles / tilephoto / itemid=sectionid`
with filepath `/tilephoto/` and emits the wiring for BOTH plugin
generations (union, mutually harmless):

- **current format_tiles (>= 2024021400):** `plugin_format_tiles_section`
  with `sectionid` ATTRIBUTE + `optiontype=1` (PHOTO) / `optionvalue=
  <filename>` / `tilesversion` — its restore writes the new
  `format_tiles_tile_options` table, maps the section id and restores the
  photo file via the `itemid` mapping. This is what current installs need;
  without it tiles show only the default icon.
- **legacy (learnweb-era):** `course_format_options` row `tilephoto` in
  `section.xml` (core restores it on format match) + `<dummysection/>`
  trigger for the old file-itemid remap. Newer plugins migrate/ignore the
  legacy row (photos take precedence, idempotent).

No banner is injected into the summary. Requirements: format_tiles installed
on the target Moodle; the admin setting **"Foto-Kacheln erlauben"
(allowphototiles)** enabled — without it Moodle hides photos even when they
restored correctly. **Author tile photos as text-free motif PNGs (~800×450)**
— the tile title is overlaid by the plugin itself, and the photo is cropped
cover-style (draw an SVG motif, rasterise via svglib→fitz like
`make_materials` does). `validate_mbz.py` enforces the full chain
(option ↔ file ↔ blob ↔ new-style element; missing dummysection = warn).

```json
{"course": {"format": "tiles", …},
 "sections": [{"name": "1 · Einstieg", "image": "assets/kachel_einstieg.png", …}]}
```

**Other formats (topics/weeks):** the file goes to the section summary
filearea (component `course`, filearea `section`) and — if the summary does
not already reference `@@PLUGINFILE@@` — the first image is embedded as a
banner on top of the summary. Author banners as slim SVGs (viewBox
`0 0 1200 150`, tinted background + motiv + title). They run through the same
SVG QA as the diagrams. `preview_mbz.py` shows section images at the top of
each Kachel in both modes.

## Downloadable materials (PDF + PowerPoint), auto-generated

Set `"material": true` on an Infoblatt `page` and `make_materials.py` (Quick
start step 2) will, for that page, generate a **print PDF that mirrors the full
Infoblatt** (header bar, explanatory prose, embedded diagram, tables/lists and
Merke box — the same content as the page) and an **editable PPTX** (title + the
page's embedded diagram + key points), and add both to the hidden teacher section
as folders (a PDF set for printing, a PPTX set for editing). The PDF is **not**
inserted after the page — the Infoblatt stays alone at its spot in the course.
Provide `"material_bullets": ["…", "…"]` for the PPTX key points; if omitted they
are extracted from the page content (list items, else paragraphs).

```json
{"type": "page", "name": "Infoblatt: Aufbau der Standbohrmaschine", "material": true,
 "material_bullets": ["Bohrfutter: hält den Bohrer", "Not-Aus: stoppt sofort"],
 "images": ["C:/.../assets/aufbau.svg"],
 "content": "<...><img src='@@PLUGINFILE@@/aufbau.svg'><..."}
```

The tool reads diagrams from the page's `images`, rasterises them for the PPTX
(SVG → PDF → PNG) and embeds them vector-wise in the PDF. So every Infoblatt
ships three ways — inline in the course, as PDF, and as editable PPTX — with no
manual file wiring. The only material intentionally **not** generated is the
**video summary** (a NotebookLM placeholder the author fills in later).

## Interactive simulations (optional, where the topic fits)

An interactive HTML simulation (drag a slider → values/picture update live) can
turn a passive topic into an explorable one. **Use it only where a topic has a
variable relationship worth exploring** — Ohm's law, series/parallel circuits,
gear ratio, engine crank, dosage, interest, pressure/flow, … A topic with nothing
to "drag" gets no simulation; forcing one is noise, not value.

**Why a file, not a page/database:** Moodle's HTMLPurifier strips `<script>` from
`page`, `book`, **database** and `label` content, so inline JS does **not** run
there (only *static* HTML survives). A real **file** served from the file area
*does* run JS. So a simulation ships as a **`resource`** (single self-contained
`.html`) — or as SCORM if you want it embedded in-page with completion tracking.
This is fully offline (no CDN), CSP-safe, light/dark-aware and keyboard-operable.

Add a simulation to a section with a `simulation` activity — either from the
built-in library or an inline spec:

```json
{"type": "simulation", "use": "reihenschaltung", "name": "Simulation: ausprobieren"}
{"type": "simulation", "name": "…", "spec": { …see below… }}
```

`scripts/build_simulation.py` expands these into self-contained `.html` files
(under `sims/`) and rewires each as a `resource`. Run it **first** in the pipeline
(before `make_materials.py`):

```
build_simulation.py course.json     -o course.sim.json          # sims → file resources
make_materials.py   course.sim.json -o course.materialized.json # PDFs/PPTX
build_mbz.py        course.materialized.json -o course.mbz --wwwroot …
```

`python build_simulation.py --list` shows the library; `--emit <name> -o f.html`
renders one standalone. After restoring, set the resource's display to *embed* or
*pop-up* so the simulation opens in place.

**Engine + spec (one engine, many subjects).** `scripts/sim_engine.py` holds a
generic engine (sliders, KPI tiles, theme, layout) and `SIM_LIBRARY`. A spec is:
`{title, subtitle, inputs:[{id,label,unit,min,max,step,default}],
kpis:[{id,label,unit,dec,big?}], visual:"<svg…>", compute:"<JS body> return {…}",
render:"<JS body>"}`. Only `compute` (the domain formulas) and `render`/`visual`
(the picture) are subject-specific — the rest is identical for every trade. **To
extend:** add a spec to `SIM_LIBRARY` (or pass one inline). Keep values on the
slider `step` grid (a `default` off the grid gets snapped by the browser).

**Layout: everything on one screen.** The engine renders controls + results in
a left column and the live view beside them, so on a normal display (≥ ~1280 px)
the WHOLE simulation is visible **without scrolling** (narrow screens stack).
Keep the `visual` viewBox flat-ish (e.g. 600×300) so it fits the height budget
(`svg {max-height:56vh}`).

## Ausfüllbare Arbeitsblätter (`formular`) — echte Eingabefelder mit Speichern

For worksheets/protocols the learners actually FILL IN (Berechnungsprotokoll,
Prüfprotokoll, Reflexionsbogen), never leave `__________` blanks in a `page` —
nobody can type there. Use a **`formular`** activity instead; `build_simulation.py`
expands it (same pass as simulations) into a self-contained HTML **file
resource** rendered by `scripts/form_engine.py` with:

- full-width inputs/textareas (long enough for a Rechenweg — no cramped gaps),
- **fields are ALWAYS EMPTY** — no placeholders, no pre-typed example
  Rechenwege (they would give the solution away; the engine ignores any
  `placeholder` in the spec). Hints belong in the `note` or teacher material,
- field `label`s may carry inline HTML — use `<sub>`/`<sup>` for
  Formelzeichen-Indizes (`A<sub>1</sub> = π/4 · d<sub>1</sub>²`); the
  Textdatei-Export strips tags automatically,
- **Autosave** into `localStorage` per field (survives reload/navigation),
- **„Als Textdatei speichern"** (downloads the answers — for the `assign` upload),
- **„Drucken / als PDF speichern"** (print CSS) and **„Zurücksetzen"**.

```json
{"type": "formular", "name": "Berechnungs- und Prüfprotokoll (ausfüllbar)",
 "spec": {
   "title": "Berechnungs- und Prüfprotokoll",
   "storage_key": "hydraulik_protokoll",
   "blocks": [
     {"heading": "Daten (gegeben)"},
     {"html": "<table>…</table>"},
     {"field": {"id": "a1", "label": "Kolbenfläche A1 (Rechenweg + Ergebnis)",
                "unit": "cm²", "type": "text"}},
     {"field": {"id": "begruendung", "label": "Begründung", "type": "textarea", "rows": 3}}
   ],
   "note": "Tipp …"}}
```

Pair it with the Praxisauftrag: learners save their answers as a file and hand
that in via the `assign`. After restore set the resource display to *embed* or
*new window*.

## Course definition reference

Full JSON schema (all course/section/activity fields and defaults) is in
`references/course-spec.md`. Highlights:

- `sections` is an ordered list. **Index 0 is section 0** (the top/"General"
  section); index 1 is "Topic 1", etc. The section `sequence` is built
  automatically from the activities you list — never hand-maintain cmid lists.
- `course.format`: `topics` (default), `weeks`, or `tiles`.
- Text fields (`summary`, `intro`, `content`) take **raw HTML**; the generator
  XML-escapes it. Don't pre-escape.

## How it works (architecture)

`scripts/build_mbz.py` is a single self-contained generator:

- An `Ids` allocator hands out internally-consistent ids across the parallel
  spaces: **cmid** (course-module id → folder name, `module.xml@id`,
  `activity@moduleid`), **instance id** (`<modname id>`), **module contextid**,
  file ids, question ids. Moodle remaps all of these on restore, so only their
  internal consistency matters.
- `ACTIVITY_BUILDERS` maps each `type` to a function returning the inner XML of
  that activity's main file. **These are the bundled per-type templates.**
- Everything else (wrapper files, course, sections, `moodle_backup.xml`,
  `.ARCHIVE_INDEX`) is generic and built once.
- The archive is packed with Python's `tarfile` as `w:gz`, writing
  `.ARCHIVE_INDEX` first (matching Moodle's own packer ordering).

## Extending: adding a new activity type

To support a type not yet covered (e.g. `lesson`, `wiki`, `h5pactivity`,
`scorm`):

1. Get the authoritative field list + order from the module's
   `backup_<mod>_stepslib.php` `define_structure()` in the Moodle 4.1 source
   (`github.com/moodle/moodle`, branch `MOODLE_401_STABLE`). The field order
   must match the source exactly.
2. Add a `b_<type>(ctx)` builder following the existing ones (return the inner
   `<modname id="...">...</modname>` XML) and register it in `ACTIVITY_BUILDERS`.
3. Rebuild and run `validate_mbz.py`.

`references/activity-types.md` lists the known field schemas and the source
files to consult, plus the documented quirks (e.g. book's `<timemcreated>` typo,
quiz's `<attempts_number>`, feedback's `<typ>`).

## Compatibility notes

- The backup declares `backup_version 2022112800` / release `4.1`. Moodle does
  **not** hard-reject a *general* restore by version: a 4.1 backup restores
  cleanly into 4.1 and forward into 4.2/4.3/4.4/4.5 (the target runs its
  upgrade steps; you may see an informational warning only). A hard version
  gate applies only to same-site *import*, not to normal restore.
- `.ARCHIVE_INDEX` is generated for fidelity with real backups, but Moodle's
  restore does not strictly require it (it reads `moodle_backup.xml`).
- **Course format:** built-in `topics`/`weeks` restore reliably everywhere.
  **`tiles`** (third-party format_tiles) is emitted with full plugin fidelity
  — course/section format options, tile photos in `format_tiles/tilephoto/
  /tilephoto/` and `plugin_format_tiles_*` elements with dummy triggers, so
  Kachel-Fotos restore natively (see "Kachel-Bilder"). Requires format_tiles
  on the target site; if a target still errors on restore, rebuild with
  `topics` as fallback (photos then need manual upload). Other third-party
  formats remain unsupported.
- User data (submissions, attempts, grades, posts) is intentionally **not**
  generated — backups are "without user info", which is what you want for
  distributing course templates. The one exception is **glossary entries**,
  which Moodle classifies as user data: filling them in switches the backup to
  `users=1` with a single synthetic author user. Everything else stays
  user-data-free. On restore, the author is matched by username/email or
  created if missing (requires the restorer's permission to create users).

## Reference files

- `references/course-design.md` — **the didactic playbook**: the 5-level structure
  model, the fixed Lernabschnitt sequence, the Infoblatt Bauplan, diagram
  conventions, learning-outcome operators, activity→purpose mapping, writing
  patterns, the materials pipeline, and a quality checklist. Read this before
  authoring any real course.
- `assets/fewshot_bohrmaschine.json` — the gold-standard vocational module (5-level
  model, embedded SVG diagrams, `material` flags); its diagrams live in `assets/*.svg`.
  Use as the few-shot template. `assets/example_course.json` is a shorter feature demo.
- `references/mbz-format.md` — the full `.mbz` format: archive layout, every
  top-level/course/section file, the ID cross-reference network, `$@NULL@$`
  semantics, the file store. Read this to understand or debug a backup.
- `references/activity-types.md` — per-activity-type field schemas and source
  pointers; read before adding or editing an activity type.
- `references/course-spec.md` — the JSON course-definition schema.
- `references/notebooklm-video-recap.md` — **Pflicht-Schritt** am Ende jedes
  Kurses: Video-Recap via NotebookLM (Dossier via `export_course_dossier.py`,
  Einbau via `set_recap_video.py`). Immer ausführen, außer kein Browser/Login.
- `scripts/validate_svg.py` + `scripts/autofit_svg.py` — diagram QA: measure real
  text widths (`scripts/svg_geometry.py`) to catch clipped edges / overlapping
  labels / styling-`<tspan>` traps, and grow each `viewBox` to fit. Also lints
  the **German typography conventions** (warn-level): units superscripted
  (`cm2`/`cm^2` → `cm²`, `min-1` → `1/min`), Malpunkt `·` instead of `x`/`×`,
  REAL umlauts ä/ö/ü/ß instead of ae/oe/ue transliterations (they render fine
  in PDF/PPTX), decimal comma (`3,14`), minimum font size 10, near-centred /
  near-flush labels (Bündigkeit) and text/box contrast. Scans activity images
  AND section images. Run on `.svg`, a folder, or a `course.json` before
  `make_materials.py`. See "SVG-Autorenregeln" in `references/course-design.md`.
