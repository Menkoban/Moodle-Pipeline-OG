import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from validate_svg import lint_file


def _write(tmp_path, body, zeichnung=False):
    marker = ' data-diagram-type="zeichnung"' if zeichnung else ""
    p = tmp_path / "t.svg"
    p.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" '
        'font-family="Helvetica"' + marker + ">" + body + "</svg>",
        encoding="utf-8")
    return str(p)


def test_zeichnung_without_dimensions_is_flagged(tmp_path):
    # Markierte Zeichnung mit nur EINER reinen Maßzahl ("20"); die übrigen
    # Labels sind beschreibend (Ø-Stichwort, Bauteilname) -> unbemaßt.
    p = _write(tmp_path,
               '<text x="60" y="60" font-size="13">20</text>'
               '<text x="60" y="100" font-size="13">Ø 5 mm (2 Bohrungen)</text>'
               '<text x="60" y="140" font-size="13">Grundplatte</text>',
               zeichnung=True)
    errors, warns = lint_file(p)
    assert any("BEMASSUNG" in w for w in warns), warns


def test_zeichnung_with_dimensions_is_clean(tmp_path):
    # Vier reine Maßzahlen (Lage + Größe) -> bemaßt, keine Warnung.
    p = _write(tmp_path,
               '<text x="60" y="60" font-size="13">20</text>'
               '<text x="60" y="100" font-size="13">55</text>'
               '<text x="60" y="140" font-size="13">80</text>'
               '<text x="60" y="180" font-size="13">100</text>',
               zeichnung=True)
    errors, warns = lint_file(p)
    assert not any("BEMASSUNG" in w for w in warns), warns


def test_unmarked_svg_without_dimensions_is_not_flagged(tmp_path):
    # Ohne data-diagram-type="zeichnung" läuft der Check gar nicht -> auch
    # ganz ohne Maßzahlen keine BEMASSUNG-Warnung.
    p = _write(tmp_path,
               '<text x="60" y="60" font-size="13">Skizze</text>'
               '<rect x="40" y="80" width="200" height="120" '
               'fill="none" stroke="#000"/>',
               zeichnung=False)
    errors, warns = lint_file(p)
    assert not any("BEMASSUNG" in w for w in warns), warns


def test_zeichnung_exactly_three_dimensions_with_unit_is_clean(tmp_path):
    # Genau MIN_MASSZAHLEN=3 Maßzahlen, eine davon mit Einheit ("8 mm") ->
    # Schwellwert erreicht, keine Warnung (prüft Grenzfall + Einheit-Variante).
    p = _write(tmp_path,
               '<text x="60" y="60" font-size="13">20</text>'
               '<text x="60" y="100" font-size="13">55</text>'
               '<text x="60" y="140" font-size="13">8 mm</text>',
               zeichnung=True)
    errors, warns = lint_file(p)
    assert not any("BEMASSUNG" in w for w in warns), warns
