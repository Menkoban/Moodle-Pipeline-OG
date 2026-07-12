#!/usr/bin/env python3
"""Adaptive Lernpfade: expandiert eine Stufen-Definition (adaptive-Spec) in
eine normale course.json mit verzweigten Niveau-Kacheln, Tests, Wiederhol-
schleife und gewichtetem Dokumentations-Gradebook.

Kernprinzip (references/adaptive-lernpfade.md): Einstufung und Bewertung sind
ENTKOPPELT. Die Kachel-Sichtbarkeit hängt nur an der Note des LETZTEN Tests
relativ zum aktuellen Niveau (availability-Fenster, §4.1); der gewichtete
kumulative Gesamtscore (Null-Item-Trick, §5/§6) ist reine Doku und steuert
NICHTS — sonst Ratschen-Effekt (§3).

Verzweigungsmatrix (Fenster sind harte Kanten: erfüllt wenn min <= note < max):

    vorher \\ Note   [0..ab)      [ab..auf)     [auf..100]
    Anfänger        Anfänger*    Anfänger      Mittel
    Mittel          Anfänger     Mittel        Fortgeschritten
    vorher \\ Note   [0..halt)                  [halt..100]
    Fortgeschritten Mittel                     Fortgeschritten

    * plus Förder-Kachel derselben Stufe (Wiederholschleife); Deckel = Quiz-
      Versuchsbegrenzung (max_versuche, Bewertung: bester Versuch).

Einstieg "mittel": Stufe 1 besteht nur aus der Mittel-Kachel + Mittel-Test.

Usage:
    python build_adaptive.py adaptive.json -o course.json
    # schreibt zusätzlich <output>.pathmap.json für simulate_pathways.py
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys

NIVEAUS = ("anfaenger", "mittel", "fortgeschritten")
NIVEAU_LABEL = {"anfaenger": "Anfänger", "mittel": "Mittel",
                "fortgeschritten": "Fortgeschritten"}

DEFAULT_GEWICHTE = {"anfaenger": 1.0, "mittel": 1.5, "fortgeschritten": 2.0}
DEFAULT_SCHWELLEN = {"aufstieg": 80, "abstieg": 40,
                     "fortgeschritten_halten": 50, "hysterese_abstieg": None}


def _cond(ref: str, mn=None, mx=None) -> dict:
    c = {"type": "grade", "ref": ref}
    if mn is not None:
        c["min"] = mn
    if mx is not None:
        c["max"] = mx
    return c


def _availability(conds: list[dict]) -> dict:
    """Ein oder mehrere grade-Fenster -> availability-Spec. Kacheln bleiben
    unsichtbar solange unerfüllt (show/showc false)."""
    if len(conds) == 1:
        return {"op": "&", "c": conds, "showc": [False]}
    return {"op": "|", "c": conds, "show": False}


def _test_ref(s: int, niveau: str) -> str:
    return f"test-s{s}-{niveau}"


def expand(spec: dict) -> tuple[dict, dict]:
    """adaptive-Spec -> (course.json-Spec, pathmap) — pathmap beschreibt die
    erwartete Verzweigungslogik für simulate_pathways.py."""
    ad = spec.get("adaptive")
    if not ad:
        raise SystemExit("Spec hat keinen 'adaptive'-Block — nichts zu expandieren.")
    stufen = ad.get("stufen") or []
    if not stufen:
        raise SystemExit("adaptive.stufen ist leer.")

    einstieg = ad.get("einstieg", "mittel")
    gewichte = {**DEFAULT_GEWICHTE, **(ad.get("gewichte") or {})}
    sw = {**DEFAULT_SCHWELLEN, **(ad.get("schwellen") or {})}
    auf = float(sw["aufstieg"])
    ab = float(sw["hysterese_abstieg"] or sw["abstieg"])
    halt = float(sw["fortgeschritten_halten"])
    max_versuche = int((ad.get("wiederholung") or {}).get("max_versuche", 3))

    out = {k: copy.deepcopy(v) for k, v in spec.items() if k != "adaptive"}
    sections: list[dict] = []
    pathmap: dict = {
        "einstieg": einstieg,
        "schwellen": {"aufstieg": auf, "abstieg": ab,
                      "fortgeschritten_halten": halt},
        "gewichte": gewichte,
        "max_versuche": max_versuche,
        "kumulativ_idnumber": "gesamtscore",
        "stufen": [],
    }
    weights_by_ref: dict[str, float] = {}

    # ---- Abschnitt 0: Intro (mit Erklärung des adaptiven Systems) -------- #
    intro = copy.deepcopy(ad.get("intro_section") or
                          {"name": "Über diesen Kurs", "activities": []})
    intro.setdefault("activities", []).insert(0, {
        "type": "label", "name": "So funktioniert dieser Kurs",
        "intro": (
            "<p>🧭 <b>Dieser Kurs passt sich dir an.</b> Jede Stufe gibt es in "
            "drei Niveaus. Nach jedem Test öffnet sich automatisch die Kachel, "
            "die zu deiner aktuellen Leistung passt — du kannst jederzeit auf- "
            "und absteigen. Deine Gesamtbewertung zählt Tests auf höherem "
            "Niveau stärker; sie dokumentiert deinen Weg, steuert ihn aber "
            "nicht.</p>"),
    })
    sections.append(intro)

    # ---- Stufen ----------------------------------------------------------- #
    def niveau_section(s: int, stufe: dict, nkey: str, conds: list[dict] | None) -> dict:
        nv = stufe["niveaus"][nkey]
        ref = _test_ref(s, nkey)
        test = copy.deepcopy(nv["test"])
        test.setdefault("type", "quiz")
        test["idnumber"] = ref
        test["grade"] = 100            # Prozent-Semantik für die Fenster
        test["attempts"] = max_versuche
        test["gradepass"] = ab if nkey != "fortgeschritten" else halt
        test.setdefault("completion", 1)
        sec = {
            "name": f"S{s} · {stufe['name']} — {nv.get('titel', NIVEAU_LABEL[nkey])}",
            "summary": nv.get("summary", ""),
            "activities": list(copy.deepcopy(nv.get("activities", []))) + [test],
        }
        if nv.get("image"):
            sec["image"] = nv["image"]
        if conds:
            sec["availability"] = _availability(conds)
        weights_by_ref[ref] = float(gewichte[nkey])
        return sec

    prev_tests: dict[str, str] | None = None  # niveau -> ref der Vorstufe

    for idx, stufe in enumerate(stufen, start=1):
        entry = {"s": idx, "name": stufe["name"], "sections": {},
                 "tests": {}, "foerder": None}
        cur_tests: dict[str, str] = {}

        if idx == 1 and einstieg == "mittel":
            niveaus_hier = ["mittel"]
        else:
            niveaus_hier = list(NIVEAUS)

        for nkey in niveaus_hier:
            if idx == 1:
                conds = None  # Stufe 1: offen (mittel für alle / freie Wahl)
            else:
                conds = []
                # Fenster gemäß Verzweigungsmatrix, nur für existierende Vortests
                if nkey == "anfaenger":
                    if "anfaenger" in prev_tests:
                        conds.append(_cond(prev_tests["anfaenger"], mx=auf))
                    if "mittel" in prev_tests:
                        conds.append(_cond(prev_tests["mittel"], mx=ab))
                elif nkey == "mittel":
                    if "anfaenger" in prev_tests:
                        conds.append(_cond(prev_tests["anfaenger"], mn=auf))
                    if "mittel" in prev_tests:
                        conds.append(_cond(prev_tests["mittel"], mn=ab, mx=auf))
                    if "fortgeschritten" in prev_tests:
                        conds.append(_cond(prev_tests["fortgeschritten"], mx=halt))
                else:  # fortgeschritten
                    if "mittel" in prev_tests:
                        conds.append(_cond(prev_tests["mittel"], mn=auf))
                    if "fortgeschritten" in prev_tests:
                        conds.append(_cond(prev_tests["fortgeschritten"], mn=halt))
            sec = niveau_section(idx, stufe, nkey, conds)
            sections.append(sec)
            entry["sections"][nkey] = sec["name"]
            cur_tests[nkey] = _test_ref(idx, nkey)
        entry["tests"] = dict(cur_tests)

        # Förder-/Wiederhol-Kachel dieser Stufe (Deckel = Quiz-Versuche)
        foerder = stufe.get("foerder")
        if foerder:
            f_conds = []
            if "anfaenger" in cur_tests:
                f_conds.append(_cond(cur_tests["anfaenger"], mx=ab))
            if "mittel" in cur_tests:
                f_conds.append(_cond(cur_tests["mittel"], mx=ab))
            if "fortgeschritten" in cur_tests:
                f_conds.append(_cond(cur_tests["fortgeschritten"], mx=halt))
            f_sec = {
                "name": f"S{idx} · {stufe['name']} — {foerder.get('titel', 'Fördervariante')}",
                "summary": foerder.get("summary",
                    "<p>Ein anderer Zugang zum Thema — danach den Test erneut "
                    "versuchen (bester Versuch zählt).</p>"),
                "activities": copy.deepcopy(foerder.get("activities", [])),
                "availability": _availability(f_conds),
            }
            if foerder.get("image"):
                f_sec["image"] = foerder["image"]
            sections.append(f_sec)
            entry["foerder"] = f_sec["name"]

        pathmap["stufen"].append(entry)
        prev_tests = cur_tests

    # ---- Abschluss-Abschnitt (optional) ----------------------------------- #
    if ad.get("abschluss_section"):
        sections.append(copy.deepcopy(ad["abschluss_section"]))

    # ---- Gradebook: kumulatives Doku-Item (Null-Item-Trick) ---------------- #
    out["gradebook"] = {
        "calculated": [{
            "itemname": "Gesamtscore (gewichtet, Dokumentation)",
            "idnumber": "gesamtscore",
            "weights": weights_by_ref,
        }]
    }
    out["sections"] = sections
    return out, pathmap


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Adaptive Stufen-Spec -> verzweigte course.json expandieren.")
    ap.add_argument("adaptive_json")
    ap.add_argument("-o", "--output", required=True,
                    help="Ziel-course.json (Pathmap: <output>.pathmap.json)")
    args = ap.parse_args()

    spec = json.load(open(args.adaptive_json, encoding="utf-8"))
    course, pathmap = expand(spec)
    json.dump(course, open(args.output, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    pm_path = os.path.splitext(args.output)[0] + ".pathmap.json"
    json.dump(pathmap, open(pm_path, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    n_sec = len(course["sections"])
    n_tests = len(pathmap["stufen"]) and sum(len(e["tests"]) for e in pathmap["stufen"])
    print(f"Expandiert: {len(pathmap['stufen'])} Stufen -> {n_sec} Sections, "
          f"{n_tests} Tests. Kurs: {args.output}  Pathmap: {pm_path}")


if __name__ == "__main__":
    main()
