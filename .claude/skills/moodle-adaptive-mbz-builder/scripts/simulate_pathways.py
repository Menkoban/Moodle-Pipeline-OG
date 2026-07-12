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


# --------------------------------------------------------------------------- #
# availability-Auswertung (Moodle-Semantik: erfüllt wenn min <= note < max;
# leere Note (Test nicht gemacht) erfüllt eine grade-Bedingung NIE)
# --------------------------------------------------------------------------- #
def eval_tree(tree, scores: dict[int, float]) -> bool:
    if tree is None:
        return True
    op = tree.get("op", "&")
    results = []
    for c in tree.get("c", []):
        if "op" in c:
            results.append(eval_tree(c, scores))
        elif c.get("type") == "grade":
            g = scores.get(int(c["id"]))
            ok = g is not None
            if ok and "min" in c:
                ok = g >= float(c["min"])
            if ok and "max" in c:
                ok = g < float(c["max"])
            results.append(ok)
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

    sw = pm["schwellen"]
    auf, ab, halt = sw["aufstieg"], sw["abstieg"], sw["fortgeschritten_halten"]
    errors, infos = [], []

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
                visible = [nk for nk, tree in cur_secs.items()
                           if eval_tree(tree, {pid: g})]
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
        vis = [nk for nk, nm in cur["sections"].items()
               if eval_tree(sec_tree(nm), {pid: score})]
        return vis[0] if len(vis) == 1 else None

    if len(stufen) >= 2:
        start_ref = stufen[0]["tests"].get("mittel") or list(stufen[0]["tests"].values())[0]
        up = next_niveau(1, start_ref, auf + 5)
        if up != "fortgeschritten":
            errors.append(f"RATSCHE: starker Start ({auf+5}%) führt zu "
                          f"'{up}' statt 'fortgeschritten'")
        stay = next_niveau(1, start_ref, (ab + auf) / 2)
        if stay != "mittel":
            errors.append(f"RATSCHE: mittlere Leistung führt zu '{stay}' statt 'mittel'")
        down = next_niveau(1, start_ref, ab - 5)
        if down != "anfaenger":
            errors.append(f"RATSCHE: schwacher Start ({ab-5}%) führt zu "
                          f"'{down}' statt 'anfaenger'")
    if len(stufen) >= 3:
        fort_ref = stufen[1]["tests"].get("fortgeschritten")
        if fort_ref:
            d = next_niveau(2, fort_ref, halt - 5)
            if d != "mittel":
                errors.append(f"RATSCHE: schwacher Fortgeschrittener ({halt-5}%) "
                              f"steigt nicht ab (-> '{d}' statt 'mittel')")
            h = next_niveau(2, fort_ref, halt + 5)
            if h != "fortgeschritten":
                errors.append(f"RATSCHE: solider Fortgeschrittener ({halt+5}%) "
                              f"hält das Niveau nicht (-> '{h}')")
        anf_ref = stufen[1]["tests"].get("anfaenger")
        if anf_ref:
            u = next_niveau(2, anf_ref, auf + 5)
            if u != "mittel":
                errors.append(f"RATSCHE: starker Anfänger ({auf+5}%) steigt "
                              f"nicht auf (-> '{u}' statt 'mittel')")
    infos.append("Ratschen-Szenarien: Auf-/Abstieg symmetrisch geprüft")

    # ---- 3) FÖRDER + 4) DECKEL -------------------------------------------- #
    for st in stufen:
        if not st.get("foerder"):
            continue
        f_tree = sec_tree(st["foerder"])
        for nk, ref in st["tests"].items():
            pid = by_ref.get(ref)
            thr = halt if nk == "fortgeschritten" else ab
            if pid is None:
                continue
            if not eval_tree(f_tree, {pid: thr - 5}):
                errors.append(f"FÖRDER S{st['s']}: {ref}={thr-5} öffnet die "
                              f"Förder-Kachel nicht")
            if eval_tree(f_tree, {pid: thr + 5}):
                errors.append(f"FÖRDER S{st['s']}: {ref}={thr+5} öffnet die "
                              f"Förder-Kachel fälschlich")
    for st in stufen:
        for ref in st["tests"].values():
            got = attempts.get(ref)
            if got != pm["max_versuche"]:
                errors.append(f"DECKEL: {ref} hat attempts={got}, erwartet "
                              f"{pm['max_versuche']}")
    infos.append("Förder-Fenster + Versuchs-Deckel geprüft")

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
        # Beispielrechnung: ein konkreter Lernweg
        sample = []
        for st in stufen:
            nk = "mittel" if "mittel" in st["tests"] else list(st["tests"])[0]
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
