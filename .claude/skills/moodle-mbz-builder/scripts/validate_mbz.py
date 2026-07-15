#!/usr/bin/env python3
"""Validate a generated .mbz: check it is a gzip tar, every XML file is
well-formed, and the core cross-references in moodle_backup.xml are consistent
with the section/activity files actually present.

Zusätzlich laufen TIEFEN-CHECKS über die Inhalte (alle < 1 s, laufen bei jedem
Build mit — und in der Pipeline idealerweise parallel zur NotebookLM-Video-
Wartezeit, siehe SKILL.md):

  * GLOSSAR-Kette: Einträge vorhanden -> users=1, <mod>_userinfo=1,
    section_userinfo=1, userref, Autor in users.xml mit mnethosturl=$@NULL@$
    (eine gesetzte URL macht den Autor zum MNet-Remote-User -> Restore
    verwirft ihn -> Glossar leer), approved=1, entriestags auf Glossar-Ebene,
    Import-Fallback-Ressource an Bord.
  * KACHELFOTOS (format tiles): tilephoto-Option je Section hat die passende
    Datei (format_tiles/tilephoto, itemid=sectionid, /tilephoto/), Blob im
    Archiv, plugin_format_tiles_section + dummysection, plugin-Element im
    course.xml.
  * ATTRIBUTION: der Entstehungs-Fuß steht am Ende jeder Seite und jedes
    Buch-Kapitels (warn, da per course.attribution abschaltbar).
  * INTERAKTIVE HTML-DATEIEN: Formulare (data-field) haben KEINE
    placeholder-Attribute (leere Antwortfelder!) und tragen Autosave +
    Speichern-Button; Simulationen nutzen das Kompakt-Layout (kein Scrollen).

Usage:  python validate_mbz.py out.mbz
Exit code 0 = all checks passed (warnings allowed), 1 = problems found.
"""

from __future__ import annotations

import html
import re
import sys
import tarfile
import xml.etree.ElementTree as ET


# --- Rechnungs-Heuristik: Ergebnis ohne Einheit (beratend, nie fatal) ------- #
# Einheiten-Token (längste Alternativen zuerst, damit "kV" vor "V" greift).
_UNIT = (r"(?:kV|mV|µV|V|mA|µA|kA|A|kΩ|MΩ|Ω|kW|MW|VA|var|W|kN|Nm|N|hPa|kPa|MPa|Pa|"
         r"mbar|bar|mm|cm|dm|km|µm|nm|m|ms|µs|ns|min|h|s|°C|K|°|kg|mg|µg|g|t|"
         r"kHz|MHz|GHz|Hz|mF|µF|nF|pF|F|mH|µH|H|kWh|Wh|kJ|MJ|J|ml|l|%)")
_UNIT_TOKEN_RX = re.compile(r"(?<![A-Za-zµ°])" + _UNIT + r"(?![A-Za-zµ])")
_RESULT_RX = re.compile(r"=\s*[-+]?\d+(?:[.,]\d+)?")
_RESULT_UNIT_RX = re.compile(r"=\s*[-+]?\d+(?:[.,]\d+)?\s*" + _UNIT + r"(?![A-Za-zµ])")
# dimensionslose Größen (kein Fehlalarm): Wirkungsgrad, Reibzahl, Übersetzung …
_DIMLESS = {"η", "μ", "µ", "ε", "φ", "λ", "i", "z", "cos", "sin", "tan", "cosφ"}


def _readable_text(raw: str) -> str:
    """XML-escapetes HTML -> lesbarer Klartext: entschärfen, Tags strippen,
    Leerraum zusammenfassen."""
    txt = html.unescape(raw)              # &lt;p&gt; -> <p>, &amp; -> &
    txt = re.sub(r"<[^>]+>", " ", txt)    # HTML-Tags entfernen
    return re.sub(r"\s+", " ", txt).strip()


def _calc_unit_warnings(text: str) -> list[str]:
    """Beratend: in einem Rechenkontext (Text mit '=' UND einem Einheiten-Token)
    ein Ergebnis '= <Zahl>' melden, dem KEINE Einheit folgt. Dimensionslose
    Größen (η, i, cos φ …) werden übersprungen. Nie fatal."""
    if "=" not in text or not _UNIT_TOKEN_RX.search(text):
        return []
    out, seen = [], set()
    for m in _RESULT_RX.finditer(text):
        if _RESULT_UNIT_RX.match(text, m.start()):
            continue  # Einheit folgt direkt -> ok
        lhs = text[max(0, m.start() - 12):m.start()].strip()
        sym = re.split(r"[\s(]+", lhs)[-1] if lhs else ""
        if sym in _DIMLESS:
            continue  # dimensionslose Größe
        snip = text[m.start():m.end()].strip()
        if snip not in seen:
            seen.add(snip)
            out.append(snip)
    return out[:5]


def main(path: str) -> int:
    problems: list[str] = []
    info: list[str] = []

    try:
        tar = tarfile.open(path, "r:gz")
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: not a readable gzip tar: {e}")
        return 1

    members = tar.getnames()
    info.append(f"archive entries: {len(members)}")

    # 1. well-formedness of every .xml
    contents: dict[str, str] = {}
    for m in members:
        if m.endswith(".xml"):
            data = tar.extractfile(m).read().decode("utf-8")
            contents[m] = data
            try:
                ET.fromstring(data)
            except ET.ParseError as e:
                problems.append(f"malformed XML in {m}: {e}")

    # 2. moodle_backup.xml must exist
    if "moodle_backup.xml" not in contents:
        problems.append("moodle_backup.xml missing")
        _report(info, [], problems)
        return 1 if problems else 0

    root = ET.fromstring(contents["moodle_backup.xml"])
    # Scope to <contents> so <activity>/<section> in <settings> aren't counted.
    contents_el = root.find("information/contents")
    if contents_el is None:
        problems.append("moodle_backup.xml has no <contents> block")
        _report(info, [], problems)
        return 1

    # 3. every referenced directory must be present
    for act in contents_el.iter("activity"):
        directory = act.findtext("directory")
        modname = act.findtext("modulename")
        if directory and f"{directory}/{modname}.xml" not in contents:
            problems.append(f"activity main file missing: {directory}/{modname}.xml")
        for req in ("module.xml", "inforef.xml", "roles.xml", "grades.xml"):
            if directory and f"{directory}/{req}" not in contents:
                problems.append(f"activity wrapper missing: {directory}/{req}")

    for sec in contents_el.iter("section"):
        directory = sec.findtext("directory")
        if directory and f"{directory}/section.xml" not in contents:
            problems.append(f"section file missing: {directory}/section.xml")

    # 4. sequence cmids must each map to a registered activity
    activity_cmids = {a.findtext("moduleid") for a in contents_el.iter("activity")}
    for m, data in contents.items():
        if re.search(r"sections/section_\d+/section\.xml$", m):
            seq = ET.fromstring(data).findtext("sequence") or ""
            for cmid in [c for c in seq.split(",") if c]:
                if cmid not in activity_cmids:
                    problems.append(
                        f"{m}: sequence references cmid {cmid} with no activity"
                    )

    # 5. files.xml ids referenced by inforef must exist
    if "files.xml" in contents:
        file_ids = {f.get("id") for f in ET.fromstring(contents["files.xml"]).iter("file")}
        for m, data in contents.items():
            if m.endswith("inforef.xml"):
                for fref in ET.fromstring(data).iter("fileref"):
                    for fid in fref.iter("id"):
                        if fid.text not in file_ids:
                            problems.append(f"{m}: fileref id {fid.text} not in files.xml")

    # 6. userref ids referenced by inforef must exist in users.xml
    user_ids = set()
    if "users.xml" in contents:
        user_ids = {u.get("id") for u in ET.fromstring(contents["users.xml"]).iter("user")}
    n_userref = 0
    for m, data in contents.items():
        if m.endswith("inforef.xml"):
            for uref in ET.fromstring(data).iter("userref"):
                for uid in uref.iter("id"):
                    n_userref += 1
                    if uid.text not in user_ids:
                        problems.append(
                            f"{m}: userref id {uid.text} not in users.xml"
                            + ("" if "users.xml" in contents else " (users.xml missing)")
                        )

    # 7. at most one root (parent=0) question category per context — Moodle's
    #    restore rejects "more than one top category" otherwise.
    if "questions.xml" in contents:
        roots: dict[str, int] = {}
        for cat in ET.fromstring(contents["questions.xml"]).iter("question_category"):
            if (cat.findtext("parent") or "").strip() == "0":
                ctxid = cat.findtext("contextid") or "?"
                roots[ctxid] = roots.get(ctxid, 0) + 1
        for ctxid, count in roots.items():
            if count > 1:
                problems.append(
                    f"questions.xml: {count} root (parent=0) categories in context "
                    f"{ctxid}; Moodle allows only one 'top' per context"
                )

    # 8. quiz-owned question categories must live at the quiz MODULE context
    #    (contextlevel 70), with contextid == that quiz's question_reference
    #    usingcontextid. Lumping every quiz's questions into the shared COURSE
    #    context (all categories at the course contextid) makes Moodle's 4.x
    #    question-bank restore abort with "A required parameter (contextid) was
    #    missing" — the qbank machinery expects module-owned questions at the
    #    module context. This guards against that regression.
    if "questions.xml" in contents:
        module_ctx_ids = {
            (cat.findtext("contextid") or "").strip()
            for cat in ET.fromstring(contents["questions.xml"]).iter("question_category")
            if (cat.findtext("contextlevel") or "").strip() == "70"
        }
        for m, data in contents.items():
            if re.match(r"activities/quiz_\d+/quiz\.xml$", m):
                for uc in ET.fromstring(data).iter("usingcontextid"):
                    ucid = (uc.text or "").strip()
                    if ucid and ucid not in module_ctx_ids:
                        problems.append(
                            f"{m}: question_reference usingcontextid {ucid} has no "
                            f"matching module-context (contextlevel=70) question_category "
                            f"in questions.xml — quiz questions must live at the quiz "
                            f"module context; a shared course-context bank makes restore "
                            f"fail with 'required parameter (contextid) was missing'"
                        )
                        break

    info.append(f"activities: {sum(1 for _ in contents_el.iter('activity'))}")
    info.append(f"users: {len(user_ids)}, userrefs: {n_userref}")
    info.append(f"sections: {sum(1 for _ in contents_el.iter('section'))}")

    # 8b. feedback items: name/dependvalue/options are NOT NULL DEFAULT ''
    #     columns in mdl_feedback_item — a $@NULL@$ there aborts the restore
    #     with dmlwriteexception "Column 'name' cannot be null" and kills every
    #     activity after the feedback (real bug 2026-07-15). Must be '' instead.
    for m, data in contents.items():
        if re.match(r"activities/feedback_\d+/feedback\.xml$", m):
            for item in ET.fromstring(data).iter("item"):
                for fieldname in ("name", "dependvalue", "options", "label"):
                    if (item.findtext(fieldname) or "").strip() == "$@NULL@$":
                        problems.append(
                            f"{m}: feedback item <{fieldname}> ist $@NULL@$ — die Spalte "
                            f"ist NOT NULL DEFAULT ''; Restore bricht mit dmlwriteexception "
                            f"ab (leeren String emittieren)"
                        )

    warns: list[str] = []

    # 9. archive/media size — big embedded media (e.g. an MP4 video) makes the
    #    SYNCHRONOUS restore on shared hosting exceed execution/gateway limits.
    #    The restore then dies mid-way (everything before is committed, the tail
    #    activities are missing) and the broken page flow surfaces as
    #    "A required parameter (contextid) was missing". Real school-Moodle
    #    backups are typically a few MB. Warn early instead of failing late.
    total = sum(m.size for m in tar.getmembers())
    big = [(m.name, m.size) for m in tar.getmembers() if m.size > 10 * 1024 * 1024]
    if big or total > 20 * 1024 * 1024:
        detail = ", ".join(f"{n} ({s // (1024*1024)} MB)" for n, s in big) or "-"
        warns.append(
            f"GROESSE: Archiv {total // (1024*1024)} MB, grosse Datei(en): {detail} — "
            f"Restore-Timeout-Risiko auf shared Hosting (Abbruch mittendrin, "
            f"'required parameter contextid missing' als Folgefehler). Grosse Videos "
            f"besser verlinken (set_recap_video.py --url) oder separat hochladen."
        )

    _deep_checks(tar, set(members), contents, problems, warns, info)

    _report(info, warns, problems)
    return 1 if problems else 0


# --------------------------------------------------------------------------- #
# Tiefen-Checks: prüfen die inhaltlichen Ketten der Skill-Features
# --------------------------------------------------------------------------- #
ATTRIBUTION_MARKER = "Labor Didaktik der Technik"


def _deep_checks(tar, members, contents, problems, warns, info):
    mb = contents.get("moodle_backup.xml", "")

    def setting(name):
        m = re.search(rf"<name>{re.escape(name)}</name>\s*<value>(\d+)</value>", mb)
        return m.group(1) if m else None

    # ---- 8. Glossar-Kette (Einträge sind Nutzerdaten) -------------------- #
    n_gloss = 0
    for path, data in contents.items():
        gm = re.match(r"activities/glossary_(\d+)/glossary\.xml$", path)
        if not gm:
            continue
        entries = re.findall(r"<entry id=\"\d+\">", data)
        if not entries:
            continue
        n_gloss += 1
        cmid = gm.group(1)
        tag = f"glossar (cmid {cmid})"
        if setting("users") != "1":
            problems.append(f"{tag}: root-Setting users != 1 — Einträge gehen beim Restore verloren")
        if setting(f"glossary_{cmid}_userinfo") != "1":
            problems.append(f"{tag}: glossary_{cmid}_userinfo != 1")
        secm = re.search(rf"<moduleid>{cmid}</moduleid>\s*<sectionid>(\d+)</sectionid>", mb)
        if secm and setting(f"section_{secm.group(1)}_userinfo") != "1":
            problems.append(f"{tag}: section_{secm.group(1)}_userinfo != 1")
        inf = contents.get(f"activities/glossary_{cmid}/inforef.xml", "")
        if "<userref>" not in inf:
            problems.append(f"{tag}: kein <userref> in der inforef — Autor wird nicht mitgesichert")
        users = contents.get("users.xml", "")
        entry_uids = set(re.findall(r"<userid>(\d+)</userid>", data))
        for uid in entry_uids:
            if f'<user id="{uid}"' not in users:
                problems.append(f"{tag}: Eintrags-Autor {uid} fehlt in users.xml")
        for mnet in re.findall(r"<mnethosturl>(.*?)</mnethosturl>", users):
            if mnet not in ("$@NULL@$", ""):
                problems.append(
                    f"{tag}: users.xml mnethosturl='{mnet}' — Autor gilt als MNet-"
                    f"Remote-User, Restore verwirft ihn und das Glossar bleibt LEER"
                )
        bad_appr = [a for a in re.findall(r"<approved>(\d+)</approved>", data) if a != "1"]
        if bad_appr:
            problems.append(f"{tag}: {len(bad_appr)} Einträge nicht approved=1 (bleiben unsichtbar)")
        if re.search(r"<entry id=\"\d+\">(?:(?!</entry>).)*<entriestags>", data, re.S):
            warns.append(f"{tag}: <entriestags> innerhalb von <entry> (gehört auf Glossar-Ebene)")
        if "Glossar-Import" not in mb:
            warns.append(f"{tag}: keine Glossar-Importdatei (Fallback) im Kurs — "
                         f"Restore ohne Nutzerdaten kann nicht repariert werden")
        info.append(f"glossar cmid {cmid}: {len(entries)} Einträge, Kette geprüft")

    # ---- 9. Kachelfotos (format tiles) ----------------------------------- #
    course = contents.get("course/course.xml", "")
    if "<format>tiles</format>" in course:
        if "plugin_format_tiles_course" not in course:
            warns.append("tiles: plugin_format_tiles_course fehlt in course.xml")
        files_xml = contents.get("files.xml", "")
        n_photos = 0
        for path, data in contents.items():
            if not re.match(r"sections/section_\d+/section\.xml$", path):
                continue
            for opt in re.finditer(
                r"<course_format_options[^>]*>\s*<format>tiles</format>\s*"
                r"<name>tilephoto</name>\s*<value>([^<]+)</value>", data):
                fname = opt.group(1)
                n_photos += 1
                sec_id = re.search(r'<section id="(\d+)">', data).group(1)
                frec = re.search(
                    r"<file id=\"\d+\">\s*<contenthash>([0-9a-f]{40})</contenthash>"
                    r"(?:(?!</file>).)*<component>format_tiles</component>\s*"
                    r"<filearea>tilephoto</filearea>\s*"
                    rf"<itemid>{sec_id}</itemid>\s*<filepath>/tilephoto/</filepath>\s*"
                    rf"<filename>{re.escape(fname)}</filename>", files_xml, re.S)
                if not frec:
                    problems.append(f"tiles: Kachelfoto '{fname}' (section {sec_id}) "
                                    f"hat keinen passenden files.xml-Eintrag")
                elif f"files/{frec.group(1)[:2]}/{frec.group(1)}" not in members:
                    problems.append(f"tiles: Foto-Blob für '{fname}' fehlt im Archiv")
                # NEUE Plugin-Generation (>= 2024021400): Element mit sectionid-
                # Attribut + optiontype=1(PHOTO)/optionvalue/tilesversion
                newstyle = re.search(
                    rf'<plugin_format_tiles_section sectionid="{sec_id}">\s*'
                    r"<optiontype>1</optiontype>\s*"
                    rf"<optionvalue>{re.escape(fname)}</optionvalue>\s*"
                    r"<tilesversion>\d+</tilesversion>", data)
                if not newstyle:
                    problems.append(
                        f"tiles: section {sec_id} ohne New-Style-Element "
                        f"(sectionid-Attribut + optiontype=1/optionvalue/"
                        f"tilesversion) — aktuelle format_tiles-Versionen "
                        f"restaurieren das Foto sonst NICHT")
                if "<dummysection>" not in data:
                    warns.append(f"tiles: section {sec_id} ohne <dummysection/> — "
                                 f"alte format_tiles-Versionen (learnweb-Ära) "
                                 f"ordnen die Fotos dann nicht zu")
        info.append(f"tiles: {n_photos} Kachelfoto(s) verdrahtet")

    # ---- 10. Attribution auf jeder Seite / jedem Buch-Kapitel ------------ #
    missing = []
    for path, data in contents.items():
        if re.match(r"activities/page_\d+/page\.xml$", path):
            if ATTRIBUTION_MARKER not in data:
                missing.append(path)
        elif re.match(r"activities/book_\d+/book\.xml$", path):
            for i, ch in enumerate(re.findall(r"<content>(.*?)</content>", data, re.S), 1):
                if ATTRIBUTION_MARKER not in ch:
                    missing.append(f"{path} (Kapitel {i})")
    if missing:
        warns.append(f"Attribution fehlt auf {len(missing)} Seite(n)/Kapitel(n): "
                     + ", ".join(missing[:4]) + ("…" if len(missing) > 4 else ""))

    # ---- 11. Interaktive HTML-Dateien (Formulare + Simulationen) --------- #
    files_xml = contents.get("files.xml", "")
    html_hashes = re.findall(
        r"<contenthash>([0-9a-f]{40})</contenthash>(?:(?!</file>).)*"
        r"<mimetype>text/html</mimetype>", files_xml, re.S)
    n_form = n_sim = 0
    for h in set(html_hashes):
        blob_path = f"files/{h[:2]}/{h}"
        if blob_path not in members:
            continue
        html = tar.extractfile(blob_path).read().decode("utf-8", "ignore")
        if "data-field" in html:  # Formular (form_engine)
            n_form += 1
            if "placeholder=" in html:
                problems.append("formular: Eingabefelder enthalten placeholder-Text "
                                "(Felder müssen LEER sein — kein vorgezeichneter "
                                "Lösungsweg)")
            if "localStorage" not in html or "btn-save" not in html:
                problems.append("formular: Autosave/Speichern-Button fehlt")
        elif "var SPEC" in html:  # Simulation (sim_engine)
            n_sim += 1
            if "grid-template-columns:300px" not in html:
                warns.append("simulation: altes Layout ohne Kompakt-Grid — passt "
                             "eventuell nicht ohne Scrollen auf einen Bildschirm")
    if n_form or n_sim:
        info.append(f"interaktiv: {n_form} Formular(e), {n_sim} Simulation(en) geprüft")

    # ---- 12. Formelzeichen-Indizes im Kurstext tiefgestellt? ------------- #
    # A1/d2/F1 … gehören als A<sub>1</sub> gesetzt. Konvertierte Stellen sind
    # im XML als "A&lt;sub&gt;1…" escaped und matchen hier nicht mehr.
    idx_rx = re.compile(r"(?<![A-Za-z0-9_/#])([AdFUIR])([0-9])(?![A-Za-z0-9_])")
    hits = []
    for path, data in contents.items():
        if re.match(r"activities/(page|book|quiz|assign|glossary|label|choice|forum)_\d+/\w+\.xml$", path):
            for m in idx_rx.finditer(data):
                hits.append((path.split("/")[1], m.group(0)))
    if hits:
        ex = ", ".join(f"'{h[1]}' in {h[0]}" for h in hits[:4])
        warns.append(f"INDEX: {len(hits)} Formelzeichen-Indizes nicht "
                     f"tiefgestellt (A<sub>1</sub>) — z. B. {ex}")


def _report(info: list[str], warns: list[str], problems: list[str]) -> None:
    for i in info:
        print(f"  info: {i}")
    for w in warns:
        print(f"  warn: {w}")
    if problems:
        print(f"FAIL: {len(problems)} problem(s):")
        for p in problems:
            print(f"  - {p}")
    else:
        print("OK: all structural checks passed."
              + (f" ({len(warns)} warning(s))" if warns else ""))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python validate_mbz.py <file.mbz>")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
