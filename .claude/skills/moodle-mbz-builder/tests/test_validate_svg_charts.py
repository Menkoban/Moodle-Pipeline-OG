import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from validate_svg import lint_file


def _write(tmp_path, body, chart=False):
    marker = ' data-diagram-type="chart"' if chart else ""
    p = tmp_path / "t.svg"
    p.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" '
        'font-family="Helvetica"' + marker + ">" + body + "</svg>",
        encoding="utf-8")
    return str(p)


# ---- V4a: unclosed figures -------------------------------------------------

def test_open_box_path_is_flagged(tmp_path):
    # Rectangle drawn as an open path with a ~6px gap back to the start.
    p = _write(tmp_path,
               '<path d="M 40 40 L 200 40 L 200 200 L 40 200 L 40 46" '
               'fill="none" stroke="#000"/>')
    errors, warns = lint_file(p)
    assert any("FIGUR" in w for w in warns), warns


def test_closed_box_path_is_clean(tmp_path):
    p = _write(tmp_path,
               '<path d="M 40 40 L 200 40 L 200 200 L 40 200 Z" '
               'fill="none" stroke="#000"/>')
    errors, warns = lint_file(p)
    assert not any("FIGUR" in w for w in warns), warns


def test_open_function_graph_is_not_flagged(tmp_path):
    # A plotted curve: endpoints far apart -> not an unclosed figure.
    p = _write(tmp_path,
               '<polyline points="40,200 100,120 160,150 220,80 300,110" '
               'fill="none" stroke="#000"/>')
    errors, warns = lint_file(p)
    assert not any("FIGUR" in w for w in warns), warns


# ---- shared chart fixtures for V1/V3 ---------------------------------------

# A well-formed marked chart: L-shaped axes (path), x/y scale numbers, x/y titles.
_GOOD_CHART = (
    '<path d="M 60 20 L 60 260 L 380 260" fill="none" stroke="#000"/>'
    '<text x="60" y="275" font-size="12">0</text>'
    '<text x="200" y="275" font-size="12">5</text>'
    '<text x="340" y="275" font-size="12">10</text>'
    '<text x="45" y="262" font-size="12" text-anchor="end">0</text>'
    '<text x="45" y="140" font-size="12" text-anchor="end">50</text>'
    '<text x="45" y="34" font-size="12" text-anchor="end">100</text>'
    '<text x="210" y="292" font-size="12">t in s</text>'
    '<text x="16" y="16" font-size="12">U in V</text>'
)


def test_good_chart_is_clean(tmp_path):
    p = _write(tmp_path, _GOOD_CHART, chart=True)
    errors, warns = lint_file(p)
    assert not any(w.startswith(("ACHSE", "SKALA")) for w in warns), warns


def test_chart_missing_x_title_flags_achse(tmp_path):
    body = _GOOD_CHART.replace(
        '<text x="210" y="292" font-size="12">t in s</text>', "")
    p = _write(tmp_path, body, chart=True)
    errors, warns = lint_file(p)
    assert any(w.startswith("ACHSE") and "x-Achse" in w for w in warns), warns
    assert not any(w.startswith("ACHSE") and "y-Achse" in w for w in warns), warns


def test_unmarked_chartlike_svg_has_no_axis_warnings(tmp_path):
    # Same drawing WITHOUT the marker and without titles: must not trip V1/V3.
    body = (
        '<path d="M 60 20 L 60 260 L 380 260" fill="none" stroke="#000"/>'
        '<text x="60" y="275" font-size="12">0</text>'
        '<text x="200" y="275" font-size="12">5</text>'
    )
    p = _write(tmp_path, body, chart=False)
    errors, warns = lint_file(p)
    assert not any(w.startswith(("ACHSE", "SKALA")) for w in warns), warns
