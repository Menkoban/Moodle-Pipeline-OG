"""Unit-Tests für den Availability-Composer + die B.4-Validierung des
Diagnose-Modul-Modells (build_modular.py, Konzept v3 Teil B).

Pflichtfälle nach B.5.3: alle Sichtbarkeitskombinationen der aktiven Layer.
"""
import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from build_modular import (  # noqa: E402
    LAYER_REGISTRY,
    ModularSpecError,
    compose_element_availability,
    expand,
    normalize_thresholds,
    validate_spec,
)


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
def ctx(active=("language_support", "practice_experience"), layer_config=None):
    return {
        "diag": "diag-m01",
        "conv": "sich-m01",
        "pass": 50.0,
        "levels": ["basic", "standard", "advanced"],
        "windows": {"basic": (None, 50.0), "standard": (50.0, 80.0),
                    "advanced": (80.0, None)},
        "groups": {"language_support": "GRP-SPRACHE",
                   "practice_experience": "GRP-PRAXIS",
                   "anschlussorientierung": "GRP-ANSCHLUSS",
                   "verkuerzer": "GRP-VERKUERZER",
                   "umschueler": "GRP-UMSCHUELER",
                   "pruefungsnaehe": "GRP-PRUEFUNG"},
        "active": list(active),
        "layer_config": layer_config or {},
    }


def leaves(tree):
    out = []
    for c in tree.get("c", []):
        if "op" in c:
            out.extend(leaves(c))
        else:
            out.append(c)
    return out


def depth(tree, d=1):
    kids = [c for c in tree.get("c", []) if "op" in c]
    return max([d] + [depth(k, d + 1) for k in kids])


# --------------------------------------------------------------------------- #
# Schwellen-Normalisierung
# --------------------------------------------------------------------------- #
def test_thresholds_normalized_to_hard_edges():
    """B.2-Format (0-49.99 / 50-79.99 / 80-100) -> lückenlose harte Kanten."""
    win = normalize_thresholds([
        {"level": "basic", "min": 0.0, "max": 49.99},
        {"level": "standard", "min": 50.0, "max": 79.99},
        {"level": "advanced", "min": 80.0, "max": 100.0},
    ])
    assert win == {"basic": (None, 50.0), "standard": (50.0, 80.0),
                   "advanced": (80.0, None)}


def test_thresholds_gap_rejected():
    with pytest.raises(ModularSpecError, match="lückenlos"):
        normalize_thresholds([
            {"level": "basic", "min": 0, "max": 40},
            {"level": "standard", "min": 60, "max": 100},
        ])


def test_thresholds_overlap_rejected():
    with pytest.raises(ModularSpecError, match="disjunkt"):
        normalize_thresholds([
            {"level": "basic", "min": 0, "max": 60},
            {"level": "standard", "min": 50, "max": 100},
        ])


# --------------------------------------------------------------------------- #
# Composer: Kern-Kombinationen (B.3)
# --------------------------------------------------------------------------- #
def test_no_visibility_no_availability():
    assert compose_element_availability({}, ctx()) is None


def test_level_only_has_gate_and_window():
    av = compose_element_availability({"level": ["basic"]}, ctx())
    assert av["op"] == "&"
    ls = leaves(av)
    # (a) Diagnose-Gate zuerst, (b) Fenster
    assert ls[0] == {"type": "completion", "cmref": "diag-m01", "e": 1}
    assert ls[1] == {"type": "grade", "ref": "diag-m01", "max": 50.0}
    assert len(ls) == 2


def test_level_advanced_open_ended():
    av = compose_element_availability({"level": ["advanced"]}, ctx())
    assert leaves(av)[1] == {"type": "grade", "ref": "diag-m01", "min": 80.0}


def test_contiguous_levels_merge_to_one_window():
    """basic+standard = [0,80) -> EIN grade-Blatt statt OR-Teilbaum."""
    av = compose_element_availability({"level": ["basic", "standard"]}, ctx())
    ls = leaves(av)
    assert len(ls) == 2
    assert ls[1] == {"type": "grade", "ref": "diag-m01", "max": 80.0}


def test_noncontiguous_levels_become_or_subtree():
    av = compose_element_availability({"level": ["basic", "advanced"]}, ctx())
    subtrees = [c for c in av["c"] if "op" in c]
    assert len(subtrees) == 1 and subtrees[0]["op"] == "|"
    assert depth(av) == 2


def test_language_support_group_condition():
    av = compose_element_availability({"language_support": True}, ctx())
    assert leaves(av) == [{"type": "group", "groupref": "GRP-SPRACHE"}]


def test_practice_with_and_without():
    with_av = compose_element_availability({"practice_experience": "with"}, ctx())
    assert leaves(with_av) == [{"type": "group", "groupref": "GRP-PRAXIS"}]
    wo_av = compose_element_availability({"practice_experience": "without"}, ctx())
    neg = [c for c in wo_av["c"] if "op" in c][0]
    assert neg["op"] == "!|"
    assert neg["c"] == [{"type": "group", "groupref": "GRP-PRAXIS"}]


def test_level_plus_language_order():
    """B.3.1: Reihenfolge (a) Gate, (b) Niveau, (c) Sprache."""
    av = compose_element_availability(
        {"level": ["standard"], "language_support": True}, ctx())
    ls = leaves(av)
    assert [c.get("type") for c in ls] == ["completion", "grade", "group"]
    assert ls[2]["groupref"] == "GRP-SPRACHE"


def test_leaf_cap_exceeded_aborts():
    """B.3.10: > 3 Blätter -> Konflikt melden statt still kürzen."""
    with pytest.raises(ModularSpecError, match="Blattbedingungen"):
        compose_element_availability(
            {"level": ["basic", "advanced"], "language_support": True,
             "practice_experience": "with"}, ctx())


def test_inactive_layer_key_rejected():
    with pytest.raises(ModularSpecError, match="active_layers"):
        compose_element_availability(
            {"anschlussorientierung": True},
            ctx(active=("language_support",)))


def test_unknown_visibility_key_rejected():
    with pytest.raises(ModularSpecError, match="unbekannt"):
        compose_element_availability({"lernstil": "visuell"}, ctx())


# --------------------------------------------------------------------------- #
# Optionale Overlays (Teil C.3, Registry)
# --------------------------------------------------------------------------- #
def test_registry_has_all_layers():
    assert set(LAYER_REGISTRY) == {
        "language_support", "practice_experience", "pruefungsnaehe",
        "wiederholer", "anschlussorientierung", "verkuerzer", "umschueler"}


def test_pruefungsnaehe_date_source():
    c = ctx(active=("pruefungsnaehe",),
            layer_config={"pruefungsnaehe": {"quelle": "datum",
                                             "ab": "2026-04-01"}})
    av = compose_element_availability({"pruefungsnaehe": True}, c)
    (leaf,) = leaves(av)
    assert leaf["type"] == "date" and leaf["d"] == ">=" and leaf["t"] > 0


def test_pruefungsnaehe_group_source_default():
    c = ctx(active=("pruefungsnaehe",))
    av = compose_element_availability({"pruefungsnaehe": True}, c)
    assert leaves(av) == [{"type": "group", "groupref": "GRP-PRUEFUNG"}]


def test_wiederholer_grade_on_convergence():
    c = ctx(active=("wiederholer",))
    av = compose_element_availability({"wiederholer": True}, c)
    assert leaves(av) == [{"type": "grade", "ref": "sich-m01", "max": 50.0}]


def test_verkuerzer_tristate():
    c = ctx(active=("verkuerzer",))
    wo = compose_element_availability({"verkuerzer": "without"}, c)
    assert [n["op"] for n in wo["c"] if "op" in n] == ["!|"]


# --------------------------------------------------------------------------- #
# B.4-Spec-Validierung + expand()
# --------------------------------------------------------------------------- #
def minimal_spec():
    q = [{"name": "F1", "text": "1+1?", "type": "multichoice",
          "answers": [{"text": "2", "fraction": 100},
                      {"text": "3", "fraction": 0}]}]
    def elems(mid):
        return [
            {"id": f"{mid}-E01", "type": "page", "role": "advance_organizer",
             "name": "Überblick", "content": "<p>…</p>", "visibility": {}},
            {"id": f"{mid}-E02", "type": "page", "role": "erarbeitung",
             "name": "Grundpfad", "content": "<p>…</p>",
             "visibility": {"level": ["basic"]}},
            {"id": f"{mid}-E03", "type": "page", "role": "erarbeitung",
             "name": "Standardpfad", "content": "<p>…</p>",
             "visibility": {"level": ["standard"]}},
            {"id": f"{mid}-E04", "type": "page", "role": "erarbeitung",
             "name": "Erweitert", "content": "<p>…</p>",
             "visibility": {"level": ["advanced"]}},
            {"id": f"{mid}-E05", "type": "page", "role": "sprachhilfe",
             "name": "Fachbegriffe einfach", "content": "<p>…</p>",
             "visibility": {"language_support": True}},
        ]
    def module(mid, titel):
        return {"id": mid, "titel": titel,
                "diagnostic": {"name": f"Diagnose {mid}", "questions": q},
                "elements": elems(mid),
                "convergence": {"name": f"Sicherung {mid}", "questions": q,
                                "pass": 50.0},
                "remediation": {"name": "Nochmal anders",
                                "activities": [{"type": "label",
                                                "name": "Hilfe",
                                                "intro": "<p>…</p>"}]}}
    return {
        "course": {"fullname": "Testkurs", "shortname": "modtest",
                   "format": "tiles"},
        "adaptive": {
            "modell": "diagnose",
            "occupation": "Elektroniker/-in für Betriebstechnik",
            "active_layers": ["language_support", "practice_experience"],
            "modules": [module("M01", "Motorschutz"),
                        module("M02", "Steuerung")],
        },
    }


def test_expand_produces_sections_and_modmap():
    course, modmap = expand(minimal_spec())
    names = [s["name"] for s in course["sections"]]
    assert any("Motorschutz" in n for n in names)
    assert len(modmap["modules"]) == 2
    m1 = modmap["modules"][0]
    assert m1["diag"] == "diag-m01" and m1["conv"] == "sich-m01"
    # Gruppen aus aktiven Layern abgeleitet
    assert {g["id"] for g in course["groups"]} == {"GRP-SPRACHE", "GRP-PRAXIS"}
    # Bewertungskategorien: Einstufung Gewicht 0, Leistung 1
    cats = {c["id"]: c["weight"] for c in course["gradebook"]["categories"]}
    assert cats == {"einstufung": 0.0, "leistung": 1.0}


def test_expand_convergence_or_gate():
    course, modmap = expand(minimal_spec())
    conv = next(a for s in course["sections"] for a in s["activities"]
                if a.get("idnumber") == "sich-m01")
    av = conv["availability"]
    assert av["op"] == "|"
    refs = [c["cmref"] for c in av["c"]]
    assert refs == ["m01-e02", "m01-e03", "m01-e04"]   # letztes Pflichtelement je Pfad


def test_expand_module2_locked_by_convergence1():
    course, _ = expand(minimal_spec())
    sec2 = next(s for s in course["sections"] if "Steuerung" in s["name"])
    (cond,) = sec2["availability"]["c"]
    assert cond == {"type": "grade", "ref": "sich-m01", "min": 50.0}


def test_expand_diagnostic_gradepass_zero_and_category():
    course, _ = expand(minimal_spec())
    diag = next(a for s in course["sections"] for a in s["activities"]
                if a.get("idnumber") == "diag-m01")
    assert diag["gradepass"] == 0                # Zustand bleibt 1 (complete)
    assert diag["grade_category"] == "einstufung"
    assert diag["completionusegrade"] is True
    conv = next(a for s in course["sections"] for a in s["activities"]
                if a.get("idnumber") == "sich-m01")
    assert conv["grade_category"] == "leistung"


def test_expand_selbsteinschaetzung_choice_generated():
    course, _ = expand(minimal_spec())
    intro = course["sections"][0]
    choices = [a for a in intro["activities"] if a["type"] == "choice"]
    assert len(choices) == 2                     # eine je aktiver Gruppenschicht


def test_h5p_rejected_with_hint():
    spec = minimal_spec()
    spec["adaptive"]["modules"][0]["elements"].append(
        {"id": "M01-E07", "type": "h5p", "role": "praxis_kompensation",
         "name": "Video", "visibility": {"practice_experience": "without"}})
    with pytest.raises(ModularSpecError, match="h5p.*noch nicht"):
        expand(spec)


def test_missing_level_path_rejected():
    spec = minimal_spec()
    spec["adaptive"]["modules"][0]["elements"] = [
        e for e in spec["adaptive"]["modules"][0]["elements"]
        if e["visibility"].get("level") != ["standard"]]
    with pytest.raises(ModularSpecError, match="erarbeitung.*standard"):
        validate_spec(spec)


def test_language_false_rejected():
    spec = minimal_spec()
    spec["adaptive"]["modules"][0]["elements"][4]["visibility"] = {
        "language_support": False}
    with pytest.raises(ModularSpecError, match="language_support"):
        validate_spec(spec)


def test_einstufung_weight_must_be_zero():
    spec = minimal_spec()
    spec["adaptive"]["grade_categories"] = [
        {"id": "einstufung", "name": "Einstufung", "weight": 0.5},
        {"id": "leistung", "name": "Leistung", "weight": 1.0}]
    with pytest.raises(ModularSpecError, match="Gewicht 0"):
        validate_spec(spec)


def test_praxis_with_without_pairing_warns(capsys):
    spec = minimal_spec()
    spec["adaptive"]["modules"][0]["elements"].append(
        {"id": "M01-E06", "type": "page", "role": "praxis_anknuepfung",
         "name": "Dein Betrieb", "content": "<p>…</p>",
         "visibility": {"practice_experience": "with"}})
    validate_spec(spec)      # Warnung, kein Abbruch (B.4.5)
    assert "Gegenstück" in capsys.readouterr().out
