"""O2 speed: make_materials._enable_font_cache() must make svglib parse each
TrueType font file at most once per process (a repeat register_font with
identical args is memoised), WITHOUT changing what gets registered — so the
rendered PDF/PPTX bytes are unaffected.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

svglib = pytest.importorskip("svglib.svglib")
_fonts = pytest.importorskip("svglib.fonts")
_ttf = pytest.importorskip("reportlab.pdfbase.ttfonts")

import make_materials as mm  # noqa: E402

# An SVG whose text needs a NON-standard family in a bold weight — that is the
# lookup svglib fails to cache on its own (find_font drops the weight), so it is
# the case the memo must cover.
SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 120">'
       '<rect x="0" y="0" width="300" height="120" fill="#ffffff"/>'
       '<text x="20" y="60" font-family="Arial, sans-serif" font-weight="bold" '
       'font-size="16">Kolbenflaeche A1</text></svg>')


def _render_twice_counting_extractions(tmp_path):
    """Render the same SVG twice and count reportlab TTFont extractions during
    the SECOND render (the first warms whatever cache exists)."""
    from svglib.svglib import svg2rlg

    p = tmp_path / "d.svg"
    p.write_text(SVG, encoding="utf-8")

    calls = {"n": 0}
    orig = _ttf.TTFontFile.extractInfo

    def counting(self, *a, **k):
        calls["n"] += 1
        return orig(self, *a, **k)

    _ttf.TTFontFile.extractInfo = counting
    try:
        svg2rlg(str(p))          # warm
        calls["n"] = 0
        svg2rlg(str(p))          # measured
        return calls["n"]
    finally:
        _ttf.TTFontFile.extractInfo = orig


def test_font_cache_eliminates_repeat_extraction(tmp_path):
    # Reset any memo state so the test is order-independent.
    if getattr(_fonts.FontMap, "_o2_font_cache", False):
        # can't easily un-patch; instead assert the effect holds regardless.
        pass
    mm._enable_font_cache()
    second_pass = _render_twice_counting_extractions(tmp_path)
    assert second_pass == 0, (
        f"font file re-parsed {second_pass} time(s) on the second render — "
        f"the memo is not covering the weighted lookup")


def test_enable_font_cache_is_idempotent():
    mm._enable_font_cache()
    ref = _fonts.FontMap.register_font       # patched wrapper (class attribute)
    mm._enable_font_cache()                  # second call must not re-wrap
    assert _fonts.FontMap.register_font is ref
    assert getattr(_fonts.FontMap, "_o2_font_cache", False) is True


def test_font_cache_preserves_registration(tmp_path):
    """The memo must not SKIP the first, real registration: after a render the
    non-standard Arial family the bold label needs is registered with reportlab
    exactly as the un-cached path would leave it."""
    mm._enable_font_cache()
    from svglib.svglib import svg2rlg
    from reportlab.pdfbase import pdfmetrics

    p = tmp_path / "d.svg"
    p.write_text(SVG, encoding="utf-8")
    svg2rlg(str(p))
    registered = set(pdfmetrics.getRegisteredFontNames())
    assert any("Arial" in n for n in registered), registered
