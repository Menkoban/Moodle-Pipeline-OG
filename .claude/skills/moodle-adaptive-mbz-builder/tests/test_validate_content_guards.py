"""Tiefen-Content-Guards von validate_mbz (beratend, nie fatal):

  * GUARD A — Merke-Satz: „Merke"/💡-Kästen sollen vollständige Sätze sein,
    keine Stichwort-/Fragment-Ketten („Schneiden scharf? Schaft sauber?").
  * GUARD B — Rechenbeispiel-Schritte: zwischen „Einsetzen" und „Ergebnis"
    muss mindestens eine Zwischenrechen-Zeile (Ziffern + Operator) stehen.

Beide Heuristiken werden — wie die bestehende EINHEIT-Heuristik — direkt auf
lesbarem Text getestet und dürfen den Goldstandard nicht flaggen.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from validate_mbz import (  # noqa: E402
    _merke_fragment_warnings,
    _rechenbeispiel_step_warnings,
    _readable_text,
)


# --- GUARD A: Merke-Satz vs. Stichwort-/Fragment-Kette --------------------- #

def test_merke_fragment_chain_is_flagged():
    # zwei kurze, verblose „…?"-Segmente hinter dem Doppelpunkt -> Fragment-Kette
    hits = _merke_fragment_warnings(
        "💡 Prüfen Sie: Schneiden scharf? Schaft sauber?")
    assert hits, hits


def test_merke_full_sentence_is_clean():
    # vollständiger Satz -> KEINE Warnung
    assert _merke_fragment_warnings(
        "💡 Merke: Prüfen Sie den Bohrer, bevor Sie ihn einspannen.") == []


def test_merke_word_anchor_full_sentence_is_clean():
    # Anker „Merke" (ohne Emoji), vollständiger Satz -> KEINE Warnung
    assert _merke_fragment_warnings(
        "⚠ Merke: Erst die Lage des Not-Aus einprägen, dann die Maschine "
        "starten.") == []


def test_merke_single_question_not_flagged():
    # nur EINE Frage -> keine Kette
    assert _merke_fragment_warnings("💡 Merke: Ist der Bohrer scharf?") == []


def test_merke_two_questions_with_finite_verb_not_flagged():
    # zwei Fragen, aber mit finitem Verb ("ist") -> vollständige Fragen, kein Flag
    assert _merke_fragment_warnings(
        "💡 Merke: Ist der Bohrer scharf? Ist der Schaft sauber?") == []


def test_merke_without_colon_not_flagged():
    # 💡 vorhanden, aber kein „…:"-Lead -> nichts zu prüfen
    assert _merke_fragment_warnings(
        "💡 Das Berechnen der Drehzahl ist neu für viele.") == []


def test_merke_three_verbless_fragments_flagged():
    hits = _merke_fragment_warnings("💡 Merke: Warum? Weshalb? Wieso?")
    assert hits, hits


# --- GUARD B: Rechenbeispiel — Zwischenrechen-Schritt --------------------- #

def test_rechenbeispiel_direct_jump_is_flagged():
    # „Einsetzen:" springt ohne Zwischenrechnung direkt zum „Ergebnis:"
    hits = _rechenbeispiel_step_warnings(
        "Schritt 4 – Einsetzen: Werte einsetzen. Ergebnis: n = 600 1/min.")
    assert hits, hits


def test_rechenbeispiel_with_intermediate_line_is_clean():
    # Zwischenrechnung „π · 0,008 = 0,0251" zwischen Einsetzen und Ergebnis
    assert _rechenbeispiel_step_warnings(
        "Schritt 3 – Einsetzen: n = π · 0,008 = 0,0251. "
        "Ergebnis: n ≈ 600 1/min.") == []


def test_rechenbeispiel_schema_enumeration_not_flagged():
    # reine Schema-Aufzählung ohne echte Rechnung (kein „:" davor, keine Zahl)
    assert _rechenbeispiel_step_warnings(
        "Ein Rechenbeispiel folgt dem Schema: Gegeben – Gesucht – Formel – "
        "Einsetzen – Ergebnis.") == []


def test_rechenbeispiel_ergebnis_only_not_flagged():
    # „Einsetzen" fehlt -> kein Rechenbeispiel-Kontext
    assert _rechenbeispiel_step_warnings("Nur Ergebnis: n = 600 1/min.") == []


def test_rechenbeispiel_survives_readable_text_pipeline():
    # doppelt-escaptes HTML -> _readable_text -> Guard schlägt trotzdem an
    raw = ("&lt;p&gt;Schritt 4 – Einsetzen: Werte einsetzen. "
           "Ergebnis: n = 600 1/min.&lt;/p&gt;")
    hits = _rechenbeispiel_step_warnings(_readable_text(raw))
    assert hits, hits


def test_rechenbeispiel_full_five_step_calc_is_clean():
    # Auszug aus dem Goldstandard: mehrere Zwischenrechnungen vorhanden
    txt = ("Schritt 3 – Einsetzen und teilen: n = 15 m/min ÷ 0,0251 m ≈ 597 "
           "1/min. Schritt 4 – Einheiten prüfen: m/min ÷ m = 1/min. "
           "✓ Ergebnis: n ≈ 597 1/min ≈ 600 1/min")
    assert _rechenbeispiel_step_warnings(txt) == []


# --- Regressionsschutz: Goldstandard bleibt sauber ------------------------ #

def _walk_strings(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _walk_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_strings(v)
    elif isinstance(obj, str):
        yield obj


def test_goldstandard_fewshot_stays_clean():
    """assets/fewshot_bohrmaschine.json hat vollständige Merksätze und ein
    5-Schritt-Rechenbeispiel mit Zwischenrechnungen — KEINE der beiden Guards
    darf dort anschlagen (über ALLE Strings geprüft, der strengste Fall)."""
    p = os.path.join(os.path.dirname(__file__), "..", "assets",
                     "fewshot_bohrmaschine.json")
    if not os.path.exists(p):
        return  # Asset optional; Test bleibt robust, falls es fehlt/umbenannt wird
    spec = json.load(open(p, encoding="utf-8"))
    merke_hits, rechen_hits = [], []
    for s in _walk_strings(spec):
        txt = _readable_text(s)
        merke_hits += _merke_fragment_warnings(txt)
        rechen_hits += _rechenbeispiel_step_warnings(txt)
    assert merke_hits == [], merke_hits
    assert rechen_hits == [], rechen_hits
