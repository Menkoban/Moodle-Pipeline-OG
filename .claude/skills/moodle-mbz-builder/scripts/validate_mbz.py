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
# Zahl inkl. Tausender-Leerzeichen ("14 400") und deutschem Dezimalkomma.
_NUM = r"[-+]?\d+(?:[  ]\d{3})*(?:[.,]\d+)?"
# Einheiten-Token: "1/min"-Formen, Symbole, ausgeschriebene Einheiten
# (längere Alternativen zuerst, damit "kV" vor "V" greift).
_UNIT = (r"(?:1/min|1/s|1/h|kV|mV|µV|V|mA|µA|kA|A|kΩ|MΩ|Ω|kW|MW|VA|var|W|kN|Nm|N|"
         r"hPa|kPa|MPa|Pa|mbar|bar|mm|cm|dm|km|µm|nm|m|ms|µs|ns|min|h|s|°C|K|°|"
         r"kg|mg|µg|g|t|kHz|MHz|GHz|Hz|mF|µF|nF|pF|F|mH|µH|H|kWh|Wh|kJ|MJ|J|ml|l|%|"
         r"Ohm|Volt|Ampere|Watt|Newton|Pascal|Hertz|Joule|Sekunden|Sekunde|"
         r"Minuten|Minute|Stunden|Stunde|Meter|Grad|Prozent)")
_UNIT_TOKEN_RX = re.compile(r"(?<![A-Za-zµ°])" + _UNIT + r"(?![A-Za-zµ])")
_RESULT_RX = re.compile(r"=\s*(" + _NUM + r")")
_RESULT_UNIT_RX = re.compile(r"=\s*" + _NUM + r"\s*" + _UNIT + r"(?![A-Za-zµ])")
# Zahl gefolgt von Operator/Hochzahl -> Formel-Term, kein Ergebnis (z. B.
# "n = 60 · f / p", "= 6²").
_RESULT_OP_RX = re.compile(r"=\s*" + _NUM + r"\s*[/·*×^²³+\-−]")
# Nur klar einheitenbehaftete Größen melden (hohe Präzision statt Vollständigkeit).
# Mehrdeutige/dimensionslose Symbole (A=Ampere/Fläche, p=Druck/Polpaar,
# n=Drehzahl/Anzahl, i/z=Übersetzung/Zähl, η=Wirkungsgrad, NN-Gewichte) bewusst
# NICHT enthalten -> keine Fehlalarme auf dimensionslosen Größen.
_QUANTITY = {"U", "I", "R", "P", "F", "M", "Q", "W", "E", "s", "v", "d", "l"}
_LHS_SYM_RX = re.compile(r"([A-Za-z])[ _]?\d*\s*$")


def _readable_text(raw: str) -> str:
    """XML-escapetes (ggf. doppelt, z. B. &amp;#183;) HTML -> lesbarer Klartext:
    entschärfen, Tags strippen, Leerraum zusammenfassen."""
    txt = raw
    for _ in range(3):                     # doppelte Escapes auflösen
        new = html.unescape(txt)
        if new == txt:
            break
        txt = new
    txt = re.sub(r"<[^>]+>", " ", txt)     # HTML-Tags entfernen
    return re.sub(r"\s+", " ", txt).strip()


def _calc_unit_warnings(text: str) -> list[str]:
    """Beratend: in einem Rechenkontext (Text mit '=' UND einem Einheiten-Token)
    ein Ergebnis '<Größe> = <Zahl>' melden, dem KEINE Einheit folgt — aber nur,
    wenn die linke Größe klar einheitenbehaftet ist (U, I, R, P, F …). Nie fatal."""
    if "=" not in text or not _UNIT_TOKEN_RX.search(text):
        return []
    out, seen = [], set()
    for m in _RESULT_RX.finditer(text):
        if _RESULT_UNIT_RX.match(text, m.start()):
            continue  # Einheit folgt -> ok
        if _RESULT_OP_RX.match(text, m.start()):
            continue  # Formel-Term (Operator/Hochzahl folgt) -> kein Ergebnis
        sym = _LHS_SYM_RX.search(text[max(0, m.start() - 14):m.start()])
        if not sym or sym.group(1) not in _QUANTITY:
            continue  # keine klar einheitenbehaftete Größe -> nicht melden
        snip = re.sub(r"\s+", " ", m.group(0)).strip()
        if snip not in seen:
            seen.add(snip)
            out.append(snip)
    return out[:5]


# --- Merke-Satz-Heuristik: Merksatz vs. Stichwort-/Fragment-Kette (beratend) - #
# Typische finite Verbformen (Hilfs-, Modal- und häufige Vollverben). Enthält ein
# "?"-Segment ein solches Token, gilt es als vollständige Frage (kein Fragment) —
# die Liste ist bewusst großzügig, damit gute Merksätze NICHT fälschlich als
# Fragment-Kette geflaggt werden (Verben verringern die Trefferzahl).
_FINITE_VERBS = {
    "ist", "sind", "war", "waren", "bin", "bist", "seid", "sei", "wird",
    "werden", "wirst", "werde", "wurde", "wurden", "hat", "haben", "habe",
    "hast", "habt", "hatte", "hatten", "kann", "kannst", "können", "konnte",
    "konnten", "muss", "musst", "müssen", "musste", "soll", "sollst", "sollen",
    "sollte", "darf", "darfst", "dürfen", "mag", "mögen", "will", "wollen",
    "willst", "möchte", "möchten", "gibt", "geht", "gehen", "kommt", "kommen",
    "macht", "machen", "nimmt", "nehmen", "dreht", "drehen", "läuft", "laufen",
    "liegt", "liegen", "steht", "stehen", "sitzt", "sitzen", "bleibt", "bleiben",
    "braucht", "brauchen", "sorgt", "sorgen", "führt", "führen", "bedeutet",
    "bedeuten", "passiert", "passieren", "entsteht", "entstehen", "erzeugt",
    "erzeugen", "erkennt", "erkennen", "achtet", "achten", "prüft", "prüfen",
    "funktioniert", "wählt", "wählen", "stellt", "stellen", "misst", "messen",
    "steigt", "steigen", "sinkt", "sinken", "schont", "schonen", "gilt",
    "gelten", "heißt", "zeigt", "zeigen", "hilft", "helfen", "tut", "tun",
    "bohrt", "bohren", "spannt", "spannen", "verwendet", "verwenden", "benutzt",
    "benutzen", "setzt", "setzen", "berechnet", "berechnen", "hält", "halten",
    "kühlt", "kühlen", "passt", "passen", "brauchst", "beträgt", "ergibt",
}
_WORD_RX = re.compile(r"[A-Za-zÄÖÜäöüß]+")
# Anker: 💡-Emoji ODER das eigenständige Wort „Merke".
_MERKE_ANCHOR_RX = re.compile("\U0001F4A1" + r"|\bMerke\b")


def _merke_fragment_warnings(text: str) -> list[str]:
    """Beratend: In „Merke"-/💡-Kästen soll der Merksatz ein VOLLSTÄNDIGER Satz
    sein, keine Stichwort-/Fragment-Kette. Anker: 💡-Emoji ODER das Wort „Merke".
    Nach dem ersten „:" wird nur die unmittelbar folgende Klausel (bis zum ersten
    „." / „!") betrachtet; besteht sie aus ≥2 kurzen (< 5 Wörter), verblosen
    „…?"-Segmenten (z. B. „Schneiden scharf? Schaft sauber?"), gilt sie als
    Fragment-Kette. Konservativ: lieber eine echte Kette verpassen als gute
    Merksätze fälschlich flaggen. Nie fatal."""
    out: list[str] = []
    seen: set[str] = set()
    for am in _MERKE_ANCHOR_RX.finditer(text):
        window = text[am.start():am.start() + 200]
        ci = window.find(":")
        if ci < 0:
            continue                       # kein „…:"-Merke-Lead -> nichts prüfen
        # Nur die unmittelbar folgende Klausel bis zum ersten Satzende ansehen —
        # so leckt späterer Kurstext (z. B. eine FAQ) keine Fragezeichen ein.
        head = re.split(r"[.!]", window[ci + 1:], 1)[0]
        segs = [s.strip(" ?\t\n") for s in re.findall(r"[^?]*\?", head)]
        segs = [s for s in segs if s]
        if len(segs) < 2:                  # keine „a? b?"-Kette
            continue
        words = [_WORD_RX.findall(s) for s in segs]
        if sum(len(w) for w in words) / len(words) >= 5:
            continue                       # Segmente im Schnitt zu lang -> Fragen
        if any(w.lower() in _FINITE_VERBS for ws in words for w in ws):
            continue                       # ein finites Verb -> vollständige Frage
        snip = re.sub(r"\s+", " ", head).strip()
        if snip and snip not in seen:
            seen.add(snip)
            out.append(snip)
    return out[:3]


# --- Rechenbeispiel-Schritt-Heuristik: Einsetzen -> Ergebnis (beratend) ------ #
# Rechenoperator-Zeichen einer echten Zwischenrechnung.
_CALC_OP_RX = re.compile(r"[·×÷/=≈*]")


def _rechenbeispiel_step_warnings(text: str) -> list[str]:
    """Beratend: Enthält ein Rechenbeispiel sowohl „Einsetzen" als auch
    „Ergebnis", soll dazwischen mindestens eine Zwischenrechen-Zeile stehen
    (Ziffern UND ein Rechenoperator ·×÷/=≈). Springt „Einsetzen:" ohne solche
    Zeile direkt zum „Ergebnis", WARN. Konservativ — es wird nur gemeldet, wenn
      * „Einsetzen" als Schritt ausgeschrieben ist (Doppelpunkt vor dem
        „Ergebnis") UND
      * nach „Ergebnis" wirklich ein Zahlenergebnis folgt,
    damit reine Schema-Aufzählungen („… – Einsetzen – Ergebnis") und Fließtext
    nichts auslösen. Nie fatal."""
    for em in re.finditer(r"Einsetzen", text):
        gm = re.search(r"Ergebnis", text[em.end():])
        if not gm:
            continue
        between = text[em.end():em.end() + gm.start()]
        after = text[em.end() + gm.end():em.end() + gm.end() + 40]
        if ":" not in between:
            continue                       # „Einsetzen" nicht als Schritt (kein „:")
        if not re.search(r"\d", after):
            continue                       # kein Zahlenergebnis -> keine echte Rechnung
        if re.search(r"\d", between) and _CALC_OP_RX.search(between):
            continue                       # Zwischenrechnung vorhanden -> ok
        return [re.sub(r"\s+", " ", "Einsetzen" + between + "Ergebnis").strip()[:140]]
    return []


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

    # ---- 13. Rechnungen ohne Einheit (beratend) -------------------------- #
    for path, data in contents.items():
        if not re.match(r"activities/(page|book)_\d+/\w+\.xml$", path):
            continue
        for block in re.findall(r"<content>(.*?)</content>", data, re.S):
            snips = _calc_unit_warnings(_readable_text(block))
            if snips:
                warns.append(
                    f"EINHEIT: mögliche Rechnung(en) ohne Einheit in "
                    f"{path.split('/')[1]}: " + ", ".join(f"'{s}'" for s in snips)
                    + " (Einheit ergänzen?)")

    # ---- 14. Merke-Satz-Qualität & Rechenbeispiel-Schritte (beratend) ---- #
    # Inhaltliche Tiefen-Checks auf Infoblättern: ein „Merke"/💡-Kasten soll ein
    # vollständiger Satz sein (keine Stichwort-/Fragment-Kette), und ein
    # Rechenbeispiel soll von „Einsetzen" nicht ohne Zwischenrechnung direkt zum
    # „Ergebnis" springen. Beides nur WARN (siehe Helfer oben) — nie fatal.
    for path, data in contents.items():
        km = re.match(r"activities/(page|book)_\d+/\w+\.xml$", path)
        if not km:
            continue
        tag = path.split("/")[1]
        for block in re.findall(r"<content>(.*?)</content>", data, re.S):
            txt = _readable_text(block)
            for snip in _merke_fragment_warnings(txt):
                warns.append(
                    f"MERKE: Merksatz wirkt wie Stichwort-/Fragment-Kette statt "
                    f"vollständiger Satz in {tag}: '{snip}'")
            if km.group(1) == "page":      # Rechenbeispiel-Check nur auf Seiten
                for snip in _rechenbeispiel_step_warnings(txt):
                    warns.append(
                        f"RECHENBEISPIEL: Einsetzen springt direkt zum Ergebnis — "
                        f"Zwischenschritt fehlt in {tag}: '{snip}'")


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
