import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from autofit_svg import fit_svg

SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200" '
       'font-family="Helvetica">'
       '<rect x="0" y="0" width="400" height="200" fill="#ffffff"/>'
       '<text x="20" y="100" font-size="14">Ein Label das etwas breiter ist</text>'
       '<rect x="20" y="120" width="500" height="40" fill="#f5f6f8"/>'
       '</svg>')


def test_autofit_is_idempotent():
    fitted, msg1 = fit_svg(SVG, 10.0)
    assert msg1 is not None  # erster Lauf: Inhalt ragt rechts raus -> Fix
    again, msg2 = fit_svg(fitted, 10.0)
    assert msg2 is None, f"zweiter Lauf muss 'already fits' sein, war: {msg2}"
    assert again == fitted


def test_background_rect_not_counted_as_content():
    # Inhalt passt laengst -> kein Wachstum, obwohl bg-Rect die viewBox fuellt
    small = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="-10 -10 420 220" '
             'font-family="Helvetica">'
             '<rect x="-10" y="-10" width="420" height="220" fill="#ffffff"/>'
             '<text x="20" y="100" font-size="14">Kurz</text>'
             '</svg>')
    _out, msg = fit_svg(small, 10.0)
    assert msg is None, msg
