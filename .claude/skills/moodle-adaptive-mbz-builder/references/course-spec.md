# Course definition JSON schema

The input to `build_mbz.py`. One JSON object with `course` and `sections`.

## Top level

| Key | Type | Default | Notes |
|---|---|---|---|
| `filename` | string | output basename | Recorded in `moodle_backup.xml`. |
| `course` | object | — | See below. |
| `sections` | array | `[]` | Ordered; index = section number (0 = top/General). |

## `course` object

| Key | Type | Default | Notes |
|---|---|---|---|
| `fullname` | string | `"Course"` | Course full name. |
| `shortname` | string | `"COURSE"` | Must be unique in the target Moodle on restore-as-new. |
| `summary` | HTML string | `""` | Course description. Raw HTML; auto-escaped. |
| `format` | string | `"topics"` | Use `topics` (default) or `weeks`. **Avoid third-party formats like `tiles`** in the backup: their format plugin runs a restore handler that needs plugin-specific data this generator does not produce, so the restore can fail with *"required parameter (contextid)"*. To get the tiles/kachel look, build with `topics` and switch the format in the course settings **after** restoring. |
| `startdate` | int (unix ts) | now | |
| `enddate` | int (unix ts) | `0` | `0` = no end date. |
| `visible` | 0/1 | `1` | |
| `category_name` | string | `"Miscellaneous"` | Cosmetic; restore lets the user pick the real target category. |

## `sections` — array of section objects

Order matters: the first element becomes **section 0** (the "General"/top
section shown above the topics), the second becomes "Topic 1", and so on. If you
want content under "Topic 1", put an (often empty-ish) section 0 first.

| Key | Type | Default | Notes |
|---|---|---|---|
| `name` | string \| null | null | Section title. `null` → Moodle's default name ("Topic N"). |
| `summary` | HTML string | `""` | Section description. |
| `image` / `images` | path \| list | — | **Kachel-Bild(er)**. With `course.format: "tiles"`: becomes the REAL tile photo (format_tiles filearea + `tilephoto` section option + restore-plugin wiring; use text-free ~800×450 PNGs). Other formats: attached to the section filearea; reference in `summary` via `@@PLUGINFILE@@/<name>`, or leave the summary without `@@PLUGINFILE@@` and the first image is auto-embedded as a banner on top. |
| `visible` | 0/1 | `1` | |
| `activities` | array | `[]` | Activity objects, in display order. |

The section's `sequence` (the comma-separated course-module id list that defines
which activities live in the section and their order) is generated automatically
from `activities`. Do not set it yourself.

## Activity objects

Every activity needs a `type`. Common optional fields on any type:

| Key | Type | Default | Notes |
|---|---|---|---|
| `name` | string | type name | Activity title. |
| `intro` | HTML string | `""` | Description shown on the activity page. |
| `visible` | 0/1 | `1` | |
| `completion` | 0/1/2 | `0` | 0 off, 1 manual, 2 automatic. |
| `showdescription` | 0/1 | `0` | Show intro on the course page. |
| `indent` | int | `0` | Indentation on the course page. |
| `idnumber` | string | `""` | Optional external id. |

Type-specific fields:

| `type` | Extra fields |
|---|---|
| `label` | — (just `name`/`intro`) |
| `page` | `content` (HTML body). Optional `images` (list of disk paths embedded inline; reference each in the HTML via `@@PLUGINFILE@@/<filename>`). Optional `material: true` (+ optional `material_bullets`) marks it an Infoblatt → `make_materials.py` auto-generates a PDF + PPTX and wires them in (see `course-design.md`). |
| `url` | `externalurl` |
| `resource` | `file` (disk path, single file download) |
| `folder` | `files` (list of disk paths) |
| `book` | `chapters`: list of `{title, content, subchapter?}` |
| `assign` | `duedate` (unix ts), `grade` (int max points) |
| `forum` | `forumtype` (`general`/`news`/`qanda`/`eachuser`/`single`) |
| `glossary` | `entries`: list of `{concept, definition}` (user data — see below) |
| `choice` | `options` (list of strings) |
| `feedback` | `items`: list (see below) |
| `quiz` | `grade` (max), `questions`: list (see below) |
| `simulation` | *(preprocessed)* `use` (SIM_LIBRARY name) OR `spec` (inline sim spec) — `build_simulation.py` expands it into an interactive HTML `resource` (SKILL.md → "Interactive simulations"). |
| `formular` | *(preprocessed)* `spec` `{title, subtitle?, storage_key?, blocks:[{heading}\|{html}\|{field:{id,label,type:text\|textarea\|number,unit?,rows?}}], note?}` — `build_simulation.py` renders a fillable worksheet (full-width fields, localStorage autosave, save-as-file, print) as an HTML `resource`. Fields are always EMPTY: no placeholders/example Rechenwege (a `placeholder` entry is ignored). See SKILL.md → "Ausfüllbare Arbeitsblätter". |

### Glossary entries (user data)

`glossary.entries` is a list of `{concept, definition}` (definition is HTML).
Because Moodle stores glossary entries as user-authored content, supplying
entries makes the generator emit a `users.xml` with one author and enable the
`users` / `*_userinfo` backup settings automatically. Set the author once via
`course.author` (`{firstname, lastname, email, username}`); it defaults to a
generic "Kurs Leitung" if omitted. On restore, leave "include user data" on.

### Feedback items

`feedback.items` is a list. Each item has a `type`:

| `type` | Fields | Notes |
|---|---|---|
| `label` | `text` (HTML) | Info text, no answer collected |
| `multichoice` | `name`, `options` (list), `required` | Single-choice radio |
| `textfield` | `name`, `size`, `maxlength`, `required` | Short text |
| `textarea` | `name`, `cols`, `rows`, `required` | Long text |
| `numeric` | `name`, `from`, `to`, `required` | Number, optional range |

### Quiz questions and formative feedback

`quiz.questions` is a list. Each question:

```json
{"type": "truefalse", "name": "Q1", "questiontext": "<p>...?</p>", "correct": true,
 "generalfeedback": "<p>Rule/solution shown to everyone after answering.</p>",
 "feedbackcorrect": "<p>Shown when the learner answers correctly.</p>",
 "feedbackwrong": "<p>Shown when the learner answers wrongly.</p>"}
```

```json
{"type": "multichoice", "name": "Q2", "questiontext": "<p>...?</p>",
 "generalfeedback": "<p>Key rule for everyone.</p>",
 "answers": [
   {"text": "A", "correct": true,  "feedback": "<p>Why this is right.</p>"},
   {"text": "B", "correct": false, "feedback": "<p>Which misconception this is.</p>"}
 ]}
```

`defaultmark` (points, default 1) is optional per question. Multiple
`correct: true` answers in a multichoice switch it to "multiple response" mode.
All feedback fields are optional but **strongly recommended** for formative
self-tests (see `references/course-design.md`).

### Quiz overall feedback (grade boundaries)

Optional `quiz.overallfeedback`: a list of bands `{min, text}` where `min` is a
percentage. Each band shows its `text` when the learner's score falls in
`[min%, next-min%)`. Use it for Feed-Forward ("repeat section X").

```json
"overallfeedback": [
  {"min": 0,  "text": "<p>Repeat section 2, then try again.</p>"},
  {"min": 60, "text": "<p>On track — review the items you missed.</p>"},
  {"min": 85, "text": "<p>Excellent!</p>"}
]
```

## Worked example

See `assets/example_course.json` for a complete spec exercising every supported
type, including a quiz with both question types.
