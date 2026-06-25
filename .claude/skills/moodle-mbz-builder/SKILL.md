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

## Authoring high-quality courses — read this first for real courses

Producing a *structurally valid* `.mbz` is the easy part. Producing a **didactically
strong, fully fleshed-out course** — especially for **vocational education
(berufliche Bildung)** — is the goal. Do not emit thin, placeholder content.

**Before writing the course JSON, read `references/course-design.md`** (the
didactic playbook) and open `assets/fewshot_bohrmaschine.json` as a worked
gold-standard example. The course-design playbook is built on the **5-level
structure model** (Lernelement → Lernbaustein → Lernabschnitt → Lerneinheit/Modul
→ Lernkurs) with a fixed section sequence. The short version of the method:

1. **Frame it:** clarify trade/Lernfeld, target group, prior knowledge, scope
   (one module ≈ 2 Unterrichtsstunden).
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
   (see "Downloadable materials" below), then run:

```bash
python <skill-dir>/scripts/make_materials.py course.json -o course.materialized.json
```

This writes a PDF and an editable PPTX for every `material` page, inserts the PDF
as a download right after its page, and collects all PDFs + PPTX into the hidden
teacher section. Then build from the **materialized** JSON. (Skip this step only
for a course with no Infoblätter to export.)

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
cross-references in `moodle_backup.xml` line up with the files actually present.

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

6. In Moodle: *Course → Restore → upload `backup.mbz` →* restore as a new course
   (or merge into an existing one).

A full demo spec covering every supported type lives at
`assets/example_course.json` — build it to see all types at once.

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

## Downloadable materials (PDF + PowerPoint), auto-generated

Set `"material": true` on an Infoblatt `page` and `make_materials.py` (Quick
start step 2) will, for that page, generate a **print PDF** and an **editable
PPTX** (title + the page's embedded diagram + key points), insert the PDF as a
download right after the page, and add both to the hidden teacher section as
folders. Provide `"material_bullets": ["…", "…"]` for the key points; if omitted
they are extracted from the page content (list items, else paragraphs).

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
- **Course format:** use the built-in `topics` (or `weeks`). Third-party formats
  like **`tiles`** have their own backup/restore handler that expects
  plugin-specific data this generator does not emit, so a restored `tiles`
  course can fail with *"required parameter (contextid)"*. For a kachel look,
  ship `topics` and switch the format in the course settings after restoring.
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
