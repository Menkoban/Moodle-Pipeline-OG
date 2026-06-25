#!/usr/bin/env python3
"""Validate a generated .mbz: check it is a gzip tar, every XML file is
well-formed, and the core cross-references in moodle_backup.xml are consistent
with the section/activity files actually present.

Usage:  python validate_mbz.py out.mbz
Exit code 0 = all checks passed, 1 = problems found.
"""

from __future__ import annotations

import re
import sys
import tarfile
import xml.etree.ElementTree as ET


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
        _report(info, problems)
        return 1 if problems else 0

    root = ET.fromstring(contents["moodle_backup.xml"])
    # Scope to <contents> so <activity>/<section> in <settings> aren't counted.
    contents_el = root.find("information/contents")
    if contents_el is None:
        problems.append("moodle_backup.xml has no <contents> block")
        _report(info, problems)
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

    info.append(f"activities: {sum(1 for _ in contents_el.iter('activity'))}")
    info.append(f"users: {len(user_ids)}, userrefs: {n_userref}")
    info.append(f"sections: {sum(1 for _ in contents_el.iter('section'))}")
    _report(info, problems)
    return 1 if problems else 0


def _report(info: list[str], problems: list[str]) -> None:
    for i in info:
        print(f"  info: {i}")
    if problems:
        print(f"FAIL: {len(problems)} problem(s):")
        for p in problems:
            print(f"  - {p}")
    else:
        print("OK: all structural checks passed.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python validate_mbz.py <file.mbz>")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
