import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from fraction_render import to_slash, to_css


def test_slash_basic():
    assert to_slash(r"R = \(\frac{U}{I}\) = 6 Ω") == "R = U/I = 6 Ω"


def test_slash_dfrac():
    assert to_slash(r"\(\dfrac{3}{4}\)") == "3/4"


def test_slash_leaves_units():
    assert to_slash("Tempo 90 km/h und 1/min") == "Tempo 90 km/h und 1/min"


def test_slash_two_fractions():
    assert to_slash(r"\(\frac{a}{b}\) und \(\frac{c}{d}\)") == "a/b und c/d"


def test_css_stacks_with_bar():
    out = to_css(r"\(\frac{U}{I}\)")
    assert "border-bottom" in out and ">U</span>" in out and ">I</span>" in out
    assert "frac" not in out


def test_css_leaves_units():
    assert to_css("90 km/h") == "90 km/h"
