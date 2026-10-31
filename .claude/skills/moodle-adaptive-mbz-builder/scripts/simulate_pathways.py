#!/usr/bin/env python3
"""Pfad-Simulator für adaptive Kurse: prüft an der FERTIG GEBAUTEN .mbz
(nicht an den Absichten), dass die Verzweigungslogik durchlässig, lückenlos
und ratschen-frei ist.

Checks:
  1. ABDECKUNG   — für jeden Test und jede Note 0..100 (Schritt 0,5) ist in
                   der Folgestufe GENAU EINE Niveau-Kachel sichtbar
                   (keine toten Enden, keine Doppel-Freischaltung).
  2. RATSCHE     — ein starker Anfänger/Mittel-Lernender steigt auf, ein
                   schwacher Fortgeschrittener steigt ab (Szenario-Läufe).
  3. FÖRDER      — unter der Mindestschwelle wird die Förder-Kachel der
                   eigenen Stufe sichtbar (Wiederholschleife) …
  4. DECKEL      — … und jeder Test hat die Versuchsbegrenzung (max_versuche).
  5. KUMULATIV   — das Calculated-Item summiert GENAU die Test-Items mit den
                   konfigurierten Niveau-Gewichten (Null-Item-Trick) …
  6. ENTKOPPLUNG — … und KEINE availability-Bedingung referenziert das
                   kumulative Item (Ratschen-Verbot, §3 der Referenz).
  7. RETAKE      — die Null-Item-Invariante überlebt Wiederholungen: Wer den
                   Stufentest eines Pfads angefasst hat, kann nach einem
                   verbesserten Retake des VORTESTS keinen Geschwister-Test
                   derselben Stufe mehr füllen (Pfad-Lock via completion-
                   Bedingungen); die eigene Kachel bleibt trotzdem offen.
  8. GRADEMAX    — grademax des kumulativen Items = real erreichbares Maximum
                   des besten Wegs (Σ je Stufe max. Gewicht × 100), damit die
                   Prozentanzeige des Doku-Scores lesbar ist.

Completion-Semantik (Moodle 4.5, availability/condition/completion,
is_available — verbatim verifiziert): e=1 matcht Zustand {1,2} („complete
also allows pass"), e=0 matcht {0,3} („incomplete also allows fail"),
e=2/e=3 exakt. Zustände: 0=unberührt, 1=complete, 2=pass, 3=fail.

Usage:  python simulate_pathways.py kurs.mbz kurs.pathmap.json
Exit 0 = alle Checks bestanden, 1 = Verstöße.
"""
from __future__ import annotations

import json
import re
import sys
import tarfile
import xml.etree.ElementTree as ET

NIVEAUS = ("anfaenger", "mittel", "fortgeschritten")


# --------------------------------------------------------------------------- #
# MBZ-Parsing
# --------------------------------------------------------------------------- #
def load_mbz(path: str):
    t = tarfile.open(path, "r:gz")
    xml = {n: t.extractfile(n).read().decode("utf-8")
           for n in t.getnames() if n.endswith(".xml")}
    t.close()
    return xml


def grade_items(xml: dict) -> tuple[dict, dict]:
    """-> (idnumber->id, id->idnumber) über Activity- UND Root-Gradebook."""
    by_ref, by_id = {}, {}
    for path, data in xml.items():
        if not (path.endswith("/grades.xml") or path == "gradebook.xml"):
            continue
        for gi in ET.fromstring(data).iter("grade_item"):
            gid = int(gi.get("id"))
            idnum = (gi.findtext("idnumber") or "").strip()
            if idnum and idnum != "$@NULL@$":
                by_ref[idnum] = gid
                by_id[gid] = idnum
    return by_ref, by_id


def calculated_items(xml: dict) -> list[dict]:
    out = []
    gb = xml.get("gradebook.xml")
    if not gb:
        return out
    for gi in ET.fromstring(gb).iter("grade_item"):
        calc = gi.findtext("calculation") or ""
        if calc and calc != "$@NULL@$":
            out.append({
                "id": int(gi.get("id")),
                "idnumber": (gi.findtext("idnumber") or "").strip(),
                "calculation": calc,
                "grademax": float(gi.findtext("grademax") or 0),
            })
    return out


def sections(xml: dict) -> dict[str, dict]:
    """Sektionsname -> {availability-Baum (dict|None)}"""
    out = {}
    for path, data in xml.items():
        if not re.match(r"sections/section_\d+/section\.xml$", path):
            continue
        root = ET.fromstring(data)
        name = root.findtext("name") or path
        av_raw = root.findtext("availabilityjson") or ""
        tree = None
        if av_raw and av_raw != "$@NULL@$":
            parsed = json.loads(av_raw)
            if parsed.get("c"):
                tree = parsed
        out[name] = {"availability": tree}
    return out


def quiz_attempts(xml: dict) -> dict[str, int]:
    """Test-idnumber -> attempts_number (Deckel)."""
    out = {}
    for path, data in xml.items():
        m = re.match(r"activities/quiz_(\d+)/quiz\.xml$", path)
        if not m:
            continue
        mod = xml.get(f"activities/quiz_{m.group(1)}/module.xml", "")
        idnum = ET.fromstring(mod).findtext("idnumber") if mod else ""
        att = ET.fromstring(data).findtext(".//attempts_number")
        if idnum:
            out[idnum] = int(att or 0)
    return out


def modules(xml: dict) -> dict[str, dict]:
    """Aktivitäts-idnumber -> {cmid, completion, availability-Baum, gradepass}.
    gradepass kommt aus dem Quiz-grade_item (Prozent, da grademax=100)."""
    out = {}
    for path, data in xml.items():
        m = re.match(r"activities/([a-z]+)_(\d+)/module\.xml$", path)
        if not m:
            continue
        root = ET.fromstring(data)
        idnum = (root.findtext("idnumber") or "").strip()
        if not idnum:
            continue
        av_raw = root.findtext("availability") or ""
        tree = None
        if av_raw and av_raw != "$@NULL@$":
            parsed = json.loads(av_raw)
            if parsed.get("c"):
                tree = parsed
        gradepass = 0.0
        grades = xml.get(f"activities/{m.group(1)}_{m.group(2)}/grades.xml")
        if grades:
            gp = ET.fromstring(grades).findtext(".//grade_item/gradepass")
            if gp and gp != "$@NULL@$":
                gradepass = float(gp)
        out[idnum] = {
            "cmid": int(root.get("id")),
            "completion": int(root.findtext("completion") or 0),
            "availability": tree,
            "gradepass": gradepass,
        }
    return out


# --------------------------------------------------------------------------- #
# availability-Auswertung (Moodle-Semantik: grade erfüllt wenn min <= note
# < max, leere Note NIE; completion e=1 matcht Zustand {1,2}, e=0 matcht
# {0,3}, e=2/e=3 exakt — Quelle: availability_completion::is_available)
# --------------------------------------------------------------------------- #
def eval_tree(tree, scores: dict[int, float],
              states: dict[int, int] | None = None) -> bool:
    if tree is None:
        return True
    states = states or {}
    op = tree.get("op", "&")
    results = []
    for c in tree.get("c", []):
        if "op" in c:
            results.append(eval_tree(c, scores, states))
        elif c.get("type") == "grade":
            g = scores.get(int(c["id"]))
            ok = g is not None
            if ok and "min" in c:
                ok = g >= float(c["min"])
            if ok and "max" in c:
                ok = g < float(c["max"])
            results.append(ok)
        elif c.get("type") == "completion":
            st = states.get(int(c["cm"]), 0)   # unbekannt = unberührt
            e = int(c["e"])
            if e == 1:
                results.append(st in (1, 2))
            elif e == 0:
                results.append(st in (0, 3))
            else:
                results.append(st == e)
        else:
            results.append(False)  # unbekannte Bedingung: konservativ
    if op == "&":
        return all(results)
    if op == "|":
        return any(results)
    if op == "!&":
        return not all(results)
    if op == "!|":
        return not any(results)
    return False


def referenced_grade_ids(tree, acc=None) -> set[int]:
    acc = set() if acc is None else acc
    if not tree:
        return acc
    for c in tree.get("c", []):
        if "op" in c:
            referenced_grade_ids(c, acc)
        elif c.get("type") == "grade":
            acc.add(int(c["id"]))
    return acc


# --------------------------------------------------------------------------- #
# Simulation
# --------------------------------------------------------------------------- #
def frange(a, b, step):
    x = a
    while x <= b + 1e-9:
        yield round(x, 3)
        x += step


def main(mbz_path: str, pathmap_path: str) -> int:
    xml = load_mbz(mbz_path)
    pm = json.load(open(pathmap_path, encoding="utf-8"))
    by_ref, by_id = grade_items(xml)
    secs = sections(xml)
    calcs = calculated_items(xml)
    attempts = quiz_attempts(xml)
    mods = modules(xml)

    sw = pm["schwellen"]
    auf, ab, halt = sw["aufstieg"], sw["abstieg"], sw["fortgeschritten_halten"]
    order = list(pm.get("niveaus") or NIVEAUS)   # geordnet niedrig -> hoch
    top = order[-1]
    errors, infos = [], []

    def mk_states(touched: dict[str, float]) -> dict[int, int]:
        """Angefasste Tests (ref -> Note) -> completion-Zustände (cmid ->
        2=pass/3=fail via gradepass). Nicht gelistete Tests = 0 (unberührt)."""
        st = {}
        for ref, g in touched.items():
            m = mods.get(ref)
            if m is None:
                continue
            st[m["cmid"]] = 2 if g >= m["gradepass"] else 3
        return st

    def expected_next(pkey: str, score: float) -> str:
        """Soll-Zielpfad nach der Verzweigungsmatrix (Referenz-Logik,
        unabhängig vom Generator implementiert)."""
        i = order.index(pkey)
        if i == len(order) - 1:
            return order[i] if score >= halt else order[i - 1]
        if score >= auf:
            return order[min(i + 1, len(order) - 1)]
        if score >= ab:
            return order[i]
        return order[max(i - 1, 0)]

    def sec_tree(name):
        if name not in secs:
            errors.append(f"Section '{name}' aus pathmap fehlt im mbz")
            return None
        return secs[name]["availability"]

    stufen = pm["stufen"]

    # ---- 1) ABDECKUNG: je Vortest genau EINE Folgekachel ------------------ #
    for i in range(1, len(stufen)):
        prev, cur = stufen[i - 1], stufen[i]
        cur_secs = {nk: sec_tree(nm) for nk, nm in cur["sections"].items()}
        for pk, pref in prev["tests"].items():
            pid = by_ref.get(pref)
            if pid is None:
                errors.append(f"Test-Item '{pref}' fehlt im Gradebook")
                continue
            for g in frange(0, 100, 0.5):
                st = mk_states({pref: g})
                visible = [nk for nk, tree in cur_secs.items()
                           if eval_tree(tree, {pid: g}, st)]
                if len(visible) != 1:
                    errors.append(
                        f"ABDECKUNG S{cur['s']}: Vortest {pref}={g} -> "
                        f"{len(visible)} Kacheln sichtbar ({visible}) — "
                        f"erwartet genau 1")
                    break
        infos.append(f"S{cur['s']}: Abdeckung 0–100 je Vortest geprüft")

    # ---- 2) RATSCHE: Szenario-Läufe --------------------------------------- #
    def next_niveau(stage_idx: int, prev_ref: str, score: float):
        cur = stufen[stage_idx]
        pid = by_ref[prev_ref]
        st = mk_states({prev_ref: score})
        vis = [nk for nk, nm in cur["sections"].items()
               if eval_tree(sec_tree(nm), {pid: score}, st)]
        return vis[0] if len(vis) == 1 else None

    def check_transition(stage_idx: int, pkey: str, score: float, szenario: str):
        ref = stufen[stage_idx - 1]["tests"].get(pkey)
        if not ref:
            return
        want = expected_next(pkey, score)
        got = next_niveau(stage_idx, ref, score)
        if got != want:
            errors.append(f"RATSCHE: {szenario} ({pkey}, {score}%) führt zu "
                          f"'{got}' statt '{want}'")

    if len(stufen) >= 2:
        start_key = (pm.get("einstieg") if pm.get("einstieg") in stufen[0]["tests"]
                     else list(stufen[0]["tests"])[0])
        check_transition(1, start_key, auf + 5, "starker Start")
        check_transition(1, start_key, (ab + auf) / 2, "mittlere Leistung")
        check_transition(1, start_key, ab - 5, "schwacher Start")
    if len(stufen) >= 3:
        # Symmetrie über ALLE Pfade der Stufe 2: rauf, halten, runter
        for pkey in stufen[1]["tests"]:
            if pkey == top:
                check_transition(2, pkey, halt + 5, "solider Top-Pfad hält")
                check_transition(2, pkey, halt - 5, "schwacher Top-Pfad steigt ab")
            else:
                check_transition(2, pkey, auf + 5, "starker Pfad steigt auf")
                check_transition(2, pkey, (ab + auf) / 2, "Pfad hält Niveau")
                check_transition(2, pkey, ab - 5, "schwacher Pfad steigt ab")
    infos.append("Ratschen-Szenarien: Auf-/Abstieg symmetrisch geprüft "
                 f"({len(order)} Pfade: {', '.join(order)})")

    # ---- 3) FÖRDER + 4) DECKEL -------------------------------------------- #
    for st in stufen:
        if not st.get("foerder"):
            continue
        f_tree = sec_tree(st["foerder"])
        for nk, ref in st["tests"].items():
            pid = by_ref.get(ref)
            thr = halt if nk == top else ab
            if pid is None:
                continue
            if not eval_tree(f_tree, {pid: thr - 5}, mk_states({ref: thr - 5})):
                errors.append(f"FÖRDER S{st['s']}: {ref}={thr-5} öffnet die "
                              f"Förder-Kachel nicht")
            if eval_tree(f_tree, {pid: thr + 5}, mk_states({ref: thr + 5})):
                errors.append(f"FÖRDER S{st['s']}: {ref}={thr+5} öffnet die "
                              f"Förder-Kachel fälschlich")
    for st in stufen:
        for ref in st["tests"].values():
            got = attempts.get(ref)
            if got != pm["max_versuche"]:
                errors.append(f"DECKEL: {ref} hat attempts={got}, erwartet "
                              f"{pm['max_versuche']}")
    infos.append("Förder-Fenster + Versuchs-Deckel geprüft")

    # ---- 7) RETAKE: Pfad-Lock gegen die Null-Item-Invariante --------------- #
    # Szenario (Befund vom 2026-07-17): Vortest verhauen -> unteren Pfad
    # begonnen (Stufentest angefasst) -> Vortest-Retake auf Aufstiegsniveau.
    # Ohne Lock öffnet das den Geschwister-Pfad derselben Stufe: zwei Kacheln
    # sichtbar, zwei Tests füllbar, Doppel-Zählung im Gesamtscore.
    def visible_tiles(stage_idx: int, grades: dict[str, float]) -> set:
        cur = stufen[stage_idx]
        scores = {by_ref[r]: g for r, g in grades.items() if r in by_ref}
        st = mk_states(grades)
        return {nk for nk, nm in cur["sections"].items()
                if eval_tree(sec_tree(nm), scores, st)}

    def quiz_available(ref: str, grades: dict[str, float]) -> bool:
        m = mods.get(ref)
        if m is None:
            return True   # kein Modul-Lock vorhanden
        scores = {by_ref[r]: g for r, g in grades.items() if r in by_ref}
        return eval_tree(m["availability"], scores, mk_states(grades))

    for i in range(1, len(stufen)):
        prev, cur = stufen[i - 1], stufen[i]
        if len(cur["tests"]) < 2:
            continue
        pkey = (pm.get("einstieg") if pm.get("einstieg") in prev["tests"]
                else list(prev["tests"])[0])
        pref = prev["tests"][pkey]
        low = expected_next(pkey, ab - 5)
        high = expected_next(pkey, auf + 5)
        if low == high or low not in cur["tests"] or high not in cur["tests"]:
            continue
        grades = {pref: ab - 5}
        v1 = visible_tiles(i, grades)
        if v1 != {low}:
            errors.append(f"RETAKE S{cur['s']}: nach Vortest={ab-5} sichtbar "
                          f"{sorted(v1)}, erwartet nur '{low}'")
        grades[cur["tests"][low]] = (ab + auf) / 2   # eigenen Stufentest angefasst
        grades[pref] = auf + 5                       # Vortest-Retake (bester Versuch)
        v2 = visible_tiles(i, grades)
        if high in v2:
            errors.append(f"RETAKE S{cur['s']}: Vortest-Retake auf {auf+5} "
                          f"öffnet Geschwister-Kachel '{high}' trotz begonnenem "
                          f"Pfad '{low}' — Null-Item-Invariante verletzt")
        if low not in v2:
            errors.append(f"RETAKE S{cur['s']}: eigene Kachel '{low}' "
                          f"verschwindet nach Vortest-Retake, obwohl ihr Test "
                          f"schon gemacht wurde")
        if quiz_available(cur["tests"][high], grades):
            errors.append(f"RETAKE S{cur['s']}: Geschwister-Test "
                          f"'{cur['tests'][high]}' bleibt nach Retake füllbar "
                          f"— Doppel-Zählung im Gesamtscore möglich")
    if len(stufen[0]["tests"]) > 1:    # Einstieg "frei": 1. Versuch wählt Pfad
        keys = list(stufen[0]["tests"])
        a, b = keys[0], keys[1]
        grades = {stufen[0]["tests"][a]: 70.0}
        if quiz_available(stufen[0]["tests"][b], grades):
            errors.append(f"RETAKE S1 (frei): Test '{b}' bleibt füllbar, "
                          f"obwohl Pfad '{a}' schon angefasst wurde")
        if a not in visible_tiles(0, grades):
            errors.append(f"RETAKE S1 (frei): eigene Kachel '{a}' nach "
                          f"Testabgabe nicht mehr sichtbar")
    infos.append("Retake-/Pfad-Lock geprüft (erster Testversuch wählt den Pfad)")

    # ---- 5) KUMULATIV: Gewichte exakt ------------------------------------- #
    kum = [c for c in calcs if c["idnumber"] == pm["kumulativ_idnumber"]]
    if not kum:
        errors.append("KUMULATIV: kein Calculated-Item mit idnumber "
                      f"'{pm['kumulativ_idnumber']}' im Gradebook")
    else:
        formula = kum[0]["calculation"]
        got_weights = {}
        for gid_s, w in re.findall(r"##gi(\d+)##\*([0-9.]+)", formula):
            ref = by_id.get(int(gid_s))
            if ref is None:
                errors.append(f"KUMULATIV: Formel referenziert unbekanntes "
                              f"Item ##gi{gid_s}##")
                continue
            got_weights[ref] = float(w)
        for st in stufen:
            for nk, ref in st["tests"].items():
                want = float(pm["gewichte"][nk])
                if abs(got_weights.get(ref, -1) - want) > 1e-9:
                    errors.append(f"KUMULATIV: {ref} Gewicht "
                                  f"{got_weights.get(ref)} != {want}")
        extra = set(got_weights) - {r for st in stufen for r in st["tests"].values()}
        if extra:
            errors.append(f"KUMULATIV: Formel enthält fremde Items: {extra}")
        # ---- 8) GRADEMAX: Prozentanzeige muss lesbar sein ----------------- #
        # Pro Stufe füllt ein Lernender genau EIN Item; das real erreichbare
        # Maximum ist Σ je Stufe (max. Gewicht der emittierten Pfade × 100) —
        # nicht die Summe ALLER Items. Moodle klemmt Calculated-Ergebnisse
        # auf grademax (grade_item::bounded_grade).
        real_max = sum(max(float(pm["gewichte"][nk]) for nk in st["tests"])
                       for st in stufen) * 100.0
        if abs(kum[0]["grademax"] - real_max) > 1e-6:
            errors.append(f"GRADEMAX: kumulatives Item hat grademax="
                          f"{kum[0]['grademax']:g}, real erreichbar sind "
                          f"{real_max:g} — Prozentanzeige irreführend "
                          f"(bester Weg käme nur auf "
                          f"{100*real_max/max(kum[0]['grademax'],1e-9):.0f} %)")
        else:
            infos.append(f"grademax={real_max:g} = bestmöglicher Weg (100 %)")
        # Beispielrechnung: ein konkreter Lernweg
        sample = []
        for st in stufen:
            nk = (pm.get("einstieg") if pm.get("einstieg") in st["tests"]
                  else list(st["tests"])[0])
            sample.append((st["tests"][nk], 70.0, pm["gewichte"][nk]))
        expect = sum(g * w for _, g, w in sample)
        infos.append(f"Kumulativ-Formel verifiziert; Beispielweg (überall 70 %) "
                     f"ergäbe {expect:g} Punkte")

    # ---- 6) ENTKOPPLUNG: availability zeigt nie aufs kumulative Item ------ #
    calc_ids = {c["id"] for c in calcs}
    for name, s in secs.items():
        bad = referenced_grade_ids(s["availability"]) & calc_ids
        if bad:
            errors.append(f"ENTKOPPLUNG: Section '{name}' referenziert das "
                          f"kumulative Item {bad} — Ratschen-Effekt!")
    for path, data in xml.items():
        if not path.endswith("/module.xml"):
            continue
        av = ET.fromstring(data).findtext("availability") or ""
        if av and av != "$@NULL@$":
            bad = referenced_grade_ids(json.loads(av)) & calc_ids
            if bad:
                errors.append(f"ENTKOPPLUNG: {path} referenziert das "
                              f"kumulative Item {bad} — Ratschen-Effekt!")
    infos.append("Entkopplung (Einstufung ≠ kumulatives Item) geprüft")

    # ---- Report ------------------------------------------------------------ #
    for i in infos:
        print(f"  info: {i}")
    if errors:
        print(f"FAIL: {len(errors)} Verstoß/Verstöße:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("OK: adaptiver Lernpfad ist durchlässig, lückenlos und ratschen-frei.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: python simulate_pathways.py <kurs.mbz> <pathmap.json>")
        sys.exit(2)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    sys.exit(main(sys.argv[1], sys.argv[2]))
