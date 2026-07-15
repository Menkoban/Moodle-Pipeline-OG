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


def test_readable_text_unescapes_and_strips():
    raw = "&lt;p&gt;&lt;b&gt;Ergebnis:&lt;/b&gt; U = 5 V; R = 150&lt;/p&gt;"
    txt = _readable_text(raw)
    assert "R = 150" in txt and "<" not in txt
    assert any("150" in s for s in _calc_unit_warnings(txt))
