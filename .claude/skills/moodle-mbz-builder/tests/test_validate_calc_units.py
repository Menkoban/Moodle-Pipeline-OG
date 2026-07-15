import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from validate_mbz import _calc_unit_warnings, _readable_text


def test_result_with_unit_is_clean():
    assert _calc_unit_warnings("R = 3 V / 0,02 A = 150 Ω") == []


def test_result_without_unit_in_calc_context_is_flagged():
    hits = _calc_unit_warnings("U = 5 V; R = 150")
    assert any("150" in s for s in hits), hits


def test_non_calc_context_not_flagged():
    # no unit token anywhere -> not a calculation, don't flag a bare count
    assert _calc_unit_warnings("Anzahl der Bauteile = 150") == []


def test_plain_prose_not_flagged():
    assert _calc_unit_warnings("Der Motor dreht sich schnell und gleichmaessig.") == []


def test_dimensionless_efficiency_not_flagged():
    # efficiency η is unitless; must not be flagged even next to a unit'd result
    assert _calc_unit_warnings("P = 100 W; η = 0,85") == []


def test_spelled_out_unit_is_clean():
    # unit written as a word ("Ohm"), not the symbol Ω, must count as a unit
    assert _calc_unit_warnings("Rges = 600 Ohm; I = 0,04 A") == []


def test_formula_numerator_not_flagged():
    # "f = 1 / T": the 1 is a formula term (operator follows), not a bare result
    assert _calc_unit_warnings("Frequenz f = 1 / T bei T = 20 ms") == []


def test_rpm_one_per_min_is_clean():
    # "1/min" is a unit; the 60/50/2 are formula terms
    assert _calc_unit_warnings("n = 60 · 50 / 2 = 1500 1/min bei U = 400 V") == []


def test_thousands_separator_with_unit_is_clean():
    # "14 400 N" is one number with a unit, not "14" without one
    assert _calc_unit_warnings("F = 14 400 N; U = 5 V") == []


def test_pole_pair_count_not_flagged():
    # dimensionless quantity (pole pairs p) -> LHS not unit-bearing -> skip
    assert _calc_unit_warnings("Polpaarzahl p = 2 bei f = 50 Hz") == []


def test_neural_weight_not_flagged():
    # NN activation z_h is dimensionless -> LHS not unit-bearing -> skip
    assert _calc_unit_warnings("Neuron z_h = 0,4 bei t = 5 ms") == []


def test_readable_text_unescapes_and_strips():
    raw = "&lt;p&gt;&lt;b&gt;Ergebnis:&lt;/b&gt; U = 5 V; R = 150&lt;/p&gt;"
    txt = _readable_text(raw)
    assert "R = 150" in txt and "<" not in txt
    assert any("150" in s for s in _calc_unit_warnings(txt))
