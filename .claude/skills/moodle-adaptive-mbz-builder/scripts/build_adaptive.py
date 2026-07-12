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

# Default: klassische 3 Niveaupfade. Über adaptive.niveaus frei
# konfigurierbar (2–4 Pfade, beliebige keys/Labels, geordnet von
# niedrigster zu höchster Anforderung) — z. B. Differenzierung nach
# Sprache: [{"key":"einfache-sprache",...},{"key":"standard",...},
# {"key":"fachsprache",...}].
DEFAULT_NIVEAUS = [
    {"key": "anfaenger", "label": "Anfänger"},
    {"key": "mittel", "label": "Mittel"},
    {"key": "fortgeschritten", "label": "Fortgeschritten"},
]

DEFAULT_SCHWELLEN = {"aufstieg": 80, "abstieg": 40,
                     "fortgeschritten_halten": 50, "hysterese_abstieg": None}


def default_gewichte(order: list[str]) -> dict[str, float]:
    """Linear gespreizte Gewichte 1,0 … 2,0 über die Pfad-Reihenfolge."""
    k = len(order)
    if k == 1:
        return {order[0]: 1.0}
    return {key: round(1.0 + i / (k - 1), 2) for i, key in enumerate(order)}


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

    # ---- Niveaupfade (konfigurierbar, geordnet niedrig -> hoch) ----------- #
    niv_defs = ad.get("niveaus") or DEFAULT_NIVEAUS
    niv_defs = [{"key": n} if isinstance(n, str) else dict(n) for n in niv_defs]
    order = [n["key"] for n in niv_defs]
    if len(order) < 2:
        raise SystemExit("adaptive.niveaus braucht mindestens 2 Pfade "
                         "(sonst gibt es nichts zu adaptieren).")
    if len(order) != len(set(order)):
        raise SystemExit(f"adaptive.niveaus: doppelte keys in {order}.")
    labels = {n["key"]: n.get("label", n["key"].replace("-", " ").title())
              for n in niv_defs}
    top = order[-1]
    k = len(order)

    einstieg = ad.get("einstieg") or order[k // 2]
    if einstieg not in order and einstieg not in ("frei", "alle"):
        raise SystemExit(f"adaptive.einstieg '{einstieg}' ist kein Pfad-Key "
                         f"aus {order} (oder 'frei').")
    gewichte = {**default_gewichte(order), **(ad.get("gewichte") or {})}
    sw = {**DEFAULT_SCHWELLEN, **(ad.get("schwellen") or {})}
    auf = float(sw["aufstieg"])
    ab = float(sw["hysterese_abstieg"] or sw["abstieg"])
    halt = float(sw["fortgeschritten_halten"])
    max_versuche = int((ad.get("wiederholung") or {}).get("max_versuche", 3))

    out = {k: copy.deepcopy(v) for k, v in spec.items() if k != "adaptive"}
    sections: list[dict] = []
    pathmap: dict = {
        "einstieg": einstieg,
        "niveaus": order,
        "labels": labels,
        "differenzierung": ad.get("differenzierung") or ["niveau"],
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
    pfade_txt = " · ".join(labels[key] for key in order)
    intro.setdefault("activities", []).insert(0, {
        "type": "label", "name": "So funktioniert dieser Kurs",
        "intro": (
            f"<p>🧭 <b>Dieser Kurs passt sich dir an.</b> Jede Stufe gibt es "
            f"in {k} Varianten ({pfade_txt}). Nach jedem Test öffnet sich "
            "automatisch die Kachel, die zu deiner aktuellen Leistung passt — "
            "du kannst jederzeit auf- und absteigen. Deine Gesamtbewertung "
            "zählt Tests auf anspruchsvolleren Pfaden stärker; sie "
            "dokumentiert deinen Weg, steuert ihn aber nicht.</p>"),
    })
    sections.append(intro)

    # ---- Verzweigungsmatrix, generisch für k Pfade ------------------------ #
    def _bands_from(i: int) -> list[tuple]:
        """Bänder (min, max, ziel_index) für den Vortest von Pfad-Index i.
        Oberster Pfad: halten ab `halt`, sonst eine Stufe runter. Andere:
        < ab runter (Index 0 bleibt unten), [ab, auf) halten, >= auf rauf."""
        if i == k - 1:
            return [(None, halt, k - 2), (halt, None, k - 1)]
        raw = [(None, ab, max(i - 1, 0)), (ab, auf, i),
               (auf, None, min(i + 1, k - 1))]
        merged: list[list] = []
        for mn, mx, t in raw:
            if merged and merged[-1][2] == t and merged[-1][1] == mn:
                merged[-1][1] = mx
            else:
                merged.append([mn, mx, t])
        return [tuple(b) for b in merged]

    def _window_conds(prev_tests: dict[str, str], nkey: str) -> list[dict]:
        """availability-Fenster für Ziel-Pfad nkey aus allen Vortests."""
        j = order.index(nkey)
        conds = []
        for pkey, pref in prev_tests.items():
            for mn, mx, t in _bands_from(order.index(pkey)):
                if t == j:
                    conds.append(_cond(pref, mn=mn, mx=mx))
        return conds

    # ---- Stufen ----------------------------------------------------------- #
    def niveau_section(s: int, stufe: dict, nkey: str, conds: list[dict] | None) -> dict:
        nv = stufe["niveaus"][nkey]
        ref = _test_ref(s, nkey)
        test = copy.deepcopy(nv["test"])
        test.setdefault("type", "quiz")
        test["idnumber"] = ref
        test["grade"] = 100            # Prozent-Semantik für die Fenster
        test["attempts"] = max_versuche
        test["gradepass"] = halt if nkey == top else ab
        test.setdefault("completion", 1)
        sec = {
            "name": f"S{s} · {stufe['name']} — {nv.get('titel', labels[nkey])}",
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

        fehlend = [key for key in order if key not in stufe.get("niveaus", {})]
        if fehlend:
            raise SystemExit(f"Stufe {idx} '{stufe.get('name')}': Pfad(e) "
                             f"{fehlend} fehlen in stufe.niveaus.")

        if idx == 1:
            # Alle starten auf dem Einstiegs-Pfad; 'frei' = freie Wahl.
            niveaus_hier = [(key, None) for key in
                            ([einstieg] if einstieg in order else order)]
        else:
            # Nur ERREICHBARE Pfade emittieren: ein Pfad ohne Fenster aus der
            # Vorstufe (z. B. der unterste direkt nach einem hohen Einstieg)
            # bekäme sonst KEINE Bedingung und stünde dauerhaft offen.
            niveaus_hier = []
            for key in order:
                conds = _window_conds(prev_tests, key)
                if conds:
                    niveaus_hier.append((key, conds))

        for nkey, conds in niveaus_hier:
            sec = niveau_section(idx, stufe, nkey, conds)
            sections.append(sec)
            entry["sections"][nkey] = sec["name"]
            cur_tests[nkey] = _test_ref(idx, nkey)
        entry["tests"] = dict(cur_tests)

        # Förder-/Wiederhol-Kachel dieser Stufe (Deckel = Quiz-Versuche)
        foerder = stufe.get("foerder")
        if foerder:
            f_conds = [_cond(cur_tests[key], mx=(halt if key == top else ab))
                       for key in order if key in cur_tests]
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

    # ---- Abschluss-Abschnitt: Kurs-Recap nach Rode-Pflicht-Sequenz -------- #
    # Der Lernkurs endet wie im linearen Skill mit einem Kurs-Recap:
    # Videozusammenfassung-Platzhalter (NotebookLM, via set_recap_video.py
    # befüllbar) + „Hinweis zur Entstehung" (Pflicht-Attribution). Beides wird
    # automatisch ergänzt, falls der Autor es nicht selbst vorgesehen hat.
    abschluss = copy.deepcopy(ad.get("abschluss_section") or
                              {"name": "Abschluss & Kurs-Recap",
                               "summary": "<p>Rückblick, Video-Recap und dein "
                                          "Gesamtergebnis.</p>",
                               "activities": []})
    acts = abschluss.setdefault("activities", [])
    have = " ".join(a.get("name", "").lower() for a in acts)
    if "video" not in have:
        acts.append({
            "type": "label", "name": "Videozusammenfassung",
            "intro": "<p>🎬 Kurze Videozusammenfassung der wichtigsten "
                     "Punkte (NotebookLM).</p>",
        })
    if "entstehung" not in have:
        try:
            from build_mbz import ATTRIBUTION_SENTENCE as _attr
        except ImportError:
            _attr = ("Dieser Kurs ist mit Hilfe von Künstlicher Intelligenz "
                     "und in Kooperation mit dem Labor Didaktik der Technik "
                     "der Hochschule Osnabrück entstanden.")
        acts.append({
            "type": "label", "name": "Hinweis zur Entstehung",
            "intro": ("<p style=\"font-size:12px;color:#5f6672;\"><i>"
                      f"{_attr}</i></p>"),
        })
    sections.append(abschluss)

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
