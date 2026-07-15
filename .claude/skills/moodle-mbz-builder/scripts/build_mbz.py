#!/usr/bin/env python3
"""Build a Moodle 2 backup file (.mbz) for Moodle 4.1+ from a JSON course spec.

A .mbz is a gzip-compressed tar archive of XML files (the "moodle2" backup
format). This generator produces a structurally valid backup that Moodle can
restore as a new course (or merged into an existing one).

Design idea
-----------
~90% of the files in a backup are *generic*: they don't depend on the activity
type (module.xml, inforef.xml, roles.xml, grades.xml, the course/section files,
moodle_backup.xml). Only ONE file per activity is type-specific: the main
``<modname>.xml``. This generator bundles small builders ("templates") for the
common activity types, so the user only supplies a high-level course spec.

Usage
-----
    python build_mbz.py course.json -o out.mbz
    python build_mbz.py course.json -o out.mbz --wwwroot https://moodle.example.edu

See references/course-spec.md for the JSON schema and references/activity-types.md
for the supported activity types and their fields.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import tarfile
import time
from typing import Any

NULL = "$@NULL@$"  # Moodle backup encoding for SQL NULL (≠ empty string "")

# Pflicht-Attribution: steht automatisch am ENDE JEDER Seite (page-Content und
# Buch-Kapitel). Override pro Kurs via course.attribution (eigener Satz) bzw.
# course.attribution = "" schaltet den Seitenfuß ab.
ATTRIBUTION_SENTENCE = (
    "Dieser Kurs ist mit Hilfe von Künstlicher Intelligenz und in Kooperation "
    "mit dem Labor Didaktik der Technik der Hochschule Osnabrück entstanden."
)


def attribution_text(spec) -> str:
    c = (spec or {}).get("course", {})
    if "attribution" in c:
        return c.get("attribution") or ""
    return ATTRIBUTION_SENTENCE


def attribution_footer(spec) -> str:
    text = attribution_text(spec)
    if not text:
        return ""
    return (
        "<div style='margin-top:16px;padding-top:8px;border-top:1px solid "
        "#c9ccd1;font-size:11.5px;color:#5f6672;font-family:Arial,sans-serif;'>"
        f"<i>{text}</i></div>"
    )


def with_attribution(content: str, spec) -> str:
    """Append the attribution footer to page-like HTML (idempotent)."""
    text = attribution_text(spec)
    if not text or text in (content or ""):
        return content or ""
    return (content or "") + attribution_footer(spec)

# Moodle 4.1 baseline. A backup created with these values restores into 4.1 and
# is forward-compatible with 4.2–4.5 (Moodle only warns on newer-than-target,
# it does not hard-reject a general restore).
MOODLE_VERSION = "2022112800"
MOODLE_RELEASE = "4.1"
BACKUP_VERSION = "2022112800"
BACKUP_RELEASE = "4.1"
# module.xml @version: the activity plugin version. Using the 4.1 baseline keeps
# it <= the installed plugin version on the target (older is always accepted).
MODULE_VERSION = "2022112800"


# --------------------------------------------------------------------------- #
# XML helpers
# --------------------------------------------------------------------------- #
XML_DECL = '<?xml version="1.0" encoding="UTF-8"?>\n'


def xesc(text: Any) -> str:
    """Escape text for an XML text node or attribute value."""
    if text is None:
        return ""
    s = str(text)
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def el(tag: str, value: Any) -> str:
    """One element with escaped text content. None -> SQL NULL sentinel."""
    if value is None:
        return f"<{tag}>{NULL}</{tag}>"
    return f"<{tag}>{xesc(value)}</{tag}>"


# --------------------------------------------------------------------------- #
# ID allocation
# --------------------------------------------------------------------------- #
class Ids:
    """Hands out internally-consistent ids. Moodle remaps everything on restore,
    so the absolute values only need to be unique and cross-referenced
    correctly within this single backup."""

    def __init__(self) -> None:
        self.course_id = 1
        self.course_contextid = 1000
        self._section = 10
        self._cmid = 100
        self._instance = 5000
        self._modctx = 2000
        self._fileid = 9000
        self._userid = 300
        self._userctx = 3000
        self._qcat = 700
        self._qbe = 800
        self._qver = 850
        self._question = 900
        self._answer = 950
        self._qinstance = 990

    def section(self) -> int:
        self._section += 1
        return self._section

    def cmid(self) -> int:
        self._cmid += 1
        return self._cmid

    def instance(self) -> int:
        self._instance += 1
        return self._instance

    def modctx(self) -> int:
        self._modctx += 1
        return self._modctx

    def fileid(self) -> int:
        self._fileid += 1
        return self._fileid

    def userid(self) -> int:
        self._userid += 1
        return self._userid

    def userctx(self) -> int:
        self._userctx += 1
        return self._userctx

    def qcat(self) -> int:
        self._qcat += 1
        return self._qcat

    def qbe(self) -> int:
        self._qbe += 1
        return self._qbe

    def qver(self) -> int:
        self._qver += 1
        return self._qver

    def question(self) -> int:
        self._question += 1
        return self._question

    def answer(self) -> int:
        self._answer += 1
        return self._answer

    def qinstance(self) -> int:
        self._qinstance += 1
        return self._qinstance


# --------------------------------------------------------------------------- #
# Backup builder
# --------------------------------------------------------------------------- #
class MbzBuilder:
    def __init__(self, spec: dict, wwwroot: str) -> None:
        self.spec = spec
        self.wwwroot = wwwroot.rstrip("/")
        self.ids = Ids()
        self.now = int(time.time())
        # path -> bytes  (every entry that ends up in the archive)
        self.files: dict[str, bytes] = {}
        # ordered list of (path, is_dir) for the archive + index
        self.entries: list[tuple[str, bool]] = []
        # collected for moodle_backup.xml <contents> and <settings>
        self.backup_activities: list[dict] = []
        self.backup_sections: list[dict] = []
        # global file records for files.xml: list of dicts
        self.file_records: list[dict] = []
        # question categories for questions.xml (course-level question bank)
        self.question_categories: list[dict] = []
        self.course_question_catref: list[int] = []
        # Moodle 4.x requires exactly ONE root "top" category per context;
        # every real category is a child of it. Created lazily, shared by all
        # quizzes in this course context.
        self.q_top_catid: int | None = None
        # user data (only when an activity carries it, e.g. glossary entries)
        self.users: dict[str, dict] = {}  # username -> user record
        self.has_userdata = False
        self.userinfo_sections: set[int] = set()
        self.userinfo_activities: set[str] = set()
        # dedupe the per-filearea directory record (one "." entry per
        # contextid+component+filearea+itemid, even with several files)
        self._fileareadirs: set[tuple] = set()

    def get_or_create_user(self, author: dict | None) -> int:
        """Return the backup user id for the given author, creating the record
        once (deduplicated by username). Author may carry firstname, lastname,
        email, username; sensible defaults fill the rest."""
        author = author or {}
        username = (author.get("username")
                    or (author.get("email", "").split("@")[0])
                    or "kursleitung")
        if username not in self.users:
            uid = self.ids.userid()
            self.users[username] = {
                "id": uid,
                "contextid": self.ids.userctx(),
                "username": username,
                "email": author.get("email", f"{username}@example.org"),
                "firstname": author.get("firstname", "Kurs"),
                "lastname": author.get("lastname", "Leitung"),
            }
        self.has_userdata = True
        return self.users[username]["id"]

    def ensure_question_top_category(self) -> int:
        """Create (once) the single root 'top' question category for the course
        context and return its id. All quiz categories hang under it, so the
        context never has more than one parent=0 category — which is exactly the
        condition Moodle's restore enforces."""
        if self.q_top_catid is not None:
            return self.q_top_catid
        cat_id = self.ids.qcat()
        self.q_top_catid = cat_id
        site = self.wwwroot.replace("https://", "").replace("http://", "")
        stamp = f"{site}+{self.now}+top{cat_id}"
        xml = (
            f'  <question_category id="{cat_id}">\n'
            f"    <name>top</name>\n"
            f"    <contextid>{self.ids.course_contextid}</contextid>\n"
            f"    <contextlevel>50</contextlevel>\n"
            f"    <contextinstanceid>{self.ids.course_id}</contextinstanceid>\n"
            f"    <info></info>\n    <infoformat>0</infoformat>\n"
            f"    <stamp>{stamp}</stamp>\n    <parent>0</parent>\n"
            f"    <sortorder>0</sortorder>\n    <idnumber>{NULL}</idnumber>\n"
            f"    <question_bank_entries>\n    </question_bank_entries>\n"
            f"  </question_category>"
        )
        # 'top' must precede its children in questions.xml.
        self.question_categories.insert(0, {"id": cat_id, "xml": xml})
        self.course_question_catref.insert(0, cat_id)
        return cat_id

    # -- low-level: register a file/dir into the archive ------------------- #
    def add_file(self, path: str, content: str) -> None:
        self.files[path] = content.encode("utf-8")
        self._register_dirs(path)
        self.entries.append((path, False))

    def add_raw(self, path: str, data: bytes) -> None:
        self.files[path] = data
        self._register_dirs(path)
        self.entries.append((path, False))

    def add_xml(self, path: str, body: str) -> None:
        """body is the XML below the declaration."""
        self.add_file(path, XML_DECL + body)

    def _register_dirs(self, path: str) -> None:
        parts = path.split("/")[:-1]
        cur = ""
        for p in parts:
            cur = f"{cur}{p}/"
            if (cur, True) not in self.entries:
                self.entries.append((cur, True))

    # ===================================================================== #
    # Top-level orchestration
    # ===================================================================== #
    def build(self) -> bytes:
        self._build_sections_and_activities()
        self._build_course()
        self._build_top_level()
        self._build_moodle_backup_xml()
        return self._pack()

    # ----- sections + activities ---------------------------------------- #
    def _build_sections_and_activities(self) -> None:
        sections = self.spec.get("sections", [])
        for number, sec in enumerate(sections):
            sec_id = self.ids.section()
            cmids: list[int] = []
            for act in sec.get("activities", []):
                cmid = self._build_activity(act, sec_id, number)
                cmids.append(cmid)
            self._build_section_files(sec, sec_id, number, cmids)
            self.backup_sections.append(
                {
                    "sectionid": sec_id,
                    "title": sec.get("name") or str(number),
                    "directory": f"sections/section_{sec_id}",
                }
            )

    def add_section_file(self, path_on_disk: str, sec_id: int,
                         tilephoto: bool = False) -> list[int]:
        """Attach a file to a section. Default: summary filearea (component
        'course', filearea 'section', itemid = section id), referenced in the
        summary via @@PLUGINFILE@@/<filename>. With tilephoto=True (Kachel-Foto
        für format_tiles): component 'format_tiles', filearea 'tilephoto',
        filepath '/tilephoto/' — genau wie das Plugin die Fotos speichert.
        Returns the file-record ids for the section's inforef.xml."""
        with open(path_on_disk, "rb") as fh:
            data = fh.read()
        contenthash = hashlib.sha1(data).hexdigest()
        filename = os.path.basename(path_on_disk)
        store_path = f"files/{contenthash[:2]}/{contenthash}"
        if store_path not in self.files:
            self.add_raw(store_path, data)
        component = "format_tiles" if tilephoto else "course"
        filearea = "tilephoto" if tilephoto else "section"
        filepath = "/tilephoto/" if tilephoto else "/"
        refs: list[int] = []
        empty_hash = "da39a3ee5e6b4b0d3255bfef95601890afd80709"
        # directory records ("." entries) — one per filepath level
        dirpaths = ["/"] if filepath == "/" else ["/", filepath]
        for dp in dirpaths:
            dirkey = (self.ids.course_contextid, component, filearea, sec_id, dp)
            if dirkey in self._fileareadirs:
                continue
            self._fileareadirs.add(dirkey)
            dir_id = self.ids.fileid()
            self.file_records.append({
                "id": dir_id, "contenthash": empty_hash,
                "contextid": self.ids.course_contextid, "component": component,
                "filearea": filearea, "itemid": sec_id, "filepath": dp,
                "filename": ".", "filesize": 0, "mimetype": None,
                "source": None, "sortorder": 0,
            })
            refs.append(dir_id)
        file_id = self.ids.fileid()
        self.file_records.append({
            "id": file_id, "contenthash": contenthash,
            "contextid": self.ids.course_contextid, "component": component,
            "filearea": filearea, "itemid": sec_id, "filepath": filepath,
            "filename": filename, "filesize": len(data),
            "mimetype": _guess_mime(filename), "source": filename,
            "sortorder": 1,
        })
        refs.append(file_id)
        return refs

    def _build_section_files(
        self, sec: dict, sec_id: int, number: int, cmids: list[int]
    ) -> None:
        name = sec.get("name")
        summary = sec.get("summary", "")
        visible = sec.get("visible", 1)
        # Kachel-Bilder: section "image"/"images".
        # - format "tiles": das Bild wird ECHTES Kachel-Foto (format_tiles):
        #   Datei in format_tiles/tilephoto//tilephoto/, Section-Format-Option
        #   'tilephoto' (Dateiname) + plugin_format_tiles_section-Element mit
        #   <dummysection/> (verbindet das Restore-Plugin, das die Datei-itemids
        #   auf die neuen Section-IDs umschreibt). KEIN Banner im Summary.
        # - andere Formate: Datei in der Section-Filearea; fehlt @@PLUGINFILE@@
        #   im Summary, wird das erste Bild als Banner vorangestellt.
        fmt = self.spec.get("course", {}).get("format", "topics")
        tiles = fmt == "tiles"
        images = sec.get("images") or ([sec["image"]] if sec.get("image") else [])
        images = [i for i in images if i and os.path.exists(i)]
        filerefs: list[int] = []
        tiles_extra = ""
        for img in images:
            filerefs += self.add_section_file(img, sec_id, tilephoto=tiles)
        if tiles and images:
            fname = os.path.basename(images[0])
            # Kachel-Foto-Verdrahtung für BEIDE format_tiles-Generationen:
            # - NEU (>= 2024021400): plugin_format_tiles_section trägt
            #   sectionid-Attribut + optiontype(1=PHOTO)/optionvalue/
            #   tilesversion; das Restore-Plugin schreibt damit in
            #   format_tiles_tile_options, mappt die Section-ID und stellt
            #   die Foto-Datei über die 'itemid'-Zuordnung wieder her.
            # - ALT (learnweb-Ära): liest die legacy-Zeile 'tilephoto' aus
            #   course_format_options (Core restauriert sie bei Format-Match)
            #   und braucht <dummysection/> als Verbindungs-Trigger für die
            #   Datei-itemid-Neuzuordnung. Neue Versionen ignorieren bzw.
            #   migrieren die legacy-Zeile (Fotos haben Vorrang, idempotent).
            tiles_extra = (
                f'  <course_format_options id="{self.ids.instance()}">\n'
                f"    {el('format', 'tiles')}\n"
                f"    {el('name', 'tilephoto')}\n"
                f"    {el('value', fname)}\n"
                f"  </course_format_options>\n"
                f'  <plugin_format_tiles_section sectionid="{sec_id}">\n'
                f"    {el('optiontype', 1)}\n"
                f"    {el('optionvalue', fname)}\n"
                f"    {el('tilesversion', 2024021400)}\n"
                f"    <dummysection></dummysection>\n"
                f"  </plugin_format_tiles_section>\n"
            )
        elif images and "@@PLUGINFILE@@" not in summary:
            first = os.path.basename(images[0])
            summary = (
                f"<div class='sectionimage'><img src='@@PLUGINFILE@@/{first}' "
                f"alt='' style='max-width:100%;height:auto;border-radius:8px;'>"
                f"</div>" + summary
            )
        body = (
            f'<section id="{sec_id}">\n'
            f"  {el('number', number)}\n"
            f"  {el('name', name) if name is not None else '<name>' + NULL + '</name>'}\n"
            f"  {el('summary', summary)}\n"
            f"  {el('summaryformat', 1)}\n"
            f"  {el('sequence', ','.join(str(c) for c in cmids))}\n"
            f"  {el('visible', visible)}\n"
            f'  <availabilityjson>{{"op":"&amp;","c":[],"showc":[]}}</availabilityjson>\n'
            f"  {el('timemodified', self.now)}\n"
            f"{tiles_extra}"
            f"</section>"
        )
        self.add_xml(f"sections/section_{sec_id}/section.xml", body)
        if filerefs:
            fr = "".join(
                f"    <file>\n      <id>{fid}</id>\n    </file>\n"
                for fid in filerefs
            )
            inforef = f"<inforef>\n  <fileref>\n{fr}  </fileref>\n</inforef>"
        else:
            inforef = "<inforef>\n</inforef>"
        self.add_xml(f"sections/section_{sec_id}/inforef.xml", inforef)

    def _build_activity(self, act: dict, sec_id: int, sec_number: int) -> int:
        mod = act["type"]
        if mod not in ACTIVITY_BUILDERS:
            raise ValueError(
                f"Unsupported activity type {mod!r}. "
                f"Supported: {', '.join(sorted(ACTIVITY_BUILDERS))}"
            )
        cmid = self.ids.cmid()
        instance = self.ids.instance()
        modctx = self.ids.modctx()
        directory = f"activities/{mod}_{cmid}"

        # type-specific main file + any side effects (files, questions, inforef)
        ctx = ActivityContext(self, act, mod, cmid, instance, modctx, directory, sec_id)
        inner = ACTIVITY_BUILDERS[mod](ctx)
        self.add_xml(
            f"{directory}/{mod}.xml",
            f'<activity id="{instance}" moduleid="{cmid}" '
            f'modulename="{mod}" contextid="{modctx}">\n{inner}\n</activity>',
        )
        # If the activity carries user data (e.g. glossary entries), enable the
        # matching userinfo settings so the data is actually restored.
        if ctx.userrefs:
            self.userinfo_activities.add(f"{mod}_{cmid}")
            self.userinfo_sections.add(sec_id)

        # generic wrapper files (identical schema for every activity type)
        self._build_module_xml(act, mod, cmid, sec_id, sec_number, directory)
        self.add_xml(f"{directory}/inforef.xml", ctx.inforef_xml())
        self.add_xml(
            f"{directory}/roles.xml",
            "<roles>\n  <role_overrides>\n  </role_overrides>\n"
            "  <role_assignments>\n  </role_assignments>\n</roles>",
        )
        self.add_xml(
            f"{directory}/grades.xml",
            "<activity_gradebook>\n  <grade_items>\n  </grade_items>\n"
            "  <grade_letters>\n  </grade_letters>\n</activity_gradebook>",
        )
        self.add_xml(
            f"{directory}/grade_history.xml",
            "<grade_history>\n  <grade_grades>\n  </grade_grades>\n</grade_history>",
        )
        self.add_xml(f"{directory}/calendar.xml", "<events>\n</events>")
        self.add_xml(
            f"{directory}/filters.xml",
            "<filters>\n  <filter_actives>\n  </filter_actives>\n"
            "  <filter_configs>\n  </filter_configs>\n</filters>",
        )
        # assign reads grading.xml (advanced grading areas); empty is fine.
        if mod == "assign":
            self.add_xml(f"{directory}/grading.xml", "<areas>\n</areas>")

        self.backup_activities.append(
            {
                "moduleid": cmid,
                "sectionid": sec_id,
                "modulename": mod,
                "title": act.get("name", mod),
                "directory": directory,
                "activity_key": f"{mod}_{cmid}",
            }
        )
        return cmid

    def _build_module_xml(
        self,
        act: dict,
        mod: str,
        cmid: int,
        sec_id: int,
        sec_number: int,
        directory: str,
    ) -> None:
        completion = act.get("completion", 0)
        body = (
            f'<module id="{cmid}" version="{MODULE_VERSION}">\n'
            f"  {el('modulename', mod)}\n"
            f"  {el('sectionid', sec_id)}\n"
            f"  {el('sectionnumber', sec_number)}\n"
            f"  <idnumber>{xesc(act.get('idnumber', ''))}</idnumber>\n"
            f"  {el('added', self.now)}\n"
            f"  {el('score', 0)}\n"
            f"  {el('indent', act.get('indent', 0))}\n"
            f"  {el('visible', act.get('visible', 1))}\n"
            f"  {el('visibleoncoursepage', 1)}\n"
            f"  {el('visibleold', act.get('visible', 1))}\n"
            f"  {el('groupmode', 0)}\n"
            f"  {el('groupingid', 0)}\n"
            f"  {el('completion', completion)}\n"
            f"  <completiongradeitemnumber>{NULL}</completiongradeitemnumber>\n"
            f"  {el('completionpassgrade', 0)}\n"
            f"  {el('completionview', 0)}\n"
            f"  {el('completionexpected', 0)}\n"
            f"  <availability>{NULL}</availability>\n"
            f"  {el('showdescription', act.get('showdescription', 0))}\n"
            f"  {el('downloadcontent', 1)}\n"
            f"  <lang></lang>\n"
            f"  <tags>\n  </tags>\n"
            f"</module>"
        )
        self.add_xml(f"{directory}/module.xml", body)

    # ----- course ------------------------------------------------------- #
    def _build_course(self) -> None:
        c = self.spec.get("course", {})
        cid = self.ids.course_id
        ctxid = self.ids.course_contextid
        fmt = c.get("format", "topics")
        startdate = c.get("startdate") or self.now
        enddate = c.get("enddate", 0)
        numsections = max(len(self.spec.get("sections", [])) - 1, 0)

        fmt_options = self._course_format_options(fmt, numsections)
        body = (
            f'<course id="{cid}" contextid="{ctxid}">\n'
            f"  {el('shortname', c.get('shortname', 'COURSE'))}\n"
            f"  {el('fullname', c.get('fullname', 'Course'))}\n"
            f"  <idnumber></idnumber>\n"
            f"  {el('summary', c.get('summary', ''))}\n"
            f"  {el('summaryformat', 1)}\n"
            f"  {el('format', fmt)}\n"
            f"  {el('showgrades', 1)}\n"
            f"  {el('newsitems', 5)}\n"
            f"  {el('startdate', startdate)}\n"
            f"  {el('enddate', enddate)}\n"
            f"  {el('marker', 0)}\n"
            f"  {el('maxbytes', 0)}\n"
            f"  {el('legacyfiles', 0)}\n"
            f"  {el('showreports', 0)}\n"
            f"  {el('visible', c.get('visible', 1))}\n"
            f"  {el('groupmode', 0)}\n"
            f"  {el('groupmodeforce', 0)}\n"
            f"  {el('defaultgroupingid', 0)}\n"
            f"  <lang></lang>\n"
            f"  <theme></theme>\n"
            f"  {el('timecreated', self.now)}\n"
            f"  {el('timemodified', self.now)}\n"
            f"  {el('requested', 0)}\n"
            f"  {el('showactivitydates', 1)}\n"
            f"  {el('showcompletionconditions', 1)}\n"
            f"  {el('enablecompletion', 1)}\n"
            f"  {el('completionnotify', 0)}\n"
            f'  <category id="44">\n'
            f"    {el('name', c.get('category_name', 'Miscellaneous'))}\n"
            f"    <description></description>\n"
            f"  </category>\n"
            f"  <tags>\n  </tags>\n"
            f"  <customfields>\n  </customfields>\n"
            f"  <courseformatoptions>\n{fmt_options}  </courseformatoptions>\n"
            # format_tiles: Dummy-Element verbindet das Restore-Plugin des
            # Kachelformats (aktiviert dessen after_restore_course-Aufräumen).
            + ("  <plugin_format_tiles_course>\n"
               "    <dummycourse></dummycourse>\n"
               "  </plugin_format_tiles_course>\n" if fmt == "tiles" else "")
            + f"</course>"
        )
        self.add_xml("course/course.xml", body)

        # enrolments: the three instances Moodle creates for every course.
        self.add_xml("course/enrolments.xml", self._enrolments_xml())
        # course-level question category reference (filled in _build_top_level)
        self._course_inforef_pending = True
        self.add_xml(
            "course/roles.xml",
            "<roles>\n  <role_overrides>\n  </role_overrides>\n"
            "  <role_assignments>\n  </role_assignments>\n</roles>",
        )
        self.add_xml(
            "course/filters.xml",
            "<filters>\n  <filter_actives>\n  </filter_actives>\n"
            "  <filter_configs>\n  </filter_configs>\n</filters>",
        )
        self.add_xml("course/calendar.xml", "<events>\n</events>")
        self.add_xml(
            "course/completiondefaults.xml",
            "<course_completion_defaults>\n</course_completion_defaults>",
        )
        self.add_xml("course/contentbank.xml", "<contents>\n</contents>")

    def _course_format_options(self, fmt: str, numsections: int) -> str:
        """Format-specific options. topics/weeks share the same set; tiles has
        its own. Each option: format, sectionid(0=course-wide), name, value."""
        if fmt == "tiles":
            opts = [
                ("basecolour", "#1670CC"),
                ("coursedisplay", "0"),
                ("courseshowtileprogress", "0"),
                ("courseusebarforheadings", "1"),
                ("courseusesubtiles", "0"),
                ("defaulttileicon", "pie-chart"),
                ("displayfilterbar", "0"),
                ("hiddensections", "1"),
                ("usesubtilesseczero", "0"),
            ]
        else:  # topics / weeks
            opts = [
                ("hiddensections", "1"),
                ("coursedisplay", "0"),
            ]
        out = []
        for name, value in opts:
            out.append(
                "    <courseformatoption>\n"
                f"      {el('format', fmt)}\n"
                f"      {el('sectionid', 0)}\n"
                f"      {el('name', name)}\n"
                f"      {el('value', value)}\n"
                "    </courseformatoption>\n"
            )
        return "".join(out)

    def _enrolments_xml(self) -> str:
        def enrol(eid, method, status, roleid, extra=""):
            return (
                f'    <enrol id="{eid}">\n'
                f"      {el('enrol', method)}\n"
                f"      {el('status', status)}\n"
                f"      <name>{NULL}</name>\n"
                f"      {el('enrolperiod', 0)}\n"
                f"      {el('enrolstartdate', 0)}\n"
                f"      {el('enrolenddate', 0)}\n"
                f"      {el('expirynotify', 0)}\n"
                f"      {el('expirythreshold', 0)}\n"
                f"      {el('notifyall', 0)}\n"
                f"      <password></password>\n"
                f"      <cost></cost>\n"
                f"      <currency></currency>\n"
                f"      {el('roleid', roleid)}\n"
                f"{extra}"
                f"      <customint1>{NULL}</customint1>\n"
                f"      <customint2>{NULL}</customint2>\n"
                f"      <customint3>{NULL}</customint3>\n"
                f"      <customint4>{NULL}</customint4>\n"
                f"      <customint5>{NULL}</customint5>\n"
                f"      <customint6>{NULL}</customint6>\n"
                f"      <customint7>{NULL}</customint7>\n"
                f"      <customint8>{NULL}</customint8>\n"
                f"      <customchar1>{NULL}</customchar1>\n"
                f"      <customchar2>{NULL}</customchar2>\n"
                f"      <customchar3>{NULL}</customchar3>\n"
                f"      <customdec1>{NULL}</customdec1>\n"
                f"      <customdec2>{NULL}</customdec2>\n"
                f"      <customtext1>{NULL}</customtext1>\n"
                f"      <customtext2>{NULL}</customtext2>\n"
                f"      <customtext3>{NULL}</customtext3>\n"
                f"      <customtext4>{NULL}</customtext4>\n"
                f"      {el('timecreated', self.now)}\n"
                f"      {el('timemodified', self.now)}\n"
                f"      <user_enrolments>\n      </user_enrolments>\n"
                f"    </enrol>\n"
            )

        body = (
            "<enrolments>\n  <enrols>\n"
            + enrol(543, "manual", 0, 5)
            + enrol(544, "guest", 1, 0)
            + enrol(545, "self", 1, 5)
            + "  </enrols>\n</enrolments>"
        )
        return body

    # ----- top-level files ---------------------------------------------- #
    def _build_top_level(self) -> None:
        # files.xml (collected from resource/folder activities)
        self.add_xml("files.xml", self._files_xml())
        # questions.xml (collected from quizzes)
        self.add_xml("questions.xml", self._questions_xml())
        # course/inforef.xml references the question categories + student role
        self.add_xml("course/inforef.xml", self._course_inforef_xml())

        self.add_xml("groups.xml", "<groups>\n  <groupings>\n  </groupings>\n</groups>")
        self.add_xml("completion.xml", "<course_completion>\n</course_completion>")
        self.add_xml("scales.xml", "<scales_definition>\n</scales_definition>")
        self.add_xml("outcomes.xml", "<outcomes_definition>\n</outcomes_definition>")
        self.add_xml(
            "roles.xml",
            "<roles_definition>\n"
            '  <role id="5">\n'
            "    <name></name>\n"
            "    <shortname>student</shortname>\n"
            f"    <nameincourse>{NULL}</nameincourse>\n"
            "    <description></description>\n"
            "    <sortorder>5</sortorder>\n"
            "    <archetype>student</archetype>\n"
            "  </role>\n"
            "</roles_definition>",
        )
        if self.has_userdata:
            self.add_xml("users.xml", self._users_xml())
        self.add_file("moodle_backup.log", "")

    def _users_xml(self) -> str:
        parts = ["<users>"]
        for u in self.users.values():
            parts.append(
                f'  <user id="{u["id"]}" contextid="{u["contextid"]}">\n'
                f"    {el('username', u['username'])}\n"
                f"    <idnumber></idnumber>\n"
                f"    {el('email', u['email'])}\n"
                f"    <phone1></phone1>\n    <phone2></phone2>\n"
                f"    <institution></institution>\n    <department></department>\n"
                f"    <address></address>\n    <city></city>\n    <country>DE</country>\n"
                f"    <lastip></lastip>\n    <picture>0</picture>\n"
                f"    <description>{NULL}</description>\n    <descriptionformat>1</descriptionformat>\n"
                f"    <imagealt>{NULL}</imagealt>\n    <auth>manual</auth>\n"
                f"    {el('firstname', u['firstname'])}\n"
                f"    {el('lastname', u['lastname'])}\n"
                f"    <firstnamephonetic></firstnamephonetic>\n    <lastnamephonetic></lastnamephonetic>\n"
                f"    <middlename></middlename>\n    <alternatename></alternatename>\n"
                # mnethosturl MUSS $@NULL@$ sein: eine gesetzte URL (ungleich der
                # Ziel-Site) macht den Autor zum MNet-REMOTE-User, den Moodle beim
                # Restore nicht anlegen darf -> User verworfen -> Glossar leer.
                f"    <mnethosturl>{NULL}</mnethosturl>\n"
                f"    <confirmed>1</confirmed>\n    <policyagreed>0</policyagreed>\n    <deleted>0</deleted>\n"
                f"    <lang>de</lang>\n    <theme></theme>\n    <timezone>99</timezone>\n"
                f"    {el('firstaccess', self.now)}\n    {el('lastaccess', self.now)}\n"
                f"    {el('lastlogin', self.now)}\n    {el('currentlogin', self.now)}\n"
                f"    <mailformat>1</mailformat>\n    <maildigest>0</maildigest>\n    <maildisplay>2</maildisplay>\n"
                f"    <autosubscribe>1</autosubscribe>\n    <trackforums>0</trackforums>\n"
                f"    {el('timecreated', self.now)}\n    {el('timemodified', self.now)}\n"
                f"    <trustbitmask>0</trustbitmask>\n"
                f"    <custom_fields>\n    </custom_fields>\n"
                f"    <tags>\n    </tags>\n"
                f"    <preferences>\n    </preferences>\n"
                f"    <roles>\n      <role_overrides>\n      </role_overrides>\n"
                f"      <role_assignments>\n      </role_assignments>\n    </roles>\n"
                f"  </user>"
            )
        parts.append("</users>")
        return "\n".join(parts)

    def _files_xml(self) -> str:
        if not self.file_records:
            return "<files>\n</files>"
        parts = ["<files>"]
        for f in self.file_records:
            parts.append(
                f'  <file id="{f["id"]}">\n'
                f"    {el('contenthash', f['contenthash'])}\n"
                f"    {el('contextid', f['contextid'])}\n"
                f"    {el('component', f['component'])}\n"
                f"    {el('filearea', f['filearea'])}\n"
                f"    {el('itemid', f['itemid'])}\n"
                f"    {el('filepath', f['filepath'])}\n"
                f"    {el('filename', f['filename'])}\n"
                f"    {el('userid', 2)}\n"
                f"    {el('filesize', f['filesize'])}\n"
                f"    {el('mimetype', f['mimetype']) if f['mimetype'] else '<mimetype>' + NULL + '</mimetype>'}\n"
                f"    {el('status', 0)}\n"
                f"    {el('timecreated', self.now)}\n"
                f"    {el('timemodified', self.now)}\n"
                f"    {el('source', f['source']) if f['source'] else '<source>' + NULL + '</source>'}\n"
                f"    <author>{NULL}</author>\n"
                f"    <license>{NULL}</license>\n"
                f"    {el('sortorder', f['sortorder'])}\n"
                f"    <repositorytype>{NULL}</repositorytype>\n"
                f"    <repositoryid>{NULL}</repositoryid>\n"
                f"    <reference>{NULL}</reference>\n"
                f"  </file>"
            )
        parts.append("</files>")
        return "\n".join(parts)

    def _questions_xml(self) -> str:
        if not self.question_categories:
            return "<question_categories>\n</question_categories>"
        parts = ["<question_categories>"]
        for cat in self.question_categories:
            parts.append(cat["xml"])
        parts.append("</question_categories>")
        return "\n".join(parts)

    def _course_inforef_xml(self) -> str:
        parts = ["<inforef>", "  <roleref>", "    <role>", "      <id>5</id>",
                 "    </role>", "  </roleref>"]
        if self.course_question_catref:
            parts.append("  <question_categoryref>")
            for qid in self.course_question_catref:
                parts.append("    <question_category>")
                parts.append(f"      <id>{qid}</id>")
                parts.append("    </question_category>")
            parts.append("  </question_categoryref>")
        parts.append("</inforef>")
        return "\n".join(parts)

    # ----- moodle_backup.xml -------------------------------------------- #
    def _build_moodle_backup_xml(self) -> None:
        c = self.spec.get("course", {})
        filename = self.spec.get("filename", "backup-moodle2-course.mbz")
        backup_id = hashlib.md5(
            f"{c.get('shortname','')}{self.now}".encode()
        ).hexdigest()
        site_hash = hashlib.md5(self.wwwroot.encode()).hexdigest()

        acts = "".join(
            "        <activity>\n"
            f"          {el('moduleid', a['moduleid'])}\n"
            f"          {el('sectionid', a['sectionid'])}\n"
            f"          {el('modulename', a['modulename'])}\n"
            f"          {el('title', a['title'])}\n"
            f"          {el('directory', a['directory'])}\n"
            "        </activity>\n"
            for a in self.backup_activities
        )
        secs = "".join(
            "        <section>\n"
            f"          {el('sectionid', s['sectionid'])}\n"
            f"          {el('title', s['title'])}\n"
            f"          {el('directory', s['directory'])}\n"
            "        </section>\n"
            for s in self.backup_sections
        )

        users_val = 1 if self.has_userdata else 0
        root_settings = [
            ("filename", filename), ("imscc11", 0), ("users", users_val), ("anonymize", 0),
            ("role_assignments", 0), ("activities", 1), ("blocks", 1), ("files", 1),
            ("filters", 1), ("comments", 0), ("badges", 0), ("calendarevents", 1),
            ("userscompletion", 0), ("logs", 0), ("grade_histories", 0),
            ("questionbank", 1), ("groups", 1), ("competencies", 0),
            ("customfield", 1), ("contentbankcontent", 1), ("legacyfiles", 1),
        ]
        settings = "".join(
            "      <setting>\n"
            f"        <level>root</level>\n"
            f"        {el('name', n)}\n"
            f"        {el('value', v)}\n"
            "      </setting>\n"
            for n, v in root_settings
        )
        for s in self.backup_sections:
            key = f"section_{s['sectionid']}"
            uinfo = 1 if s["sectionid"] in self.userinfo_sections else 0
            for suffix, val in (("included", 1), ("userinfo", uinfo)):
                settings += (
                    "      <setting>\n        <level>section</level>\n"
                    f"        {el('section', key)}\n"
                    f"        {el('name', key + '_' + suffix)}\n"
                    f"        {el('value', val)}\n      </setting>\n"
                )
        for a in self.backup_activities:
            key = a["activity_key"]
            uinfo = 1 if key in self.userinfo_activities else 0
            for suffix, val in (("included", 1), ("userinfo", uinfo)):
                settings += (
                    "      <setting>\n        <level>activity</level>\n"
                    f"        {el('activity', key)}\n"
                    f"        {el('name', key + '_' + suffix)}\n"
                    f"        {el('value', val)}\n      </setting>\n"
                )

        body = (
            "<moodle_backup>\n"
            "  <information>\n"
            f"    {el('name', filename)}\n"
            f"    {el('moodle_version', MOODLE_VERSION)}\n"
            f"    {el('moodle_release', MOODLE_RELEASE)}\n"
            f"    {el('backup_version', BACKUP_VERSION)}\n"
            f"    {el('backup_release', BACKUP_RELEASE)}\n"
            f"    {el('backup_date', self.now)}\n"
            f"    {el('mnet_remoteusers', 0)}\n"
            f"    {el('include_files', 1)}\n"
            f"    {el('include_file_references_to_external_content', 0)}\n"
            f"    {el('original_wwwroot', self.wwwroot)}\n"
            f"    {el('original_site_identifier_hash', site_hash)}\n"
            f"    {el('original_course_id', self.ids.course_id)}\n"
            f"    {el('original_course_format', c.get('format', 'topics'))}\n"
            f"    {el('original_course_fullname', c.get('fullname', 'Course'))}\n"
            f"    {el('original_course_shortname', c.get('shortname', 'COURSE'))}\n"
            f"    {el('original_course_startdate', c.get('startdate') or self.now)}\n"
            f"    {el('original_course_enddate', c.get('enddate', 0))}\n"
            f"    {el('original_course_contextid', self.ids.course_contextid)}\n"
            f"    {el('original_system_contextid', 1)}\n"
            "    <details>\n"
            f'      <detail backup_id="{backup_id}">\n'
            "        <type>course</type>\n"
            "        <format>moodle2</format>\n"
            "        <interactive>1</interactive>\n"
            "        <mode>10</mode>\n"
            "        <execution>1</execution>\n"
            "        <executiontime>0</executiontime>\n"
            "      </detail>\n"
            "    </details>\n"
            "    <contents>\n"
            f"      <activities>\n{acts}      </activities>\n"
            f"      <sections>\n{secs}      </sections>\n"
            "      <course>\n"
            f"        {el('courseid', self.ids.course_id)}\n"
            f"        {el('title', c.get('shortname', 'COURSE'))}\n"
            "        <directory>course</directory>\n"
            "      </course>\n"
            "    </contents>\n"
            f"    <settings>\n{settings}    </settings>\n"
            "  </information>\n"
            "</moodle_backup>"
        )
        self.add_xml("moodle_backup.xml", body)

    # ----- packaging ----------------------------------------------------- #
    def _pack(self) -> bytes:
        # Build .ARCHIVE_INDEX matching the (dir+file) entry order.
        index_lines = [f"Moodle archive file index. Count: {len(self.entries)}"]
        for path, is_dir in self.entries:
            if is_dir:
                index_lines.append(f"{path}\td\t0\t?")
            else:
                size = len(self.files[path])
                index_lines.append(f"{path}\tf\t{size}\t{self.now}")
        index_content = "\n".join(index_lines) + "\n"

        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            self._add_tar(tar, ".ARCHIVE_INDEX", index_content.encode("utf-8"))
            for path, is_dir in self.entries:
                if is_dir:
                    info = tarfile.TarInfo(path)
                    info.type = tarfile.DIRTYPE
                    info.mode = 0o755
                    info.mtime = self.now
                    tar.addfile(info)
                else:
                    self._add_tar(tar, path, self.files[path])
        return buf.getvalue()

    def _add_tar(self, tar: tarfile.TarFile, path: str, data: bytes) -> None:
        info = tarfile.TarInfo(path)
        info.size = len(data)
        info.mode = 0o644
        info.mtime = self.now
        tar.addfile(info, io.BytesIO(data))


# --------------------------------------------------------------------------- #
# Activity context + per-type builders ("templates")
# --------------------------------------------------------------------------- #
class ActivityContext:
    """Carries everything a type-builder needs and lets it register side effects
    (embedded files, question categories) back on the builder."""

    def __init__(self, b: MbzBuilder, act, mod, cmid, instance, modctx, directory,
                 sec_id=None):
        self.b = b
        self.act = act
        self.mod = mod
        self.cmid = cmid
        self.instance = instance
        self.modctx = modctx
        self.directory = directory
        self.sec_id = sec_id
        self.filerefs: list[int] = []  # file ids referenced by this activity
        self.userrefs: list[int] = []  # user ids referenced by this activity

    # -- embedded files (resource/folder) -------------------------------- #
    def add_file(self, path_on_disk: str, filearea: str) -> None:
        with open(path_on_disk, "rb") as fh:
            data = fh.read()
        contenthash = hashlib.sha1(data).hexdigest()
        filename = os.path.basename(path_on_disk)
        # physical content (deduplicated by hash; only written once)
        store_path = f"files/{contenthash[:2]}/{contenthash}"
        if store_path not in self.b.files:
            self.b.add_raw(store_path, data)
        # directory record for this filearea (empty-file sha1) — only once per
        # filearea, so a page with several images doesn't emit duplicate "."
        dirkey = (self.modctx, f"mod_{self.mod}", filearea, 0)
        if dirkey not in self.b._fileareadirs:
            self.b._fileareadirs.add(dirkey)
            empty_hash = "da39a3ee5e6b4b0d3255bfef95601890afd80709"
            dir_id = self.b.ids.fileid()
            self.b.file_records.append({
                "id": dir_id, "contenthash": empty_hash, "contextid": self.modctx,
                "component": f"mod_{self.mod}", "filearea": filearea, "itemid": 0,
                "filepath": "/", "filename": ".", "filesize": 0, "mimetype": None,
                "source": None, "sortorder": 0,
            })
            self.filerefs.append(dir_id)
        # the file record
        file_id = self.b.ids.fileid()
        self.b.file_records.append({
            "id": file_id, "contenthash": contenthash, "contextid": self.modctx,
            "component": f"mod_{self.mod}", "filearea": filearea, "itemid": 0,
            "filepath": "/", "filename": filename, "filesize": len(data),
            "mimetype": _guess_mime(filename), "source": filename, "sortorder": 1,
        })
        self.filerefs.append(file_id)

    # -- question categories (quiz) -------------------------------------- #
    def register_quiz_questions(self, questions: list[dict]) -> tuple[int, list[dict]]:
        """Create the quiz's question categories AT THE QUIZ MODULE CONTEXT
        (contextlevel 70), the way real Moodle 4.x stores quiz-owned questions.

        Each quiz gets its OWN root 'top' category plus a child category that
        holds the questions, both at this quiz's module context — so the category
        contextid is UNIQUE per quiz and matches the question_reference
        ``usingcontextid``. Lumping every quiz's questions into one shared
        COURSE-context bank (all categories at contextid=course) is what made
        restore abort with "A required parameter (contextid) was missing": the
        4.x question-bank restore (restore_move_module_questions_categories)
        expects module-owned questions to live at the module context, then moves
        them into the recreated module once its context mapping exists.

        Returns (child_categoryid, [ {slot, qbe_id, maxmark} ... ]) for quiz slots."""
        b = self.b
        site = b.wwwroot.replace("https://", "").replace("http://", "")
        # Per-quiz root 'top' category at the MODULE context (parent = 0). One
        # 'top' per context is exactly what Moodle's restore enforces, and each
        # quiz module context is its own context, so this stays valid.
        top_id = b.ids.qcat()
        top_stamp = f"{site}+{b.now}+top{top_id}"
        top_xml = (
            f'  <question_category id="{top_id}">\n'
            f"    <name>top</name>\n"
            f"    <contextid>{self.modctx}</contextid>\n"
            f"    <contextlevel>70</contextlevel>\n"
            f"    <contextinstanceid>{self.cmid}</contextinstanceid>\n"
            f"    <info></info>\n    <infoformat>0</infoformat>\n"
            f"    <stamp>{top_stamp}</stamp>\n    <parent>0</parent>\n"
            f"    <sortorder>0</sortorder>\n    <idnumber>{NULL}</idnumber>\n"
            f"    <question_bank_entries>\n    </question_bank_entries>\n"
            f"  </question_category>"
        )
        # 'top' must precede its child in questions.xml.
        b.question_categories.append({"id": top_id, "xml": top_xml})
        # expose for the quiz's inforef annotation (b_quiz reads this)
        self.quiz_top_catid = top_id
        cat_id = b.ids.qcat()
        entries_xml = []
        slots = []
        for i, q in enumerate(questions, start=1):
            qbe_id = b.ids.qbe()
            qver_id = b.ids.qver()
            qid = b.ids.question()
            stamp = f"{site}+{b.now}+q{qid}"
            qxml = self._question_xml(q, qid, stamp)
            entries_xml.append(
                f'      <question_bank_entry id="{qbe_id}">\n'
                f"        <questioncategoryid>{cat_id}</questioncategoryid>\n"
                f"        <idnumber>{NULL}</idnumber>\n"
                f"        <ownerid>2</ownerid>\n"
                f"        <question_version>\n"
                f'          <question_versions id="{qver_id}">\n'
                f"            <version>1</version>\n"
                f"            <status>ready</status>\n"
                f"            <questions>\n{qxml}\n            </questions>\n"
                f"          </question_versions>\n"
                f"        </question_version>\n"
                f"      </question_bank_entry>"
            )
            slots.append({"slot": i, "qbe_id": qbe_id, "maxmark": q.get("defaultmark", 1)})
        cat_stamp = f"{site}+{b.now}+cat{cat_id}"
        cat_xml = (
            f'  <question_category id="{cat_id}">\n'
            f"    <name>{xesc(self.act.get('name','Quiz'))} Questions</name>\n"
            f"    <contextid>{self.modctx}</contextid>\n"
            f"    <contextlevel>70</contextlevel>\n"
            f"    <contextinstanceid>{self.cmid}</contextinstanceid>\n"
            f"    <info></info>\n    <infoformat>0</infoformat>\n"
            f"    <stamp>{cat_stamp}</stamp>\n    <parent>{top_id}</parent>\n"
            f"    <sortorder>999</sortorder>\n    <idnumber>{NULL}</idnumber>\n"
            f"    <question_bank_entries>\n" + "\n".join(entries_xml) + "\n"
            f"    </question_bank_entries>\n"
            f"  </question_category>"
        )
        b.question_categories.append({"id": cat_id, "xml": cat_xml})
        # NOTE: module-context categories are annotated ONLY in this quiz's own
        # inforef.xml (top + child), exactly like real Moodle backups. The
        # course inforef references only course-context categories — listing
        # module categories there deviates from real backups.
        return cat_id, slots

    def _question_xml(self, q: dict, qid: int, stamp: str) -> str:
        b = self.b
        qtype = q.get("type", "truefalse")
        common = (
            f'              <question id="{qid}">\n'
            f"                <parent>0</parent>\n"
            f"                {el('name', q.get('name', 'Question'))}\n"
            f"                {el('questiontext', q.get('questiontext', ''))}\n"
            f"                <questiontextformat>1</questiontextformat>\n"
            f"                {el('generalfeedback', q.get('generalfeedback', ''))}\n"
            f"                <generalfeedbackformat>1</generalfeedbackformat>\n"
            f"                <defaultmark>{float(q.get('defaultmark',1)):.7f}</defaultmark>\n"
            f"                <penalty>0.3333333</penalty>\n"
            f"                {el('qtype', qtype)}\n"
            f"                <length>1</length>\n"
            f"                <stamp>{stamp}</stamp>\n"
            f"                {el('timecreated', b.now)}\n"
            f"                {el('timemodified', b.now)}\n"
            f"                <createdby>2</createdby>\n"
            f"                <modifiedby>2</modifiedby>\n"
        )
        if qtype == "truefalse":
            correct = bool(q.get("correct", True))
            # Per-answer feedback: shown depending on which option the learner
            # picks. Map the didactic feedbackcorrect/feedbackwrong onto the
            # True/False answers according to which one is the correct choice.
            fb_correct = q.get("feedbackcorrect", "")
            fb_wrong = q.get("feedbackwrong", "")
            true_fb = fb_correct if correct else fb_wrong
            false_fb = fb_wrong if correct else fb_correct
            ta = b.ids.answer()
            fa = b.ids.answer()
            plugin = (
                f"                <plugin_qtype_truefalse_question>\n"
                f"                  <answers>\n"
                f'                    <answer id="{ta}">\n'
                f"                      <answertext>True</answertext>\n"
                f"                      <answerformat>0</answerformat>\n"
                f"                      <fraction>{1.0 if correct else 0.0:.7f}</fraction>\n"
                f"                      {el('feedback', true_fb)}\n"
                f"                      <feedbackformat>1</feedbackformat>\n"
                f"                    </answer>\n"
                f'                    <answer id="{fa}">\n'
                f"                      <answertext>False</answertext>\n"
                f"                      <answerformat>0</answerformat>\n"
                f"                      <fraction>{0.0 if correct else 1.0:.7f}</fraction>\n"
                f"                      {el('feedback', false_fb)}\n"
                f"                      <feedbackformat>1</feedbackformat>\n"
                f"                    </answer>\n"
                f"                  </answers>\n"
                f'                  <truefalse id="{qid}">\n'
                f"                    <trueanswer>{ta}</trueanswer>\n"
                f"                    <falseanswer>{fa}</falseanswer>\n"
                f"                    <showstandardinstruction>1</showstandardinstruction>\n"
                f"                  </truefalse>\n"
                f"                </plugin_qtype_truefalse_question>\n"
            )
        elif qtype == "multichoice":
            answers = q.get("answers", [])
            ans_xml = []
            for a in answers:
                aid = b.ids.answer()
                frac = 1.0 if a.get("correct") else 0.0
                ans_xml.append(
                    f'                    <answer id="{aid}">\n'
                    f"                      {el('answertext', a.get('text',''))}\n"
                    f"                      <answerformat>1</answerformat>\n"
                    f"                      <fraction>{frac:.7f}</fraction>\n"
                    f"                      {el('feedback', a.get('feedback', ''))}\n"
                    f"                      <feedbackformat>1</feedbackformat>\n"
                    f"                    </answer>"
                )
            single = 1 if sum(1 for a in answers if a.get("correct")) <= 1 else 0
            plugin = (
                f"                <plugin_qtype_multichoice_question>\n"
                f"                  <answers>\n" + "\n".join(ans_xml) + "\n"
                f"                  </answers>\n"
                f'                  <multichoice id="{qid}">\n'
                f"                    <layout>0</layout>\n"
                f"                    <single>{single}</single>\n"
                f"                    <shuffleanswers>1</shuffleanswers>\n"
                f"                    <correctfeedback></correctfeedback>\n"
                f"                    <correctfeedbackformat>1</correctfeedbackformat>\n"
                f"                    <partiallycorrectfeedback></partiallycorrectfeedback>\n"
                f"                    <partiallycorrectfeedbackformat>1</partiallycorrectfeedbackformat>\n"
                f"                    <incorrectfeedback></incorrectfeedback>\n"
                f"                    <incorrectfeedbackformat>1</incorrectfeedbackformat>\n"
                f"                    <answernumbering>abc</answernumbering>\n"
                f"                    <shownumcorrect>1</shownumcorrect>\n"
                f"                    <showstandardinstruction>1</showstandardinstruction>\n"
                f"                  </multichoice>\n"
                f"                </plugin_qtype_multichoice_question>\n"
            )
        else:
            raise ValueError(f"Unsupported question type {qtype!r} (truefalse, multichoice)")

        tail = (
            f"                <plugin_qbank_comment_question>\n"
            f"                  <comments>\n                  </comments>\n"
            f"                </plugin_qbank_comment_question>\n"
            f"                <plugin_qbank_customfields_question>\n"
            f"                  <customfields>\n                  </customfields>\n"
            f"                </plugin_qbank_customfields_question>\n"
            f"                <question_hints>\n                </question_hints>\n"
            f"                <tags>\n                </tags>\n"
            f"              </question>"
        )
        return common + plugin + tail

    def inforef_xml(self) -> str:
        parts = ["<inforef>"]
        if self.filerefs:
            parts.append("  <fileref>")
            for fid in self.filerefs:
                parts.append(f"    <file>\n      <id>{fid}</id>\n    </file>")
            parts.append("  </fileref>")
        if self.userrefs:
            parts.append("  <userref>")
            for uid in self.userrefs:
                parts.append(f"    <user>\n      <id>{uid}</id>\n    </user>")
            parts.append("  </userref>")
        if getattr(self, "question_catref", None):
            parts.append("  <question_categoryref>")
            for qid in self.question_catref:
                parts.append(
                    f"    <question_category>\n      <id>{qid}</id>\n    </question_category>"
                )
            parts.append("  </question_categoryref>")
        parts.append("</inforef>")
        return "\n".join(parts)


def _guess_mime(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return {
        "pdf": "application/pdf", "png": "image/png", "jpg": "image/jpeg",
        "jpeg": "image/jpeg", "gif": "image/gif", "svg": "image/svg+xml",
        "webp": "image/webp", "txt": "text/plain",
        "html": "text/html", "doc": "application/msword", "zip": "application/zip",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "mp4": "video/mp4", "mp3": "audio/mp3",
    }.get(ext, "application/octet-stream")


# ----- the type-specific "templates" (inner XML of <modname>.xml) --------- #
def _intro(act):
    return (
        f"    {el('intro', act.get('intro', ''))}\n"
        f"    {el('introformat', 1)}\n"
    )


def b_label(ctx):
    a = ctx.act
    return (
        f'  <label id="{ctx.instance}">\n'
        f"    {el('name', a.get('name', 'Label'))}\n"
        f"{_intro(a)}"
        f"    {el('timemodified', ctx.b.now)}\n"
        f"  </label>"
    )


def b_page(ctx):
    a = ctx.act
    # Embed images into the page's "content" filearea. Reference them in the
    # HTML via <img src="@@PLUGINFILE@@/<filename>">. Inline <svg> is stripped
    # by Moodle's HTMLPurifier, so embed SVG/PNG as a file and <img> to it.
    for img in a.get("images", []):
        path = img if isinstance(img, str) else img.get("file")
        if path:
            ctx.add_file(path, "content")
    return (
        f'  <page id="{ctx.instance}">\n'
        f"    {el('name', a.get('name', 'Page'))}\n"
        f"{_intro(a)}"
        f"    {el('content', with_attribution(a.get('content', ''), ctx.b.spec))}\n"
        f"    {el('contentformat', 1)}\n"
        f"    {el('legacyfiles', 0)}\n"
        f"    <legacyfileslast>{NULL}</legacyfileslast>\n"
        f"    {el('display', 5)}\n"
        f'    <displayoptions>a:1:{{s:12:&quot;printheading&quot;;i:1;}}</displayoptions>\n'
        f"    {el('revision', 1)}\n"
        f"    {el('timemodified', ctx.b.now)}\n"
        f"  </page>"
    )


def b_url(ctx):
    a = ctx.act
    return (
        f'  <url id="{ctx.instance}">\n'
        f"    {el('name', a.get('name', 'URL'))}\n"
        f"{_intro(a)}"
        f"    {el('externalurl', a.get('externalurl', 'https://moodle.org'))}\n"
        f"    {el('display', 0)}\n"
        f'    <displayoptions>a:1:{{s:10:&quot;printintro&quot;;i:1;}}</displayoptions>\n'
        f"    <parameters>a:0:{{}}</parameters>\n"
        f"    {el('timemodified', ctx.b.now)}\n"
        f"  </url>"
    )


def b_resource(ctx):
    a = ctx.act
    if a.get("file"):
        ctx.add_file(a["file"], "content")
    return (
        f'  <resource id="{ctx.instance}">\n'
        f"    {el('name', a.get('name', 'File'))}\n"
        f"{_intro(a)}"
        f"    {el('tobemigrated', 0)}\n"
        f"    {el('legacyfiles', 0)}\n"
        f"    <legacyfileslast>{NULL}</legacyfileslast>\n"
        f"    {el('display', 0)}\n"
        f'    <displayoptions>a:1:{{s:10:&quot;printintro&quot;;i:1;}}</displayoptions>\n'
        f"    {el('filterfiles', 0)}\n"
        f"    {el('revision', 1)}\n"
        f"    {el('timemodified', ctx.b.now)}\n"
        f"  </resource>"
    )


def b_folder(ctx):
    a = ctx.act
    for f in a.get("files", []):
        ctx.add_file(f, "content")
    return (
        f'  <folder id="{ctx.instance}">\n'
        f"    {el('name', a.get('name', 'Folder'))}\n"
        f"{_intro(a)}"
        f"    {el('revision', 1)}\n"
        f"    {el('timemodified', ctx.b.now)}\n"
        f"    {el('display', 0)}\n"
        f"    {el('showexpanded', 1)}\n"
        f"    {el('showdownloadfolder', 1)}\n"
        f"    {el('forcedownload', 0)}\n"
        f"  </folder>"
    )


def b_book(ctx):
    a = ctx.act
    chapters = []
    for i, ch in enumerate(a.get("chapters", []), start=1):
        chapters.append(
            f'      <chapter id="{ctx.b.ids.instance()}">\n'
            f"        {el('pagenum', i)}\n"
            f"        {el('subchapter', 1 if ch.get('subchapter') else 0)}\n"
            f"        {el('title', ch.get('title', f'Chapter {i}'))}\n"
            f"        {el('content', with_attribution(ch.get('content', ''), ctx.b.spec))}\n"
            f"        {el('contentformat', 1)}\n"
            f"        {el('hidden', 0)}\n"
            f"        {el('timemcreated', ctx.b.now)}\n"  # sic: 'timemcreated'
            f"        {el('timemodified', ctx.b.now)}\n"
            f"        <importsrc></importsrc>\n"
            f"      </chapter>"
        )
    return (
        f'  <book id="{ctx.instance}">\n'
        f"    {el('name', a.get('name', 'Book'))}\n"
        f"{_intro(a)}"
        f"    {el('numbering', 1)}\n"
        f"    {el('navstyle', 1)}\n"
        f"    {el('customtitles', 0)}\n"
        f"    {el('timecreated', ctx.b.now)}\n"
        f"    {el('timemodified', ctx.b.now)}\n"
        f"    <chapters>\n" + "\n".join(chapters) + ("\n" if chapters else "") +
        f"    </chapters>\n"
        f"  </book>"
    )


def b_assign(ctx):
    a = ctx.act
    return (
        f'  <assign id="{ctx.instance}">\n'
        f"    {el('name', a.get('name', 'Assignment'))}\n"
        f"{_intro(a)}"
        f"    {el('alwaysshowdescription', 1)}\n"
        f"    {el('submissiondrafts', 0)}\n"
        f"    {el('sendnotifications', 0)}\n"
        f"    {el('sendlatenotifications', 0)}\n"
        f"    {el('sendstudentnotifications', 1)}\n"
        f"    {el('duedate', a.get('duedate', 0))}\n"
        f"    {el('cutoffdate', 0)}\n"
        f"    {el('gradingduedate', 0)}\n"
        f"    {el('allowsubmissionsfromdate', 0)}\n"
        f"    {el('grade', a.get('grade', 100))}\n"
        f"    {el('timemodified', ctx.b.now)}\n"
        f"    {el('completionsubmit', 0)}\n"
        f"    {el('requiresubmissionstatement', 0)}\n"
        f"    {el('teamsubmission', 0)}\n"
        f"    {el('requireallteammemberssubmit', 0)}\n"
        f"    {el('teamsubmissiongroupingid', 0)}\n"
        f"    {el('blindmarking', 0)}\n"
        f"    {el('hidegrader', 0)}\n"
        f"    {el('revealidentities', 0)}\n"
        f"    {el('attemptreopenmethod', 'none')}\n"
        f"    {el('maxattempts', -1)}\n"
        f"    {el('markingworkflow', 0)}\n"
        f"    {el('markingallocation', 0)}\n"
        f"    {el('preventsubmissionnotingroup', 0)}\n"
        f"    <activity></activity>\n"
        f"    {el('activityformat', 1)}\n"
        f"    {el('timelimit', 0)}\n"
        f"    {el('submissionattachments', 0)}\n"
        f"    <plugin_configs>\n"
        f'      <plugin_config id="1"><plugin>file</plugin><subtype>assignsubmission</subtype><name>enabled</name><value>1</value></plugin_config>\n'
        f'      <plugin_config id="2"><plugin>onlinetext</plugin><subtype>assignsubmission</subtype><name>enabled</name><value>1</value></plugin_config>\n'
        f'      <plugin_config id="3"><plugin>comments</plugin><subtype>assignfeedback</subtype><name>enabled</name><value>1</value></plugin_config>\n'
        f"    </plugin_configs>\n"
        f"  </assign>"
    )


def b_forum(ctx):
    a = ctx.act
    return (
        f'  <forum id="{ctx.instance}">\n'
        f"    {el('type', a.get('forumtype', 'general'))}\n"
        f"    {el('name', a.get('name', 'Forum'))}\n"
        f"{_intro(a)}"
        f"    {el('duedate', 0)}\n    {el('cutoffdate', 0)}\n"
        f"    {el('assessed', 0)}\n    {el('assesstimestart', 0)}\n    {el('assesstimefinish', 0)}\n"
        f"    {el('scale', 0)}\n    {el('maxbytes', 0)}\n    {el('maxattachments', 1)}\n"
        f"    {el('forcesubscribe', 0)}\n    {el('trackingtype', 1)}\n"
        f"    {el('rsstype', 0)}\n    {el('rssarticles', 0)}\n"
        f"    {el('timemodified', ctx.b.now)}\n"
        f"    {el('warnafter', 0)}\n    {el('blockafter', 0)}\n    {el('blockperiod', 0)}\n"
        f"    {el('completiondiscussions', 0)}\n    {el('completionreplies', 0)}\n    {el('completionposts', 0)}\n"
        f"    {el('displaywordcount', 0)}\n    {el('lockdiscussionafter', 0)}\n"
        f"    {el('grade_forum', 0)}\n"
        f"  </forum>"
    )


def b_glossary(ctx):
    a = ctx.act
    # Glossary entries are user data: each needs an author recorded in users.xml
    # and referenced from this activity's inforef.xml (<userref>).
    entries_xml = ""
    raw_entries = a.get("entries", [])
    if raw_entries:
        uid = ctx.b.get_or_create_user(a.get("author") or ctx.b.spec.get("course", {}).get("author"))
        if uid not in ctx.userrefs:
            ctx.userrefs.append(uid)
        rows = []
        for e in raw_entries:
            rows.append(
                f'      <entry id="{ctx.b.ids.instance()}">\n'
                f"        {el('userid', uid)}\n"
                f"        {el('concept', e.get('concept', 'Begriff'))}\n"
                f"        {el('definition', e.get('definition', ''))}\n"
                f"        {el('definitionformat', 1)}\n"
                f"        {el('definitiontrust', 0)}\n"
                f"        <attachment></attachment>\n"
                f"        {el('timecreated', ctx.b.now)}\n"
                f"        {el('timemodified', ctx.b.now)}\n"
                f"        {el('teacherentry', 1)}\n"
                f"        {el('sourceglossaryid', 0)}\n"
                f"        {el('usedynalink', 1)}\n"
                f"        {el('casesensitive', 0)}\n"
                f"        {el('fullmatch', 1)}\n"
                f"        {el('approved', 1)}\n"
                f"        <aliases>\n        </aliases>\n"
                f"        <ratings>\n        </ratings>\n"
                f"      </entry>"
            )
        entries_xml = "\n" + "\n".join(rows) + "\n    "
    return (
        f'  <glossary id="{ctx.instance}">\n'
        f"    {el('name', a.get('name', 'Glossary'))}\n"
        f"{_intro(a)}"
        f"    {el('allowduplicatedentries', 0)}\n"
        f"    {el('displayformat', 'dictionary')}\n"
        f"    {el('mainglossary', 0)}\n"
        f"    {el('showspecial', 1)}\n    {el('showalphabet', 1)}\n    {el('showall', 1)}\n"
        f"    {el('allowcomments', 0)}\n    {el('allowprintview', 1)}\n    {el('usedynalink', 1)}\n"
        f"    {el('defaultapproval', 1)}\n    {el('globalglossary', 0)}\n"
        f"    {el('entbypage', 10)}\n    {el('editalways', 0)}\n"
        f"    {el('rsstype', 0)}\n    {el('rssarticles', 0)}\n"
        f"    {el('assessed', 0)}\n    {el('assesstimestart', 0)}\n    {el('assesstimefinish', 0)}\n"
        f"    {el('scale', 0)}\n"
        f"    {el('timecreated', ctx.b.now)}\n    {el('timemodified', ctx.b.now)}\n"
        f"    {el('completionentries', 0)}\n"
        f"    <entries>{entries_xml}</entries>\n"
        f"    <entriestags>\n    </entriestags>\n"
        f"  </glossary>"
    )


def b_choice(ctx):
    a = ctx.act
    options = []
    for opt in a.get("options", ["Option 1", "Option 2"]):
        options.append(
            f'      <option id="{ctx.b.ids.instance()}">\n'
            f"        {el('text', opt)}\n"
            f"        {el('maxanswers', 0)}\n"
            f"        {el('timemodified', ctx.b.now)}\n"
            f"      </option>"
        )
    return (
        f'  <choice id="{ctx.instance}">\n'
        f"    {el('name', a.get('name', 'Choice'))}\n"
        f"{_intro(a)}"
        f"    {el('publish', 0)}\n    {el('showresults', 0)}\n    {el('display', 0)}\n"
        f"    {el('allowupdate', 0)}\n    {el('allowmultiple', 0)}\n    {el('showunanswered', 0)}\n"
        f"    {el('limitanswers', 0)}\n    {el('timeopen', 0)}\n    {el('timeclose', 0)}\n"
        f"    {el('timemodified', ctx.b.now)}\n    {el('completionsubmit', 0)}\n"
        f"    {el('showpreview', 0)}\n    {el('includeinactive', 0)}\n    {el('showavailable', 0)}\n"
        f"    <options>\n" + "\n".join(options) + "\n    </options>\n"
        f"  </choice>"
    )


def _feedback_item(ctx, it, pos):
    """Build one <item>. Supported types: label, multichoice, textfield,
    textarea, numeric. `presentation` encoding is per Moodle's item plugins."""
    t = it.get("type", "label")
    required = it.get("required", 0)
    if t == "label":
        # name MUST be the empty string, never NULL: mdl_feedback_item.name is
        # NOT NULL DEFAULT '' — a $@NULL@$ here aborts the whole restore with
        # dmlwriteexception "Column 'name' cannot be null" (real bug 2026-07-15,
        # killed everything after the feedback activity).
        name, label, pres, hasvalue = "", f"info{pos}", it.get("text", ""), 0
    elif t == "multichoice":
        # 'r' = radio (single choice); '>>>>>' separates subtype from options,
        # '|' separates options. el() will escape the '>' as &gt;.
        opts = "|".join(it.get("options", ["Option 1", "Option 2"]))
        name, label, pres, hasvalue = it.get("name", "Frage"), f"item{pos}", f"r>>>>>{opts}", 1
    elif t == "textfield":
        size, maxlen = it.get("size", 30), it.get("maxlength", 255)
        name, label, pres, hasvalue = it.get("name", "Eingabe"), f"item{pos}", f"{size}|{maxlen}", 1
    elif t == "textarea":
        cols, rows = it.get("cols", 60), it.get("rows", 5)
        name, label, pres, hasvalue = it.get("name", "Kommentar"), f"item{pos}", f"{cols}|{rows}", 1
    elif t == "numeric":
        rng = f"{it.get('from', '-')}|{it.get('to', '-')}"
        name, label, pres, hasvalue = it.get("name", "Zahl"), f"item{pos}", rng, 1
    else:
        raise ValueError(f"Unsupported feedback item type {t!r} "
                         "(label, multichoice, textfield, textarea, numeric)")
    return (
        f'      <item id="{ctx.b.ids.instance()}">\n'
        f"        {el('template', 0)}\n"
        f"        {el('name', name)}\n"
        f"        {el('label', label)}\n"
        f"        {el('presentation', pres)}\n"
        f"        {el('typ', t)}\n"
        f"        {el('hasvalue', hasvalue)}\n"
        f"        {el('position', pos)}\n"
        f"        {el('required', 1 if required else 0)}\n"
        f"        {el('dependitem', 0)}\n"
        f"        <dependvalue></dependvalue>\n"
        f"        <options></options>\n"
        f"      </item>"
    )


def b_feedback(ctx):
    a = ctx.act
    items = a.get("items", [])
    items_xml = ""
    if items:
        rows = [_feedback_item(ctx, it, i) for i, it in enumerate(items, start=1)]
        items_xml = "\n" + "\n".join(rows) + "\n    "
    return (
        f'  <feedback id="{ctx.instance}">\n'
        f"    {el('name', a.get('name', 'Feedback'))}\n"
        f"{_intro(a)}"
        f"    {el('anonymous', 1)}\n    {el('email_notification', 0)}\n"
        f"    {el('multiple_submit', 0)}\n    {el('autonumbering', 0)}\n"
        f"    <site_after_submit></site_after_submit>\n"
        f"    <page_after_submit></page_after_submit>\n    {el('page_after_submitformat', 1)}\n"
        f"    {el('publish_stats', 0)}\n"
        f"    {el('timeopen', 0)}\n    {el('timeclose', 0)}\n    {el('timemodified', ctx.b.now)}\n"
        f"    {el('completionsubmit', 0)}\n"
        f"    <items>{items_xml}</items>\n"
        f"  </feedback>"
    )


def b_quiz(ctx):
    a = ctx.act
    questions = a.get("questions", [])
    instances_xml = ""
    if questions:
        cat_id, slots = ctx.register_quiz_questions(questions)
        # reference this quiz's own 'top' category and its child category
        # (both at this quiz's module context)
        ctx.question_catref = [ctx.quiz_top_catid, cat_id]
        rows = []
        for s in slots:
            rows.append(
                f'      <question_instance id="{ctx.b.ids.qinstance()}">\n'
                f"        {el('slot', s['slot'])}\n"
                f"        {el('page', s['slot'])}\n"
                f"        {el('requireprevious', 0)}\n"
                f"        <maxmark>{float(s['maxmark']):.7f}</maxmark>\n"
                f'        <question_reference id="{ctx.b.ids.qinstance()}">\n'
                f"          <usingcontextid>{ctx.modctx}</usingcontextid>\n"
                f"          <component>mod_quiz</component>\n"
                f"          <questionarea>slot</questionarea>\n"
                f"          <questionbankentryid>{s['qbe_id']}</questionbankentryid>\n"
                f"          <version>{NULL}</version>\n"
                f"        </question_reference>\n"
                f"      </question_instance>"
            )
        instances_xml = "\n".join(rows)
    grade = a.get("grade", 10)
    sumgrades = float(len(questions)) if questions else 0.0

    # Optional overall feedback with grade boundaries (Feed-Forward). Bands are
    # given as {"min": <percent>, "text": <html>}; converted to point ranges on
    # the quiz's grade scale. Only emitted when provided (keeps default output
    # unchanged). Bands are contiguous: each row covers [min, next-min); the top
    # row's upper bound is grade+1 so a perfect score is included.
    feedbacks_xml = ""
    bands = a.get("overallfeedback", [])
    if bands:
        g = float(grade)
        bands_sorted = sorted(bands, key=lambda x: x.get("min", 0))
        rows_fb = []
        for i, band in enumerate(bands_sorted):
            mn = band.get("min", 0) / 100.0 * g
            mx = (bands_sorted[i + 1].get("min", 0) / 100.0 * g
                  if i + 1 < len(bands_sorted) else g + 1.0)
            rows_fb.append(
                f'      <feedback id="{ctx.b.ids.qinstance()}">\n'
                f"        {el('feedbacktext', band.get('text', ''))}\n"
                f"        <feedbacktextformat>1</feedbacktextformat>\n"
                f"        <mingrade>{mn:.5f}</mingrade>\n"
                f"        <maxgrade>{mx:.5f}</maxgrade>\n"
                f"      </feedback>"
            )
        feedbacks_xml = (
            f"    <feedbacks>\n" + "\n".join(rows_fb) + "\n    </feedbacks>\n"
        )
    return (
        f'  <quiz id="{ctx.instance}">\n'
        f"    {el('name', a.get('name', 'Quiz'))}\n"
        f"{_intro(a)}"
        f"    {el('timeopen', 0)}\n    {el('timeclose', 0)}\n    {el('timelimit', 0)}\n"
        f"    {el('overduehandling', 'autosubmit')}\n    {el('graceperiod', 0)}\n"
        f"    {el('canredoquestions', 0)}\n    {el('preferredbehaviour', 'deferredfeedback')}\n"
        f"    {el('attempts_number', 0)}\n    {el('attemptonlast', 0)}\n"
        f"    {el('grademethod', 1)}\n    {el('decimalpoints', 2)}\n    {el('questiondecimalpoints', -1)}\n"
        f"    {el('reviewattempt', 69888)}\n    {el('reviewcorrectness', 4352)}\n"
        f"    {el('reviewmarks', 4352)}\n    {el('reviewspecificfeedback', 4352)}\n"
        f"    {el('reviewgeneralfeedback', 4352)}\n    {el('reviewrightanswer', 4352)}\n    {el('reviewoverallfeedback', 4352)}\n"
        f"    {el('questionsperpage', 1)}\n    {el('navmethod', 'free')}\n    {el('shuffleanswers', 1)}\n"
        f"    <sumgrades>{sumgrades:.5f}</sumgrades>\n    <grade>{float(grade):.5f}</grade>\n"
        f"    {el('timecreated', ctx.b.now)}\n    {el('timemodified', ctx.b.now)}\n"
        f"    <password></password>\n    <subnet></subnet>\n    {el('browsersecurity', '-')}\n"
        f"    {el('delay1', 0)}\n    {el('delay2', 0)}\n"
        f"    {el('showuserpicture', 0)}\n    {el('showblocks', 0)}\n"
        f"    {el('completionattemptsexhausted', 0)}\n    {el('completionminattempts', 0)}\n"
        f"    {el('allowofflineattempts', 0)}\n"
        f"    <question_instances>\n{instances_xml}\n    </question_instances>\n"
        f'    <sections>\n      <section id="{ctx.b.ids.qinstance()}">\n'
        f"        <firstslot>1</firstslot>\n"
        f"        <heading></heading>\n"
        f"        <shufflequestions>0</shufflequestions>\n"
        f"      </section>\n    </sections>\n"
        f"{feedbacks_xml}"
        f"    <overrides>\n    </overrides>\n"
        f"    <grades>\n    </grades>\n"
        f"    <attempts>\n    </attempts>\n"
        f"  </quiz>"
    )


ACTIVITY_BUILDERS = {
    "label": b_label,
    "page": b_page,
    "url": b_url,
    "resource": b_resource,
    "folder": b_folder,
    "book": b_book,
    "assign": b_assign,
    "forum": b_forum,
    "glossary": b_glossary,
    "choice": b_choice,
    "feedback": b_feedback,
    "quiz": b_quiz,
}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Build a Moodle .mbz from a JSON course spec.")
    p.add_argument("spec", help="Path to course spec JSON file")
    p.add_argument("-o", "--output", required=True, help="Output .mbz path")
    p.add_argument(
        "--wwwroot",
        default="https://moodle.example.edu",
        help="Original site URL recorded in the backup metadata",
    )
    p.add_argument(
        "--strict-svg", action="store_true",
        help="abort the build if an embedded SVG diagram has defects",
    )
    p.add_argument(
        "--no-svg-check", action="store_true",
        help="skip the automatic SVG diagram check",
    )
    args = p.parse_args(argv)

    with open(args.spec, encoding="utf-8") as fh:
        spec = json.load(fh)
    if "filename" not in spec:
        spec["filename"] = os.path.basename(args.output)

    # Automatically check embedded SVG diagrams for clipping / overlaps / tspan
    # traps / tofu glyphs / lines crossing labels, so no build ships a broken
    # diagram unnoticed. Degrades gracefully if the SVG toolchain is absent.
    if not args.no_svg_check:
        try:
            import validate_svg  # same scripts/ dir
            validate_svg.check_course_svgs(
                spec, os.path.dirname(os.path.abspath(args.spec)),
                strict=args.strict_svg)
        except SystemExit:
            raise
        except Exception as e:  # noqa: BLE001 - optional dependency (reportlab)
            print(f"NOTE: SVG diagram check skipped ({e}). "
                  f"Install reportlab to enable it.", file=sys.stderr)

    # Course formats: topics/weeks (built-in) restore reliably. 'tiles'
    # (third-party format_tiles) is now emitted with full plugin fidelity:
    # course-/section-Format-Optionen, Kachel-Foto-Dateien (format_tiles/
    # tilephoto//tilephoto/) und plugin_format_tiles_*-Elemente mit Dummy-
    # Triggern für das Restore-Plugin. Voraussetzung: format_tiles ist auf der
    # Ziel-Site installiert. Andere Drittanbieter-Formate bleiben ungetestet.
    fmt = spec.get("course", {}).get("format", "topics")
    if fmt == "tiles":
        print(
            "NOTE: course format 'tiles' requires the format_tiles plugin on the"
            " target Moodle. Tile photos (section 'image') are wired natively;"
            " if the restore errors, rebuild with format 'topics' as fallback.",
            file=sys.stderr,
        )
    elif fmt not in ("topics", "weeks"):
        print(
            f"WARNING: course format '{fmt}' is a third-party plugin without"
            " dedicated support in this generator; restoring may fail."
            " Recommended: 'topics' (or 'tiles' for Kachel-Fotos).",
            file=sys.stderr,
        )

    builder = MbzBuilder(spec, args.wwwroot)
    data = builder.build()
    with open(args.output, "wb") as fh:
        fh.write(data)

    n_act = len(builder.backup_activities)
    n_sec = len(builder.backup_sections)
    print(
        f"Wrote {args.output} ({len(data)} bytes): "
        f"{n_sec} section(s), {n_act} activity/ies."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
