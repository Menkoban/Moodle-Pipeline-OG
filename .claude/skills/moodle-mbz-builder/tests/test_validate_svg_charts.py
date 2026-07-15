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
