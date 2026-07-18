#!/usr/bin/env python3
"""Abnahme-Simulator für das Diagnose-Modul-Modell: prüft an der FERTIG
GEBAUTEN .mbz (nicht an den Absichten) die Akzeptanzkriterien aus Teil B.7
des Konzepts v3.

Checks:
  1. KATEGORIEN  — Einstufung trägt Gewicht 0 (aggregationcoef2 am
                   Kategorie-Item), Leistung das Spec-Gewicht; Diagnose-
                   Quizze hängen in Einstufung, Konvergenz in Leistung
                   (entkoppelte Scoring-Architektur, B.7.2).
  2. GATE        — vor dem ersten Diagnoseversuch ist KEIN Niveaupfad-
                   Element sichtbar (B.7.8).
  3. ABDECKUNG   — jede Diagnose-Note 0–100 (0,5er-Schritte) öffnet die
                   Erarbeitung GENAU des passenden Levels; Fremd-Level
                   bleiben zu.
  4. NUTZER A/B/C— B.7.3–5: A (30 %, Sprachhilfe, keine Praxis) sieht
                   Grundpfad + Sprachhilfe + Praxis-KOMPENSATION; B (85 %,
                   keine Gruppen) sieht nur den erweiterten Pfad (plus
                   Kompensation — als Nicht-Praxis-Mitglied, normative
                   B.3.5-Semantik; die B.7.4-Formulierung „keine Overlays"
                   ist an dieser Stelle unpräzise); C (60 %, Praxis) sieht
                   Standardpfad + Anknüpfung, NICHT die Kompensation.
  5. KONVERGENZ  — Sicherung erst sichtbar, wenn das letzte Pflichtelement
                   eines Pfads abgeschlossen ist (OR-Gate, B.7.6).
  6. REMEDIATION — sichtbar genau bei Konvergenz-Note < pass (B.7.7) …
  7. FREISCHALTUNG— … und Modul n+1 öffnet genau ab pass (B.7.7).
  8. OVERLAYS    — je aktivem Layer ein Sichtbarkeits-Testpaar: Mitglied /
                   Nicht-Mitglied bzw. Bedingung erfüllt / nicht (B.7.9);
                   date-Layer: vor Stichtag zu, danach offen.
  9. GRUPPEN     — jede group-Bedingung zeigt auf eine Gruppe in groups.xml.

Usage:  python simulate_modular.py kurs.mbz kurs.modmap.json
Exit 0 = alle Checks bestanden, 1 = Verstöße.
"""
from __future__ import annotations

import json
import re
import sys
import tarfile
import xml.etree.ElementTree as ET


# --------------------------------------------------------------------------- #
# MBZ-Parsing
# --------------------------------------------------------------------------- #
def load_mbz(path: str) -> dict[str, str]:
    t = tarfile.open(path, "r:gz")
    xml = {n: t.extractfile(n).read().decode("utf-8")
           for n in t.getnames() if n.endswith(".xml")}
    t.close()
    return xml


def grade_items(xml: dict) -> tuple[dict, dict, dict]:
    """-> (idnumber->id, id->idnumber, idnumber->categoryid)."""
    by_ref, by_id, cat_of = {}, {}, {}
    for path, data in xml.items():
        if not (path.endswith("/grades.xml") or path == "gradebook.xml"):
            continue
        for gi in ET.fromstring(data).iter("grade_item"):
            gid = int(gi.get("id"))
            idnum = (gi.findtext("idnumber") or "").strip()
            if idnum and idnum != "$@NULL@$":
                by_ref[idnum] = gid
                by_id[gid] = idnum
                cat = (gi.findtext("categoryid") or "").strip()
                if cat and cat != "$@NULL@$":
                    cat_of[idnum] = int(cat)
    return by_ref, by_id, cat_of


def category_weights(xml: dict) -> dict[str, tuple[int, float]]:
    """Kategorie-Fullname -> (id, Gewicht am Kategorie-Item)."""
    gb = xml.get("gradebook.xml")
    if not gb:
        return {}
    root = ET.fromstring(gb)
    names = {int(gc.get("id")): (gc.findtext("fullname") or "")
             for gc in root.iter("grade_category")}
    out = {}
    for gi in root.iter("grade_item"):
        if (gi.findtext("itemtype") or "") == "category":
            cid = int(gi.findtext("iteminstance"))
            out[names.get(cid, "?")] = (cid, float(
                gi.findtext("aggregationcoef2") or 0))
    return out


def sections(xml: dict) -> dict[str, dict | None]:
    out = {}
    for path, data in xml.items():
        if not re.match(r"sections/section_\d+/section\.xml$", path):
            continue
        root = ET.fromstring(data)
        name = root.findtext("name") or path
        raw = root.findtext("availabilityjson") or ""
        tree = None
        if raw and raw != "$@NULL@$":
            parsed = json.loads(raw)
            if parsed.get("c"):
                tree = parsed
        out[name] = tree
    return out


def modules(xml: dict) -> dict[str, dict]:
    """idnumber -> {cmid, availability, gradepass, sectionid}."""
    out = {}
    for path, data in xml.items():
        m = re.match(r"activities/([a-z]+)_(\d+)/module\.xml$", path)
        if not m:
            continue
        root = ET.fromstring(data)
        idnum = (root.findtext("idnumber") or "").strip()
        if not idnum:
            continue
        raw = root.findtext("availability") or ""
        tree = None
        if raw and raw != "$@NULL@$":
            parsed = json.loads(raw)
            if parsed.get("c"):
                tree = parsed
        gradepass = 0.0
        grades = xml.get(f"activities/{m.group(1)}_{m.group(2)}/grades.xml")
        if grades:
            gp = ET.fromstring(grades).findtext(".//grade_item/gradepass")
            if gp and gp != "$@NULL@$":
                gradepass = float(gp)
        out[idnum] = {"cmid": int(root.get("id")),
                      "availability": tree, "gradepass": gradepass}
    return out


def groups_xml(xml: dict) -> dict[str, int]:
    """symbolische Gruppen-idnumber -> numerische id."""
    out = {}
    g = xml.get("groups.xml")
    if not g:
        return out
    for grp in ET.fromstring(g).iter("group"):
        sym = (grp.findtext("idnumber") or "").strip() or grp.findtext("name")
        out[sym] = int(grp.get("id"))
    return out


# --------------------------------------------------------------------------- #
# availability-Auswertung (Moodle-Semantik, quellcode-verifiziert)
# --------------------------------------------------------------------------- #
def eval_tree(tree, scores, states, member: set[int], now: int) -> bool:
    if tree is None:
        return True
    op = tree.get("op", "&")
    res = []
    for c in tree.get("c", []):
        if "op" in c:
            res.append(eval_tree(c, scores, states, member, now))
        elif c.get("type") == "grade":
            g = scores.get(int(c["id"]))
            ok = g is not None
            if ok and "min" in c:
                ok = g >= float(c["min"])
            if ok and "max" in c:
                ok = g < float(c["max"])
            res.append(ok)
        elif c.get("type") == "completion":
            st = states.get(int(c["cm"]), 0)
            e = int(c["e"])
            res.append(st in (1, 2) if e == 1 else
                       st in (0, 3) if e == 0 else st == e)
        elif c.get("type") == "group":
            res.append(int(c["id"]) in member)
        elif c.get("type") == "date":
            res.append(now >= int(c["t"]) if c["d"] == ">=" else
                       now < int(c["t"]))
        else:
            res.append(False)
    if op == "&":
        return all(res)
    if op == "|":
        return any(res)
    if op == "!&":
        return not all(res)
    return not any(res) if op == "!|" else False


# --------------------------------------------------------------------------- #
# Simulation
# --------------------------------------------------------------------------- #
def frange(a, b, step):
    x = a
    while x <= b + 1e-9:
        yield round(x, 3)
        x += step


def main(mbz_path: str, modmap_path: str) -> int:
    xml = load_mbz(mbz_path)
    mm = json.load(open(modmap_path, encoding="utf-8"))
    if mm.get("modell") != "diagnose":
        print("FAIL: modmap ist kein Diagnose-Modell (simulate_pathways.py "
              "für Stufen-Kurse nutzen).")
        return 1
    by_ref, by_id, cat_of = grade_items(xml)
    cats = category_weights(xml)
    secs = sections(xml)
    mods = modules(xml)
    gmap = groups_xml(xml)
    levels = mm["levels"]
    windows = {l: tuple(mm["windows"][l]) for l in levels}
    errors, infos = [], []

    def persona(diag_grade=None, done=(), groups=(), conv_grade=None,
                module=None, now=None):
        """-> (scores, states, member, now) für eval_tree."""
        m = module or mm["modules"][0]
        scores, states = {}, {}
        if diag_grade is not None:
            scores[by_ref[m["diag"]]] = diag_grade
            states[mods[m["diag"]]["cmid"]] = 1     # gradepass=0 -> complete
        if conv_grade is not None:
            scores[by_ref[m["conv"]]] = conv_grade
            states[mods[m["conv"]]["cmid"]] = (
                2 if conv_grade >= mods[m["conv"]]["gradepass"] else 3)
        for idnum in done:
            states[mods[idnum]["cmid"]] = 1         # Ansehen-Abschluss
        member = {gmap[mm["groups"][k]] for k in groups
                  if k in mm["groups"] and mm["groups"][k] in gmap}
        return scores, states, member, now or 10_000_000_000

    def visible(idnum, p) -> bool:
        return eval_tree(mods[idnum]["availability"], *p)

    def elems(m, **filt):
        out = []
        for e in m["elements"]:
            if all((e.get("visibility") or {}).get(k) == v or
                   (k == "role" and e.get("role") == v)
                   for k, v in filt.items()):
                out.append(e["idnumber"])
        return out

    def level_of(e) -> list:
        return (e.get("visibility") or {}).get("level") or []

    # ---- 1) KATEGORIEN: entkoppelte Scoring-Architektur ------------------- #
    want = mm.get("grade_categories", {})
    einst = next((v for k, v in cats.items() if "Einstufung" in k or
                  k == "einstufung"), None)
    leist = next((v for k, v in cats.items() if "Leistung" in k or
                  k == "leistung"), None)
    if einst is None or abs(einst[1]) > 1e-9:
        errors.append(f"KATEGORIEN: Einstufung fehlt oder Gewicht != 0 "
                      f"({einst}) — Diagnose würde die Note beeinflussen")
    if leist is None:
        errors.append("KATEGORIEN: Kategorie Leistung fehlt")
    for m in mm["modules"]:
        if einst and cat_of.get(m["diag"]) != einst[0]:
            errors.append(f"KATEGORIEN: {m['diag']} hängt nicht in "
                          f"Einstufung (categoryid {cat_of.get(m['diag'])})")
        if leist and cat_of.get(m["conv"]) != leist[0]:
            errors.append(f"KATEGORIEN: {m['conv']} hängt nicht in Leistung")
    infos.append(f"Kategorien: Einstufung Gewicht {einst[1] if einst else '?'}"
                 f", Leistung {leist[1] if leist else '?'} — Diagnose zählt "
                 f"nie zur Note")

    # ---- 2) GATE: vor Diagnose kein Pfad sichtbar (B.7.8) ----------------- #
    for m in mm["modules"]:
        p0 = persona(module=m)     # nichts angefasst
        offen = [e["idnumber"] for e in m["elements"]
                 if level_of(e) and visible(e["idnumber"], p0)]
        if offen:
            errors.append(f"GATE {m['id']}: vor dem Diagnoseversuch sichtbar: "
                          f"{offen} — Diagnose-Gate (B.3.2) fehlt/undicht")
    infos.append("Diagnose-Gate: vor dem 1. Versuch ist kein Pfad offen")

    # ---- 3) ABDECKUNG: jede Note -> genau das passende Level -------------- #
    def want_level(g):
        for l in levels:
            lo, hi = windows[l]
            if (lo is None or g >= lo) and (hi is None or g < hi):
                return l
        return None

    for m in mm["modules"]:
        for g in frange(0, 100, 0.5):
            p = persona(diag_grade=g, module=m)
            wl = want_level(g)
            for e in m["elements"]:
                lv = level_of(e)
                if not lv or len((e.get("visibility") or {})) > 1:
                    continue        # nur reine Level-Elemente prüfen
                vis = visible(e["idnumber"], p)
                if (wl in lv) != vis:
                    errors.append(f"ABDECKUNG {m['id']}: Note {g} -> "
                                  f"{e['idnumber']} {'sichtbar' if vis else 'zu'}"
                                  f", erwartet {'sichtbar' if wl in lv else 'zu'}")
                    break
            else:
                continue
            break
    infos.append("Abdeckung 0–100: jede Diagnose-Note öffnet genau ihr Level")

    # ---- 4) NUTZER A/B/C (B.7.3–5) ---------------------------------------- #
    m1 = mm["modules"][0]
    def check_user(name, p, must_see, must_not):
        for idnum in must_see:
            if not visible(idnum, p):
                errors.append(f"NUTZER {name}: sieht '{idnum}' NICHT — "
                              f"erwartet sichtbar")
        for idnum in must_not:
            if visible(idnum, p):
                errors.append(f"NUTZER {name}: sieht '{idnum}' — erwartet "
                              f"verborgen")

    basic_e = elems(m1, role="erarbeitung", level=["basic"])
    std_e = elems(m1, role="erarbeitung", level=["standard"])
    adv_e = elems(m1, role="erarbeitung", level=["advanced"])
    sprach = [e["idnumber"] for e in m1["elements"]
              if (e.get("visibility") or {}).get("language_support")]
    praxis_mit = [e["idnumber"] for e in m1["elements"]
                  if (e.get("visibility") or {}).get("practice_experience") == "with"]
    praxis_ohne = [e["idnumber"] for e in m1["elements"]
                   if (e.get("visibility") or {}).get("practice_experience") == "without"]

    check_user("A (30 %, Sprachhilfe, keine Praxis)",
               persona(diag_grade=30, groups=("language_support",)),
               basic_e + sprach + praxis_ohne, std_e + adv_e + praxis_mit)
    check_user("B (85 %, keine Gruppen)",
               persona(diag_grade=85),
               adv_e + praxis_ohne, basic_e + std_e + sprach + praxis_mit)
    check_user("C (60 %, Praxis)",
               persona(diag_grade=60, groups=("practice_experience",)),
               std_e + praxis_mit, basic_e + adv_e + sprach + praxis_ohne)
    infos.append("Testnutzer A/B/C: Pfade + Overlays wie spezifiziert "
                 "(B sieht die Praxis-Kompensation als Nicht-Mitglied — "
                 "normative B.3.5-Semantik)")

    # ---- 5) KONVERGENZ: OR über letzte Pflichtelemente (B.7.6) ------------ #
    for m in mm["modules"]:
        if visible(m["conv"], persona(diag_grade=30, module=m)):
            errors.append(f"KONVERGENZ {m['id']}: sichtbar ohne "
                          f"abgeschlossenes Pfadelement")
        for lvl, last in m["last_required"].items():
            if not visible(m["conv"], persona(diag_grade=30, module=m,
                                              done=(last,))):
                errors.append(f"KONVERGENZ {m['id']}: '{last}' ({lvl}) "
                              f"abgeschlossen, aber Sicherung bleibt zu")
    infos.append("Konvergenzpunkt: öffnet mit Abschluss des letzten "
                 "Pflichtelements jedes Pfads")

    # ---- 6) REMEDIATION + 7) FREISCHALTUNG (B.7.7) ------------------------ #
    for i, m in enumerate(mm["modules"]):
        pass_ = float(m["pass"])
        # Remediation-Aktivitäten tragen keine idnumber in modmap.elements —
        # erkenne sie an ihrer Bedingung: grade auf die Konvergenz MIT max
        # (= Fenster unter der Bestehensgrenze).
        low = persona(diag_grade=60, conv_grade=pass_ - 5, module=m)
        high = persona(diag_grade=60, conv_grade=pass_ + 5, module=m)
        conv_gid = by_ref[m["conv"]]
        rem_mods = [idn for idn, info in mods.items()
                    if info["availability"] and
                    any(c.get("type") == "grade" and c.get("id") == conv_gid
                        and "max" in c
                        for c in info["availability"].get("c", []))]
        for idn in rem_mods:
            if not eval_tree(mods[idn]["availability"], *low):
                errors.append(f"REMEDIATION {m['id']}: '{idn}' bei "
                              f"{pass_-5} % nicht sichtbar")
            if eval_tree(mods[idn]["availability"], *high):
                errors.append(f"REMEDIATION {m['id']}: '{idn}' bei "
                              f"{pass_+5} % fälschlich sichtbar")
        if i + 1 < len(mm["modules"]):
            nxt = mm["modules"][i + 1]["section"]
            tree = secs.get(nxt)
            if tree is None:
                errors.append(f"FREISCHALTUNG: Section '{nxt}' hat keine "
                              f"availability — Modul {i+2} stünde offen")
            else:
                if eval_tree(tree, *low):
                    errors.append(f"FREISCHALTUNG: '{nxt}' offen bei "
                                  f"Konvergenz {pass_-5} %")
                if not eval_tree(tree, *high):
                    errors.append(f"FREISCHALTUNG: '{nxt}' zu bei "
                                  f"Konvergenz {pass_+5} %")
    infos.append("Remediation < pass, Folgemodul >= pass — beide Kanten "
                 "geprüft")

    # ---- 8) OVERLAY-TESTPAARE je aktivem Layer (B.7.9) -------------------- #
    for layer in mm["active_layers"]:
        pair_checked = False
        for m in mm["modules"]:
            for e in m["elements"]:
                val = (e.get("visibility") or {}).get(layer)
                if val is None:
                    continue
                idnum = e["idnumber"]
                base = {"diag_grade": 60, "module": m}
                lv = level_of(e)
                if lv:
                    base["diag_grade"] = {"basic": 30, "standard": 60,
                                          "advanced": 85}[lv[0]]
                cfg = (mm.get("layer_config") or {}).get(layer) or {}
                if cfg.get("quelle") == "datum":
                    on = persona(**base, now=10_000_000_000)
                    off = persona(**base, now=1)
                elif layer == "wiederholer":
                    on = persona(**base, conv_grade=m["pass"] - 5)
                    off = persona(**base, conv_grade=m["pass"] + 5)
                else:
                    inside = persona(**base, groups=(layer,))
                    outside = persona(**base)
                    on, off = (outside, inside) if val == "without" \
                        else (inside, outside)
                if not visible(idnum, on):
                    errors.append(f"OVERLAY {layer}: '{idnum}' bei erfüllter "
                                  f"Bedingung nicht sichtbar")
                if visible(idnum, off):
                    errors.append(f"OVERLAY {layer}: '{idnum}' bei NICHT "
                                  f"erfüllter Bedingung sichtbar")
                pair_checked = True
        if not pair_checked:
            print(f"  warn: Layer '{layer}' aktiv, aber kein Element nutzt "
                  f"ihn — Testpaar entfällt (B.7.9)")
    infos.append("Overlay-Testpaare: Mitglied/Nicht-Mitglied bzw. Bedingung "
                 "erfüllt/nicht geprüft")

    # ---- 9) GRUPPEN-Konsistenz -------------------------------------------- #
    def group_ids_in(tree, acc):
        for c in (tree or {}).get("c", []):
            if "op" in c:
                group_ids_in(c, acc)
            elif c.get("type") == "group":
                acc.add(int(c["id"]))
        return acc

    used: set[int] = set()
    for info in mods.values():
        group_ids_in(info["availability"], used)
    for tree in secs.values():
        group_ids_in(tree, used)
    missing = used - set(gmap.values())
    if missing:
        errors.append(f"GRUPPEN: availability referenziert Gruppen {missing}, "
                      f"die nicht in groups.xml stehen")
    infos.append(f"Gruppen: {len(gmap)} in groups.xml, {len(used)} in "
                 f"Bedingungen referenziert, alle auflösbar")

    # ---- Report ------------------------------------------------------------ #
    for i in infos:
        print(f"  info: {i}")
    if errors:
        print(f"FAIL: {len(errors)} Verstoß/Verstöße:")
        for e in errors[:30]:
            print(f"  - {e}")
        return 1
    print("OK: Diagnose-Modul-Modell erfüllt die Akzeptanzkriterien B.7 "
          "(statisch simuliert).")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: python simulate_modular.py <kurs.mbz> <kurs.modmap.json>")
        sys.exit(2)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    sys.exit(main(sys.argv[1], sys.argv[2]))
