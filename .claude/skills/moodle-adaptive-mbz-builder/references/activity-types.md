# Activity type field schemas (Moodle 4.1)

The main file of each activity is `activities/<mod>_<cmid>/<mod>.xml`, with the
outer wrapper `<activity id moduleid modulename contextid>` and one inner
`<modname id>` element. **Only the inner element differs by type** — that's the
"template" each `b_<type>()` builder in `build_mbz.py` produces.

Field **order matters**: Moodle's restore reads these as ordered structures
defined in each module's `backup/moodle2/backup_<mod>_stepslib.php`
(`define_structure()`), branch `MOODLE_401_STABLE` on github.com/moodle/moodle.
When adding/editing a type, copy the order from there.

## Contents
- Resources: label, page, url, resource, folder, book
- Activities: assign, quiz, forum, glossary, choice, feedback
- Quiz ↔ question bank
- Documented quirks
- Adding a new type

---

## Resources ("Arbeitsmaterialien")

### label
`name, intro, introformat, timemodified`

### page
`name, intro, introformat, content, contentformat, legacyfiles,
legacyfileslast, display, displayoptions, revision, timemodified`
- `display` 5 = embed; `displayoptions` is a serialized PHP array.

### url
`name, intro, introformat, externalurl, display, displayoptions, parameters,
timemodified`
- `parameters` = `a:0:{}` when none.

### resource (single file download)
`name, intro, introformat, tobemigrated, legacyfiles, legacyfileslast, display,
displayoptions, filterfiles, revision, timemodified`
- The file lives in the file store, filearea `mod_resource/content`.

### folder
`name, intro, introformat, revision, timemodified, display, showexpanded,
showdownloadfolder, forcedownload`  (9 fields — `forcedownload` is easy to miss)
- Files in filearea `mod_folder/content`.

### book
book: `name, intro, introformat, numbering, navstyle, customtitles,
timecreated, timemodified` (no `revision`)
chapter: `pagenum, subchapter, title, content, contentformat, hidden,
timemcreated, timemodified, importsrc`

---

## Activities ("Aktivitäten")

### assign
`name, intro, introformat, alwaysshowdescription, submissiondrafts,
sendnotifications, sendlatenotifications, sendstudentnotifications, duedate,
cutoffdate, gradingduedate, allowsubmissionsfromdate, grade, timemodified,
completionsubmit, requiresubmissionstatement, teamsubmission,
requireallteammemberssubmit, teamsubmissiongroupingid, blindmarking, hidegrader,
revealidentities, attemptreopenmethod, maxattempts, markingworkflow,
markingallocation, preventsubmissionnotingroup, activity, activityformat,
timelimit, submissionattachments` + `<plugin_configs>` for submission/feedback
subplugins. Reads `grading.xml`.

### quiz
`name, intro, introformat, timeopen, timeclose, timelimit, overduehandling,
graceperiod, canredoquestions, preferredbehaviour, attempts_number,
attemptonlast, grademethod, decimalpoints, questiondecimalpoints, reviewattempt,
reviewcorrectness, reviewmaxmarks, reviewmarks, reviewspecificfeedback,
reviewgeneralfeedback, reviewrightanswer, reviewoverallfeedback,
questionsperpage, navmethod, shuffleanswers, sumgrades, grade, timecreated,
timemodified, password, subnet, browsersecurity, delay1, delay2,
showuserpicture, showblocks, completionattemptsexhausted, completionminattempts,
allowofflineattempts` + `<question_instances>`.

### forum
`type, name, intro, introformat, duedate, cutoffdate, assessed, assesstimestart,
assesstimefinish, scale, maxbytes, maxattachments, forcesubscribe, trackingtype,
rsstype, rssarticles, timemodified, warnafter, blockafter, blockperiod,
completiondiscussions, completionreplies, completionposts, displaywordcount,
lockdiscussionafter, grade_forum` (`grade_forum` is last).

### glossary
`name, intro, introformat, allowduplicatedentries, displayformat, mainglossary,
showspecial, showalphabet, showall, allowcomments, allowprintview, usedynalink,
defaultapproval, globalglossary, entbypage, editalways, rsstype, rssarticles,
assessed, assesstimestart, assesstimefinish, scale, timecreated, timemodified,
completionentries` + `<entries>`.

### choice
`name, intro, introformat, publish, showresults, display, allowupdate,
allowmultiple, showunanswered, limitanswers, timeopen, timeclose, timemodified,
completionsubmit, showpreview, includeinactive, showavailable` + `<options>` of
`<option>` (`text, maxanswers, timemodified`).

### feedback
`name, intro, introformat, anonymous, email_notification, multiple_submit,
autonumbering, site_after_submit, page_after_submit, page_after_submitformat,
publish_stats, timeopen, timeclose, timemodified, completionsubmit` + `<items>`
of `<item>` (note the type tag is `<typ>`, not `type`).

---

## Quiz ↔ question bank (Moodle 4.0+)

Quiz slots do **not** point at questions directly. The chain is:

```
quiz <question_instances><question_instance>
  → <question_reference><questionbankentryid>      (fixed question)
  → <question_set_reference><filtercondition>      (random question)
      ↓
questions.xml: question_category → question_bank_entry → question_version
  → question_versions(version,status) → questions → question(qtype, plugin_qtype_*)
```

The actual question content lives in the top-level **questions.xml**, referenced
from the quiz's `inforef.xml` via `<question_categoryref>`. `build_mbz.py` emits
the entries/versions/questions for `truefalse` and `multichoice` types.

**Critical rule — quiz-owned questions live at the quiz MODULE context
(`contextlevel 70`), NOT the course context.** Each quiz gets its **own** `top`
category (`parent=0`) **plus** a child category holding its questions, and BOTH
carry `<contextid>` = that quiz's module context, `<contextlevel>70</contextlevel>`
and `<contextinstanceid>` = the quiz's cmid. The `question_reference`'s
`<usingcontextid>` is the same module context, so category context, wrapper
context (`<activity … contextid="…">`) and reference context all agree.

*Why the module context:* it is what REAL Moodle backups do — verified against
a genuine school-Moodle backup (module-context `top`+child per quiz,
`contextlevel 70`); Moodle's restore creates module-owned categories at course
context temporarily and *moves* them into the recreated module
(`restore_move_module_questions_categories`) via the context mapping from each
activity's `<activity … contextid="…">` wrapper. Lab-verified end-to-end on
Moodle 4.5 (2026-07-15). Note: an earlier theory blamed a shared course-context
bank for a restore abort — the actual blocker turned out to be a mod_feedback
NULL field (see quirks below); the module-context layout is kept because it
matches real backups exactly.

**One `top` per context still holds:** each quiz module context is its own
context, so one `top` (`parent=0`) per quiz keeps exactly one root per context —
what Moodle's restore enforces (*"more than one top category for questions in
context N"* otherwise). `validate_mbz.py` checks both invariants: at most one
`parent=0` category per context, AND every quiz `usingcontextid` has a matching
`contextlevel=70` category in `questions.xml`.

---

## Documented quirks (must reproduce exactly)

- **book chapter**: the created-time tag is `<timemcreated>` (extra "m") — a
  long-standing source quirk; restore expects this spelling. `book` has **no**
  `revision`.
- **quiz**: the XML tag is `<attempts_number>` (DB column is `attempts`); the
  `<canredoquestions>` field exists.
- **feedback item**: type tag is `<typ>`, not `type`. **`<name>`, `<dependvalue>`,
  `<options>`, `<label>` are NOT NULL DEFAULT '' columns** — emit the EMPTY
  string (`<name></name>`), NEVER `$@NULL@$`: a NULL there aborts the whole
  restore with dmlwriteexception *"Column 'name' cannot be null"* and silently
  kills every activity after the feedback (real restore-blocking bug, found via
  Moodle-Lab repro 2026-07-15; `validate_mbz.py` check 8b guards this). Label
  items have `name=''`; the visible text lives in `<presentation>`.
- **folder**: don't forget the 9th field `<forcedownload>`.
- **module.xml**: include `<completionpassgrade>` and the trailing `<lang>`.
- **files**: single-level hash sharding `files/<2 chars>/<full hash>`.
- **multichoice question**: the `<multichoice>` options block must include
  `<showstandardinstruction>` (NOT NULL int in `qtype_multichoice_options`).
- **question**: after the `plugin_qtype_*_question` block, real backups also
  emit empty `plugin_qbank_comment_question` and `plugin_qbank_customfields_question`
  blocks (before `question_hints`); the generator includes them for fidelity.
- **`$@NULL@$` is the correct NULL token** and is decoded to SQL NULL by restore
  (confirmed: real backups use it even in nullable INT columns like enrol
  `customint*` and `course_modules.completiongradeitemnumber`). Do NOT replace it
  with empty tags. Only use empty `<tag></tag>` for "" (empty string) on
  not-null text/char columns.

---

## Adding a new type

1. Open `mod/<type>/backup/moodle2/backup_<type>_stepslib.php` on the
   `MOODLE_401_STABLE` branch; read `define_structure()` for the exact field
   list and order of the root element (and any nested elements/subplugins).
2. Write `b_<type>(ctx)` in `build_mbz.py` returning the inner
   `<type id="...">…</type>` XML. Use `ctx.instance` for the id, `el()` for
   fields, `ctx.b.now` for timestamps. For nested rows needing their own ids,
   call `ctx.b.ids.instance()`.
3. If the type carries files, call `ctx.add_file(path, filearea)`.
4. Register it in `ACTIVITY_BUILDERS`.
5. Rebuild and run `validate_mbz.py`. For real confidence, restore the result
   into a test Moodle 4.1 and check the activity renders.
