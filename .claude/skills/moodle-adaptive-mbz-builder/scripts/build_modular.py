#!/usr/bin/env python3
"""Diagnose-Modul-Modell (Konzept v3, Teil B — normativ): expandiert eine
modulare Spezifikation in eine normale course.json + modmap.json.

Zweiter Modus neben dem Stufen-Modell (build_adaptive.py). Auswahl über
`adaptive.modell`: "diagnose" (dieses Skript) vs. "stufen" (Default alt).

Strukturmodell je Modul (= eine Kachel/Section):
  1. DIAGNOSE     — Kurztest (5–8 Items), Bewertungskategorie „Einstufung"
                    mit Gewicht 0 (entkoppelte Scoring-Architektur): steuert
                    NUR die Pfadzuweisung, nie die Note. gradepass=0 ist
                    Pflicht — so bleibt der completion-Zustand nach dem
                    Versuch exakt 1 (complete) und das Diagnose-Gate (e=1)
                    greift auch bei 0 Punkten.
  2. NIVEAUPFADE  — basic/standard/advanced über grade-Fenster auf die
                    Diagnose (harte Kanten min ≤ g < max, normalisiert aus
                    level_thresholds).
  3. KONVERGENZ   — EINE bewertete Aktivität (Kategorie „Leistung"), Gate:
                    OR über completion des letzten Pflichtelements je Pfad.
  4. FREISCHALTUNG— Folgemodul-Section per grade ≥ pass auf die Konvergenz;
                    darunter wird der Remediationsblock sichtbar.

Schichtenmodell: NUR Niveau ist multiplikativ (echte Pfade). Alle weiteren
Dimensionen sind additive Overlays (Gruppen-/date-/grade-Bedingungen), die
einzelne Elemente ein-/ausblenden — Wachstum 3+2+2 statt 3×2×2. Der
Bedingungsbaum je Element bleibt flach (Tiefe ≤ 2, ≤ 3 Blätter, B.3.10 —
Verstoß bricht ab statt still zu kürzen).

Golden-Template-Fakten (aus echtem Moodle-4.5-Lab-Backup extrahiert,
2026-07-17): group-Bedingung {"type":"group","id":N}, Negation als
!|-Teilbaum, date {"type":"date","d":">=","t":unix}; Gruppen wandern über
groups.xml + Root-Setting groups=1 (inforef bleibt LEER — anders als das
Konzeptpapier annimmt); Kategorien-Gewichte leben als aggregationcoef2 +
weightoverride=1 am Kategorie-Item (itemtype category, aggregation 13).

Usage:
    python build_modular.py modular.json -o course.json
    # schreibt zusätzlich <output>.modmap.json für simulate_modular.py
"""
from __future__ import annotations

import argparse
import calendar
import copy
import datetime as _dt
import json
import os
import sys


class ModularSpecError(ValueError):
    """B.4-Validierungsfehler — Build wird abgebrochen, nichts still gekürzt."""


# --------------------------------------------------------------------------- #
# Layer-Registry (B.5.6) — datengetrieben, ein Eintrag je Overlay.
# kind: group          -> Gruppen-Bedingung (ggf. negiert via "without")
#       group_or_date  -> Gruppe ODER date-Bedingung (layer_config.quelle)
#       grade_below_pass -> grade-Fenster unter der Bestehensgrenze der
#                         Konvergenz desselben Moduls (Wiederholer)
# values: erlaubte visibility-Werte (B.4.8). True ≡ "with".
# frage: Selbsteinschätzungs-Choice im Startabschnitt (B.6).
# Hinweis H5P: Elementtyp "h5p" ist bewusst NICHT gebaut (User-Entscheid
# 2026-07-18: erst weglassen, vorbereiten) — Erweiterungspunkt wäre ein
# ACTIVITY_BUILDER "h5pactivity" in build_mbz.py + Content-Pipeline.
# --------------------------------------------------------------------------- #
LAYER_REGISTRY: dict[str, dict] = {
    "language_support": {
        "label": "Sprachhilfe", "kind": "group",
        "group": {"id": "GRP-SPRACHE", "name": "Sprachhilfe"},
        "values": (True,),   # B.4.8: es gibt keine „nur für Nicht-DaZ"-Inhalte
        "frage": "Möchtest du sprachliche Unterstützung (Glossar, einfach "
                 "erklärte Fachbegriffe, Satzstarter)?",
    },
    "practice_experience": {
        "label": "Praxiserfahrung", "kind": "group",
        "group": {"id": "GRP-PRAXIS", "name": "Praxiserfahrung"},
        "values": ("with", "without"),   # tri-state: with/without/unset
        "frage": "Kennst du dieses Themenfeld schon aus der Praxis in "
                 "deinem Betrieb?",
    },
    "pruefungsnaehe": {
        "label": "Prüfungsvorbereitung", "kind": "group_or_date",
        "group": {"id": "GRP-PRUEFUNG", "name": "Prüfungsvorbereitung"},
        "values": (True,),
        "frage": "Möchtest du prüfungsnahe Zusatzaufgaben (AP1/AP2-Stil) "
                 "bearbeiten?",
    },
    "wiederholer": {
        "label": "Wiederholer / 2. Anlauf", "kind": "grade_below_pass",
        "values": (True,),
    },
    "anschlussorientierung": {
        "label": "Anschlussorientierung", "kind": "group",
        "group": {"id": "GRP-ANSCHLUSS", "name": "Anschlussorientierung"},
        "values": (True, "with", "without"),
        "frage": "Strebst du Techniker, Meister oder ein Studium an und "
                 "möchtest theorielastige Vertiefungen sehen?",
    },
    "verkuerzer": {
        "label": "Verkürzer", "kind": "group",
        "group": {"id": "GRP-VERKUERZER", "name": "Verkürzer"},
        "values": (True, "with", "without"),
        "frage": "Verkürzt du deine Ausbildung (verdichtete Instruktion "
                 "gewünscht)?",
    },
    "umschueler": {
        "label": "Umschulung / Erwachsene", "kind": "group",
        "group": {"id": "GRP-UMSCHUELER", "name": "Umschulung"},
        "values": (True, "with", "without"),
        "frage": "Bist du Umschüler/-in bzw. bringst du Berufserfahrung aus "
                 "einem anderen Feld mit?",
    },
}

KERN_LAYERS = ("language_support", "practice_experience")

DEFAULT_THRESHOLDS = [
    {"level": "basic", "min": 0.0, "max": 49.99},
    {"level": "standard", "min": 50.0, "max": 79.99},
    {"level": "advanced", "min": 80.0, "max": 100.0},
]

DEFAULT_PACING = {"unlock_rule": "grade_min", "unlock_threshold": 50.0,
                  "remediation": True}

MAX_LEAVES = 3      # B.3.10 — Blattbedingungen je Element
MAX_DEPTH = 2       # B.3.10 — Baumtiefe

# Rollen, die selbst Overlay-Inhalte SIND (dürfen Overlay-Bedingungen tragen;
# alle anderen Rollen: höchstens EINE Overlay-Bedingung, B.4.9).
OVERLAY_ROLES = {"sprachhilfe", "praxis_anknuepfung", "praxis_kompensation",
                 "vertiefung", "pruefungsvorbereitung", "wiederholung",
                 "anschluss", "verkuerzer", "umschueler"}

# Typen, deren Abschluss über „Ansehen" automatisch erfassbar ist — nur sie
# taugen als „letztes Pflichtelement je Pfad" fürs Konvergenz-Gate (B.3.7).
VIEW_COMPLETION_TYPES = {"page", "book", "url", "file", "folder"}


# --------------------------------------------------------------------------- #
# Schwellen -> lückenlose harte Kanten
# --------------------------------------------------------------------------- #
def normalize_thresholds(thresholds: list[dict] | None) -> dict[str, tuple]:
    """B.2-Schwellen (0–49.99/50–79.99/80–100) -> Fenster mit harten Kanten
    (min ≤ g < max): unterstes Fenster offen nach unten (None), oberstes
    offen nach oben — deckt garantiert JEDE reelle Note ab (lückenlos trotz
    49.99-Schreibweise; die UI-Lücke 49.99..50 existiert in Moodle nicht)."""
    ths = [dict(t) for t in (thresholds or DEFAULT_THRESHOLDS)]
    if len(ths) < 2:
        raise ModularSpecError("level_thresholds: mindestens 2 Level nötig.")
    ths.sort(key=lambda t: float(t["min"]))
    names = [t["level"] for t in ths]
    if len(names) != len(set(names)):
        raise ModularSpecError(f"level_thresholds: doppelte Level in {names}.")
    for prev, nxt in zip(ths, ths[1:]):
        gap = float(nxt["min"]) - float(prev["max"])
        if gap > 0.011:
            raise ModularSpecError(
                f"level_thresholds: nicht lückenlos — zwischen "
                f"{prev['level']} (max {prev['max']}) und {nxt['level']} "
                f"(min {nxt['min']}) klafft eine Lücke.")
        if float(nxt["min"]) < float(prev["max"]) - 1e-9:
            raise ModularSpecError(
                f"level_thresholds: nicht disjunkt — {prev['level']} und "
                f"{nxt['level']} überlappen.")
    if float(ths[0]["min"]) > 1e-9 or float(ths[-1]["max"]) < 99.99:
        raise ModularSpecError("level_thresholds: müssen 0–100 abdecken.")
    windows: dict[str, tuple] = {}
    for i, t in enumerate(ths):
        lo = None if i == 0 else float(t["min"])
        hi = None if i == len(ths) - 1 else float(ths[i + 1]["min"])
        windows[t["level"]] = (lo, hi)
    return windows


# --------------------------------------------------------------------------- #
# Availability-Composer (B.3) — reine Funktion visibility -> Bedingungsbaum
# --------------------------------------------------------------------------- #
def _leaves(tree: dict) -> list[dict]:
    out = []
    for c in tree.get("c", []):
        out.extend(_leaves(c) if "op" in c else [c])
    return out


def _depth(tree: dict, d: int = 1) -> int:
    kids = [c for c in tree.get("c", []) if "op" in c]
    return max([d] + [_depth(k, d + 1) for k in kids])


def _grade_cond(ref: str, lo, hi) -> dict:
    c: dict = {"type": "grade", "ref": ref}
    if lo is not None:
        c["min"] = float(lo)
    if hi is not None:
        c["max"] = float(hi)
    return c


def _level_node(levels_sel: list[str], ctx: dict) -> dict:
    """Gewählte Level -> grade-Fenster; ZUSAMMENHÄNGENDE Level verschmelzen
    zu EINEM Fenster (weniger Blätter), sonst OR-Teilbaum."""
    order = ctx["levels"]
    unknown = [l for l in levels_sel if l not in order]
    if unknown:
        raise ModularSpecError(f"visibility.level: unbekannte Level {unknown} "
                               f"(erlaubt: {order}).")
    idx = sorted(order.index(l) for l in levels_sel)
    runs: list[list[int]] = [[idx[0]]]
    for i in idx[1:]:
        if i == runs[-1][-1] + 1:
            runs[-1].append(i)
        else:
            runs.append([i])
    conds = [_grade_cond(ctx["diag"], ctx["windows"][order[r[0]]][0],
                         ctx["windows"][order[r[-1]]][1]) for r in runs]
    return conds[0] if len(conds) == 1 else {"op": "|", "c": conds}


def _parse_date(iso: str) -> int:
    d = _dt.datetime.strptime(str(iso), "%Y-%m-%d")
    return int(calendar.timegm(d.timetuple()))


def _layer_node(key: str, value, ctx: dict) -> dict:
    reg = LAYER_REGISTRY[key]
    allowed = reg["values"]
    if value not in allowed:
        raise ModularSpecError(
            f"visibility.{key}: Wert {value!r} unzulässig — erlaubt "
            f"{allowed} oder weglassen (B.4.8). Insbesondere "
            f"language_support: nur true oder weglassen.")
    if reg["kind"] == "grade_below_pass":
        return _grade_cond(ctx["conv"], None, ctx["pass"])
    if reg["kind"] == "group_or_date":
        cfg = (ctx.get("layer_config") or {}).get(key) or {}
        if cfg.get("quelle") == "datum":
            if not cfg.get("ab"):
                raise ModularSpecError(
                    f"layer_config.{key}: quelle 'datum' braucht 'ab' "
                    f"(ISO-Datum, z. B. 2026-04-01).")
            return {"type": "date", "d": ">=", "t": _parse_date(cfg["ab"])}
        # Default: Gruppen-Selbstwahl
    group_leaf = {"type": "group", "groupref": ctx["groups"][key]}
    if value == "without":
        return {"op": "!|", "c": [group_leaf]}
    return group_leaf


def compose_element_availability(vis: dict | None, ctx: dict) -> dict | None:
    """B.3: visibility-Koordinaten -> availability-Spec (symbolische refs).
    Reihenfolge der Kinder: (a) Diagnose-Gate, (b) Niveau, (c) Sprache,
    (d) Praxis, (e) weitere aktive Overlays in active_layers-Reihenfolge."""
    if not vis:
        return None
    vis = dict(vis)
    vis.pop("optional_self_select", None)   # Flag, keine eigene Bedingung
    for k in vis:
        if k != "level" and k not in LAYER_REGISTRY:
            raise ModularSpecError(f"visibility-Schlüssel '{k}' unbekannt — "
                                   f"erlaubt: level + {sorted(LAYER_REGISTRY)}.")
        if k != "level" and k not in ctx["active"]:
            raise ModularSpecError(
                f"visibility.{k}: Layer nicht in active_layers — inaktive "
                f"Schlüssel sind ein Spezifikationsfehler (B.2/B.4.7).")

    children: list[dict] = []
    if vis.get("level"):
        # (a) Diagnose-Gate: vor dem ersten Diagnoseversuch ist KEIN Pfad
        # sichtbar (B.3.2/B.7.8). e=1 reicht, weil die Diagnose gradepass=0
        # trägt und damit nach dem Versuch immer exakt Zustand 1 hat.
        children.append({"type": "completion", "cmref": ctx["diag"], "e": 1})
        children.append(_level_node(list(vis["level"]), ctx))
    for key in KERN_LAYERS:
        if key in vis:
            children.append(_layer_node(key, vis[key], ctx))
    for key in ctx["active"]:
        if key in KERN_LAYERS or key not in vis:
            continue
        children.append(_layer_node(key, vis[key], ctx))
    if not children:
        return None

    tree = {"op": "&", "c": children}
    n_leaves = len(_leaves(tree))
    if n_leaves > MAX_LEAVES:
        raise ModularSpecError(
            f"Bedingungsbaum hat {n_leaves} Blattbedingungen (> {MAX_LEAVES}, "
            f"B.3.10) — Overlay-Kombination reduzieren statt still kürzen. "
            f"Tipp: Overlay-Elemente ohne level-Einschränkung anlegen.")
    if _depth(tree) > MAX_DEPTH:
        raise ModularSpecError(f"Bedingungsbaum tiefer als {MAX_DEPTH} "
                               f"(B.3.10).")
    return tree


# --------------------------------------------------------------------------- #
# B.4-Validierung (vor dem Build, Pflicht)
# --------------------------------------------------------------------------- #
def _elements(module: dict) -> list[dict]:
    return module.get("elements") or module.get("elemente") or []


def validate_spec(spec: dict) -> dict:
    ad = spec.get("adaptive") or {}
    if ad.get("modell") != "diagnose":
        raise ModularSpecError("adaptive.modell muss 'diagnose' sein — für "
                               "das Stufen-Modell build_adaptive.py nutzen.")
    active = list(ad.get("active_layers") or [])
    for k in active:
        if k not in LAYER_REGISTRY:
            raise ModularSpecError(f"active_layers: '{k}' ist kein bekannter "
                                   f"Layer ({sorted(LAYER_REGISTRY)}).")
    optional = [k for k in active if k not in KERN_LAYERS]
    if len(optional) > 3:
        print(f"warn: {len(optional)} optionale Overlays aktiv — Empfehlung "
              f"sind höchstens 2–3 (C.6.2), Pflegbarkeit + B.3.10 im Blick "
              f"behalten.")

    windows = normalize_thresholds(ad.get("level_thresholds"))
    levels = list(windows)

    cats = ad.get("grade_categories") or [
        {"id": "einstufung", "name": "Einstufung (unbewertet)", "weight": 0.0},
        {"id": "leistung", "name": "Leistung", "weight": 1.0}]
    einst = next((c for c in cats if c["id"] == "einstufung"), None)
    if einst is None or abs(float(einst.get("weight", -1))) > 1e-9:
        raise ModularSpecError(
            "grade_categories: Kategorie 'einstufung' MUSS Gewicht 0 haben — "
            "das ist die entkoppelte Scoring-Architektur (B.4.3): die "
            "Diagnose darf die Endnote niemals beeinflussen.")

    modules = ad.get("modules") or []
    if not modules:
        raise ModularSpecError("adaptive.modules ist leer.")
    seen_ids: set[str] = set()
    for m in modules:
        mid = m.get("id") or ""
        if not mid or mid in seen_ids:
            raise ModularSpecError(f"Modul-id fehlt oder doppelt: {mid!r}.")
        seen_ids.add(mid)
        if not (m.get("diagnostic") or {}).get("questions"):
            raise ModularSpecError(f"Modul {mid}: diagnostic mit questions "
                                   f"ist Pflicht (B.4.2).")
        if not m.get("convergence"):
            raise ModularSpecError(f"Modul {mid}: convergence ist Pflicht "
                                   f"(B.4.2).")
        for e in _elements(m):
            eid = e.get("id") or ""
            if not eid or eid in seen_ids:
                raise ModularSpecError(f"Element-id fehlt oder doppelt: "
                                       f"{eid!r} (Modul {mid}).")
            seen_ids.add(eid)
            if e.get("type") == "h5p":
                raise ModularSpecError(
                    f"Element {eid}: Typ 'h5p' wird noch nicht unterstützt — "
                    f"vorbereiteter Erweiterungspunkt (mod_h5pactivity), bis "
                    f"dahin type 'page' (ggf. mit simulation/Video) nutzen.")
            vis = e.get("visibility") or {}
            if vis.get("language_support") is False:
                raise ModularSpecError(
                    f"Element {eid}: language_support: false ist unzulässig — "
                    f"nur true oder weglassen (B.4.8), es gibt keine "
                    f"„nur für Nicht-DaZ“-Inhalte.")
            n_overlay = sum(1 for k in vis if k in LAYER_REGISTRY)
            if e.get("role") not in OVERLAY_ROLES and n_overlay >= 2:
                raise ModularSpecError(
                    f"Element {eid} (Rolle {e.get('role')!r}): trägt "
                    f"{n_overlay} Overlay-Bedingungen — Komplexitätsdeckel "
                    f"B.4.9 erlaubt das nur für Overlay-Rollen.")
        # B.4.4: kein leerer Pfad
        for lvl in levels:
            ok = any(e.get("role") == "erarbeitung"
                     and (not (e.get("visibility") or {}).get("level")
                          or lvl in e["visibility"]["level"])
                     for e in _elements(m))
            if not ok:
                raise ModularSpecError(
                    f"Modul {mid}: kein Element mit Rolle 'erarbeitung' für "
                    f"Level '{lvl}' — leerer Pfad (B.4.4).")
        # B.4.5: Praxis-Anknüpfung braucht Kompensations-Gegenstück (Warnung)
        has_with = any((e.get("visibility") or {}).get("practice_experience")
                       == "with" and e.get("role") == "praxis_anknuepfung"
                       for e in _elements(m))
        has_without = any((e.get("visibility") or {}).get(
            "practice_experience") == "without" for e in _elements(m))
        if has_with and not has_without:
            print(f"warn: Modul {mid}: praxis_anknuepfung ohne Gegenstück "
                  f"'without' (Kompensation) — Lernortkooperation prüfen "
                  f"(B.4.5).")
    return {"active": active, "windows": windows, "levels": levels,
            "cats": cats, "modules": modules}


# --------------------------------------------------------------------------- #
# Expander
# --------------------------------------------------------------------------- #
def _mk_ctx(mid: str, checked: dict, ad: dict, pass_: float) -> dict:
    return {
        "diag": f"diag-{mid.lower()}",
        "conv": f"sich-{mid.lower()}",
        "pass": pass_,
        "levels": checked["levels"],
        "windows": checked["windows"],
        "groups": {k: LAYER_REGISTRY[k]["group"]["id"]
                   for k in LAYER_REGISTRY if "group" in LAYER_REGISTRY[k]},
        "active": checked["active"],
        "layer_config": ad.get("layer_config") or {},
    }


def expand(spec: dict) -> tuple[dict, dict]:
    checked = validate_spec(spec)
    ad = spec["adaptive"]
    active, levels, windows = checked["active"], checked["levels"], checked["windows"]
    pacing = {**DEFAULT_PACING, **(ad.get("pacing") or {})}
    max_versuche = int((ad.get("wiederholung") or {}).get("max_versuche", 3))
    layer_config = ad.get("layer_config") or {}

    out = {k: copy.deepcopy(v) for k, v in spec.items() if k != "adaptive"}
    sections: list[dict] = []

    # ---- Gruppen aus aktiven Layern ableiten ------------------------------ #
    groups = []
    for key in active:
        reg = LAYER_REGISTRY[key]
        if "group" not in reg:
            continue
        if reg["kind"] == "group_or_date" and \
                (layer_config.get(key) or {}).get("quelle") == "datum":
            continue    # zeitgesteuert -> keine Gruppe nötig
        g = dict(reg["group"])
        g["name"] = (layer_config.get(key) or {}).get("gruppe", g["name"])
        groups.append(g)
    out["groups"] = groups

    # ---- Intro: Erklärung + Selbsteinschätzung (B.6) ---------------------- #
    intro = copy.deepcopy(ad.get("intro_section") or
                          {"name": "Über diesen Kurs", "activities": []})
    acts = intro.setdefault("activities", [])
    acts.insert(0, {
        "type": "label", "name": "So funktioniert dieser Kurs",
        "intro": (
            "<p>🧭 <b>Dieser Kurs passt sich dir an.</b> Jedes Modul beginnt "
            "mit einer kurzen Einstufung (zählt NICHT für die Note) — danach "
            "öffnet sich der Lernpfad, der zu dir passt. Alle Pfade führen "
            "zum selben Abschlusstest des Moduls; erst der zählt. Zusätzliche "
            "Unterstützung (z. B. Sprachhilfe, Praxisbezüge) wird über deine "
            "Angaben unten eingeblendet.</p>"),
    })
    for key in active:
        reg = LAYER_REGISTRY[key]
        if "frage" not in reg or not any(g["id"] == reg.get("group", {}).get("id")
                                         for g in groups):
            continue
        acts.append({
            "type": "choice",
            "name": f"Selbsteinschätzung: {reg['label']}",
            "intro": f"<p>{reg['frage']}</p><p><i>Deine Antwort hilft der "
                     f"Lehrkraft, dir die passenden Materialien "
                     f"freizuschalten.</i></p>",
            "options": ["Ja", "Nein"],
        })
    if groups:
        gnames = ", ".join(f"„{g['name']}“" for g in groups)
        acts.append({
            "type": "label", "name": "Hinweis für die Lehrkraft",
            "intro": (f"<p style=\"font-size:12px;color:#5f6672;\"><i>👩‍🏫 Die "
                      f"Gruppen {gnames} werden beim Wiederherstellen "
                      f"angelegt (ohne Mitglieder). Bitte die Ergebnisse der "
                      f"Selbsteinschätzung in die Gruppen übertragen — die "
                      f"Zusatz-Elemente blenden sich dann automatisch ein. "
                      f"Nachteilsausgleich läuft bewusst NICHT über "
                      f"Sichtbarkeit, sondern über Nutzerüberschreibungen "
                      f"(z. B. verlängerte Testzeit im Quiz).</i></p>"),
        })
    sections.append(intro)

    # ---- Module ------------------------------------------------------------ #
    modmap: dict = {
        "modell": "diagnose", "active_layers": active, "levels": levels,
        "windows": {l: list(windows[l]) for l in levels},
        "unlock_rule": pacing["unlock_rule"],
        "groups": {k: LAYER_REGISTRY[k]["group"]["id"] for k in active
                   if any(g["id"] == LAYER_REGISTRY[k].get("group", {}).get("id")
                          for g in groups)},
        "layer_config": layer_config,
        "grade_categories": {c["id"]: float(c["weight"])
                             for c in checked["cats"]},
        "max_versuche": max_versuche,
        "modules": [],
    }
    prev_conv: str | None = None
    prev_pass: float | None = None

    for m in checked["modules"]:
        mid = m["id"]
        conv_spec = m["convergence"]
        pass_ = float(conv_spec.get("pass", conv_spec.get(
            "pass_threshold", pacing["unlock_threshold"])))
        ctx = _mk_ctx(mid, checked, ad, pass_)
        sec: dict = {
            "name": f"{mid} · {m.get('titel') or m.get('title') or mid}",
            "summary": m.get("summary", ""),
            "activities": [],
        }
        if m.get("image"):
            sec["image"] = m["image"]
        if prev_conv is not None:
            if pacing["unlock_rule"] == "completion":
                sec["availability"] = {"op": "&", "c": [
                    {"type": "completion", "cmref": prev_conv, "e": 2}]}
            else:
                sec["availability"] = {"op": "&", "c": [
                    _grade_cond(prev_conv, prev_pass, None)]}

        # 1) Diagnose — Kategorie Einstufung (Gewicht 0), gradepass=0 PFLICHT
        diag = copy.deepcopy(m["diagnostic"])
        diag.setdefault("name", f"Einstufung {mid}")
        diag.update({
            "type": "quiz", "idnumber": ctx["diag"], "grade": 100,
            "gradepass": 0, "attempts": int(ad.get("diagnose_versuche", 1)),
            "completion": 2, "completionusegrade": True,
            "grade_category": "einstufung",
        })
        sec["activities"].append(diag)

        # 2) Elemente (Pfade + Overlays)
        el_entries = []
        last_required: dict[str, str] = {}
        for e in _elements(m):
            act = {k: copy.deepcopy(v) for k, v in e.items()
                   if k not in ("id", "role", "visibility")}
            act.setdefault("name", act.pop("title", e["id"]))
            act["idnumber"] = e["id"].lower()
            vis = e.get("visibility") or {}
            av = compose_element_availability(vis, ctx)
            if av:
                act["availability"] = av
            if act.get("type") == "quiz":
                # Selbstchecks in Pfaden: unbewertet halten
                act.setdefault("grade_category", "einstufung")
                act.setdefault("gradepass", 0)
                act.setdefault("completion", 2)
                act.setdefault("completionusegrade", True)
            elif act.get("type") in VIEW_COMPLETION_TYPES:
                act.setdefault("completion", 2)
                act.setdefault("completionview", 1)
            sec["activities"].append(act)
            el_entries.append({"idnumber": act["idnumber"],
                               "role": e.get("role"), "visibility": vis,
                               "name": act["name"]})
            if (e.get("type") in VIEW_COMPLETION_TYPES
                    and not vis.get("optional_self_select")
                    and vis.get("level")):
                for lvl in vis["level"]:
                    last_required[lvl] = act["idnumber"]
        missing = [l for l in levels if l not in last_required]
        if missing:
            raise ModularSpecError(
                f"Modul {mid}: kein abschluss-fähiges Pfadelement (Typ "
                f"{sorted(VIEW_COMPLETION_TYPES)}) für Level {missing} — "
                f"das Konvergenz-Gate (B.3.7) braucht je Pfad ein letztes "
                f"Pflichtelement mit automatischem Abschluss.")

        # 3) Konvergenzpunkt — Kategorie Leistung, Gate: OR über Pfad-Abschluss
        conv = copy.deepcopy(conv_spec)
        conv.pop("pass", None); conv.pop("pass_threshold", None)
        conv.setdefault("name", f"Sicherung {mid}")
        conv.update({
            "type": conv.get("type", "quiz"), "idnumber": ctx["conv"],
            "grade": 100, "gradepass": pass_, "attempts": max_versuche,
            "completion": 2, "completionusegrade": True,
            "grade_category": "leistung",
        })
        gate_refs = []
        for lvl in levels:                      # dedupe, Reihenfolge stabil
            r = last_required[lvl]
            if r not in gate_refs:
                gate_refs.append(r)
        conv["availability"] = {"op": "|", "show": False, "c": [
            {"type": "completion", "cmref": r, "e": 1} for r in gate_refs]}
        sec["activities"].append(conv)

        # 4) Remediation — sichtbar genau unter der Bestehensgrenze (B.3.8)
        rem_names = []
        rem = m.get("remediation")
        if rem and pacing.get("remediation", True):
            rem_av = {"op": "&", "c": [_grade_cond(ctx["conv"], 0, pass_)]}
            header = {"type": "label",
                      "name": rem.get("name", "Nochmal anders erklärt"),
                      "intro": ("<p>🔁 <b>Noch nicht bestanden — kein "
                                "Problem.</b> Hier ist ein anderer Zugang "
                                "zum Thema; danach den Abschlusstest erneut "
                                "versuchen (bester Versuch zählt).</p>"),
                      "availability": copy.deepcopy(rem_av)}
            sec["activities"].append(header)
            rem_names.append(header["name"])
            for a in rem.get("activities", []):
                a = copy.deepcopy(a)
                a["availability"] = copy.deepcopy(rem_av)
                sec["activities"].append(a)
                rem_names.append(a.get("name", "?"))

        sections.append(sec)
        modmap["modules"].append({
            "id": mid, "section": sec["name"], "diag": ctx["diag"],
            "conv": ctx["conv"], "pass": pass_, "elements": el_entries,
            "last_required": last_required, "remediation": rem_names,
        })
        prev_conv, prev_pass = ctx["conv"], pass_

    # ---- Abschluss: Kurs-Recap (Rode) + Attribution ------------------------ #
    abschluss = copy.deepcopy(ad.get("abschluss_section") or
                              {"name": "Abschluss & Kurs-Recap",
                               "summary": "<p>Rückblick und Video-Recap.</p>",
                               "activities": []})
    aacts = abschluss.setdefault("activities", [])
    have = " ".join(a.get("name", "").lower() for a in aacts)
    if "video" not in have:
        aacts.append({"type": "label", "name": "Videozusammenfassung",
                      "intro": "<p>🎬 Kurze Videozusammenfassung der "
                               "wichtigsten Punkte (NotebookLM).</p>"})
    if "entstehung" not in have:
        try:
            from build_mbz import ATTRIBUTION_SENTENCE as _attr
        except ImportError:
            _attr = ("Dieser Kurs ist mit Hilfe von Künstlicher Intelligenz "
                     "und in Kooperation mit dem Labor Didaktik der Technik "
                     "der Hochschule Osnabrück entstanden.")
        aacts.append({"type": "label", "name": "Hinweis zur Entstehung",
                      "intro": (f"<p style=\"font-size:12px;color:#5f6672;\">"
                                f"<i>{_attr}</i></p>")})
    sections.append(abschluss)

    # ---- Gradebook: Kategorien (Gewichte via Golden-Template-Syntax) ------- #
    out["gradebook"] = {"categories": [dict(c) for c in checked["cats"]]}
    out["sections"] = sections
    return out, modmap


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Diagnose-Modul-Spec -> course.json + modmap expandieren.")
    ap.add_argument("modular_json")
    ap.add_argument("-o", "--output", required=True,
                    help="Ziel-course.json (Modmap: <output>.modmap.json)")
    args = ap.parse_args()

    spec = json.load(open(args.modular_json, encoding="utf-8"))
    course, modmap = expand(spec)
    json.dump(course, open(args.output, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    mm_path = os.path.splitext(args.output)[0] + ".modmap.json"
    json.dump(modmap, open(mm_path, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"Expandiert: {len(modmap['modules'])} Module -> "
          f"{len(course['sections'])} Sections, {len(course.get('groups', []))} "
          f"Gruppen, Layer: {', '.join(modmap['active_layers']) or '—'}. "
          f"Kurs: {args.output}  Modmap: {mm_path}")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    main()
