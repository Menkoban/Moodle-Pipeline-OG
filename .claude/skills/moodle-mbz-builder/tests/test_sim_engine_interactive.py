"""Tests for the interactive extensions of sim_engine (strand O3):
time animation (`animate` + Play/Pause/Speed/Reset), extended input types
(`select`/`toggle`) and the opt-in `challenge` card. Pure-string assertions on
the self-contained HTML that `render(spec)` returns.

Backward compatibility is the load-bearing property: a spec with only `range`
inputs + `render` (no `animate`/`challenge`) must still render as before — no
Play button, no challenge card — and keep the markers `validate_mbz.py` relies
on (`var SPEC`, `grid-template-columns:300px`).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import sim_engine  # noqa: E402
from sim_engine import render, SIM_LIBRARY  # noqa: E402


# --------------------------------------------------------------------------- #
# minimal specs
# --------------------------------------------------------------------------- #

def _legacy_spec():
    """Old-style spec: only range inputs + render, no animate/challenge."""
    return {
        "title": "Ohm", "subtitle": "x",
        "inputs": [{"id": "u", "label": "U", "unit": "V",
                    "min": 0, "max": 10, "step": 1, "default": 5}],
        "kpis": [{"id": "i", "label": "I", "unit": "A", "dec": 2}],
        "visual": "<svg viewBox='0 0 10 10'></svg>",
        "compute": "return {i:s.u/2};",
        "render": "",
    }


def _animate_spec():
    s = _legacy_spec()
    s["animate"] = "root.setAttribute('data-t', t);"
    return s


def _select_spec():
    return {
        "title": "Sel",
        "inputs": [{"id": "mode", "label": "Betriebsart", "type": "select",
                    "options": [{"value": "a", "label": "A"},
                                {"value": "b", "label": "B"}]}],
        "kpis": [{"id": "x", "label": "X", "dec": 0}],
        "compute": "return {x:1};", "render": "",
    }


def _toggle_spec():
    return {
        "title": "Tog",
        "inputs": [{"id": "sw", "label": "Schalter", "type": "toggle",
                    "on": 1, "off": 0, "default": True,
                    "onLabel": "geschlossen", "offLabel": "offen"}],
        "kpis": [{"id": "x", "label": "X", "dec": 0}],
        "compute": "return {x:s.sw};", "render": "",
    }


def _challenge_spec():
    s = _legacy_spec()
    s["challenge"] = {"prompt": "Stelle U=8 ein", "check": "return s.u===8;",
                      "success": "Super!", "hint": "Noch nicht."}
    return s


# --------------------------------------------------------------------------- #
# (a) time animation
# --------------------------------------------------------------------------- #

def test_animate_renders_play_pause_control():
    h = render(_animate_spec())
    assert 'id="anim_play"' in h
    assert 'id="anim_reset"' in h          # Reset (t=0)


def test_animate_renders_speed_control_slowmo_to_4():
    # Verlangsamung bis 0,1x (Zeitlupe) + Zeitraffer bis 4x, damit schnelle
    # Animationen (z.B. Bohrer-Drehung bei realistischer Drehzahl) lesbar werden.
    h = render(_animate_spec())
    assert 'id="anim_speed"' in h
    assert 'min="0.1"' in h and 'max="4"' in h


def test_animate_exposes_readable_rotation_helper():
    # visDeg(rpm,t): bildet eine reale Drehzahl auf ein ruhiges Sicht-Tempo ab,
    # damit die animate-Bodies rohe U/min NICHT 1:1 als Rotationsspeed nutzen.
    h = render(_animate_spec())
    assert "function visDeg(" in h


def test_legacy_spec_has_no_rotation_helper():
    # Helfer nur bei animate -> Legacy-Form bleibt byte-gleich.
    h = render(_legacy_spec())
    assert "function visDeg(" not in h


def test_animate_uses_requestanimationframe_loop():
    h = render(_animate_spec())
    assert "requestAnimationFrame" in h


def test_animate_starts_paused():
    h = render(_animate_spec())
    assert "playing=false" in h            # default state PAUSED


def test_animate_body_embedded_with_t_signature():
    h = render(_animate_spec())
    assert "animate: function(root, s, o, t)" in h
    assert "root.setAttribute('data-t', t);" in h


# --------------------------------------------------------------------------- #
# (b) extended input types
# --------------------------------------------------------------------------- #

def test_select_input_type_and_options_embedded():
    h = render(_select_spec())
    assert '"type": "select"' in h
    assert '"options"' in h
    assert '<select id="' in h             # engine builds a <select>


def test_toggle_input_type_and_checkbox_control():
    h = render(_toggle_spec())
    assert '"type": "toggle"' in h
    assert 'type="checkbox"' in h          # engine builds a checkbox


def test_state_reads_all_input_types_uniformly():
    # The engine's state() must cover range (+number), select (.value) and
    # toggle (.checked -> on/off value).
    h = render(_toggle_spec())
    assert "elm.checked" in h              # toggle read
    assert "elm.value" in h                # select/range read


# --------------------------------------------------------------------------- #
# (c) opt-in challenge
# --------------------------------------------------------------------------- #

def test_challenge_renders_card_and_pruefen_button():
    h = render(_challenge_spec())
    assert "card challenge" in h           # the challenge card
    assert 'id="ch_check"' in h            # "Prüfen" button
    assert "Prüfen" in h


def test_challenge_check_is_embedded_as_function():
    h = render(_challenge_spec())
    assert "challenge: { prompt:" in h
    assert "check: function(s, o)" in h
    assert "return s.u===8;" in h
    assert "Super!" in h and "Noch nicht." in h


def test_without_challenge_no_card():
    h = render(_legacy_spec())
    assert "card challenge" not in h
    assert 'id="ch_check"' not in h
    assert "challenge: {" not in h


# --------------------------------------------------------------------------- #
# backward compatibility — legacy spec renders unchanged
# --------------------------------------------------------------------------- #

def test_legacy_spec_has_no_animation_controls():
    h = render(_legacy_spec())
    assert 'id="anim_play"' not in h
    assert "requestAnimationFrame" not in h
    assert 'id="anim_speed"' not in h
    assert "animate: function" not in h


def test_legacy_spec_has_no_challenge():
    h = render(_legacy_spec())
    assert "card challenge" not in h
    assert 'id="ch_check"' not in h


def test_legacy_spec_keeps_core_markers_and_controls():
    h = render(_legacy_spec())
    assert "var SPEC" in h                       # validate_mbz sim marker
    assert "grid-template-columns:300px" in h    # compact no-scroll layout
    assert 'type="range"' in h                   # range control still there
    assert "return {i:s.u/2};" in h              # compute body intact


# --------------------------------------------------------------------------- #
# library upgrades
# --------------------------------------------------------------------------- #

def test_reihenschaltung_is_now_animated():
    h = render(SIM_LIBRARY["reihenschaltung"])
    assert 'id="anim_play"' in h
    assert "flowpath" in h                 # current-flow path for moving dots
    assert "flowdot" in h


def test_reihenschaltung_has_switch_toggle():
    h = render(SIM_LIBRARY["reihenschaltung"])
    assert '"type": "toggle"' in h


def test_parallelschaltung_is_now_animated():
    h = render(SIM_LIBRARY["parallelschaltung"])
    assert 'id="anim_play"' in h
    assert "fp1" in h                      # per-branch current-flow paths
    assert 'class="fd1"' in h              # per-branch flow dots


def test_wechselspannung_sim_exists_and_is_time_based():
    assert "wechselspannung" in SIM_LIBRARY
    h = render(SIM_LIBRARY["wechselspannung"])
    assert 'id="anim_play"' in h           # time animation
    assert "animate: function(root, s, o, t)" in h


def test_wechselspannung_has_challenge():
    h = render(SIM_LIBRARY["wechselspannung"])
    assert 'id="ch_check"' in h
    assert "challenge: { prompt:" in h


def test_all_library_sims_keep_compact_grid_and_marker():
    for name, spec in SIM_LIBRARY.items():
        h = render(spec)
        assert "grid-template-columns:300px" in h, name
        assert "var SPEC" in h, name


def test_all_library_sims_render_without_error():
    for name, spec in SIM_LIBRARY.items():
        h = render(spec)
        assert h.startswith("<!doctype html>"), name
        assert "<script>" in h, name
