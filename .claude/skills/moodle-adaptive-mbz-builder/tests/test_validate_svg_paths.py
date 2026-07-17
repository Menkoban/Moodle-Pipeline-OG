import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from validate_svg import lint_file


def _write(tmp_path, body):
    p = tmp_path / "t.svg"
    p.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200" '
        'font-family="Helvetica">' + body + "</svg>", encoding="utf-8")
    return str(p)


def test_curved_path_crossing_text_is_flagged(tmp_path):
    # Q-Kurve laeuft mitten durch das Label (wie der Rotationspfeil W1)
    p = _write(tmp_path,
               '<text x="180" y="105" font-size="13">W1</text>'
               '<path d="M 300 118 Q 200 80 100 116" fill="none" stroke="#000"/>')
    errors, warns = lint_file(p)
    assert any("PATH" in w and "W1" in w for w in warns), warns


def test_arc_path_crossing_text_is_flagged(tmp_path):
    # Bogen von (200,60) nach (200,160), r=60, sweep=1 -> Bauch rechts bis
    # x ~ 227; das Label sitzt mitten im Bauch
    p = _write(tmp_path,
               '<text x="216" y="115" font-size="13">D1</text>'
               '<path d="M 200 60 A 60 60 0 0 1 200 160" fill="none" stroke="#000"/>')
    errors, warns = lint_file(p)
    assert any("PATH" in w and "D1" in w for w in warns), warns


def test_polygon_covering_text_is_flagged(tmp_path):
    p = _write(tmp_path,
               '<text x="100" y="100" font-size="13">B1</text>'
               '<polygon points="95,85 130,85 112,105" fill="#000"/>')
    errors, warns = lint_file(p)
    assert any("SHAPE" in w and "B1" in w for w in warns), warns


def test_leader_path_ending_at_text_is_exempt(tmp_path):
    # Leader-Linie ENDET am Text -> gewollt, kein Fund
    p = _write(tmp_path,
               '<text x="200" y="100" font-size="13">B2</text>'
               '<path d="M 100 140 L 196 102" fill="none" stroke="#000"/>')
    errors, warns = lint_file(p)
    assert not any("PATH" in w for w in warns), warns


def test_clear_path_not_flagged(tmp_path):
    p = _write(tmp_path,
               '<text x="50" y="30" font-size="13">OK</text>'
               '<path d="M 100 150 Q 200 120 300 150" fill="none" stroke="#000"/>')
    errors, warns = lint_file(p)
    assert not any("PATH" in w or "SHAPE" in w for w in warns), warns


def test_curved_arrow_endpoint_near_text_but_belly_crosses_is_flagged(tmp_path):
    # Drehpfeil-Fall (spannen_ankoernen): EIN Endpunkt landet zufaellig am
    # Label, der Bogen schwingt aber quer durch die Schrift. Die fruehere
    # Leader-Ausnahme stellte den GANZEN Pfad frei -> Fehltreffer durchgerutscht.
    p = _write(tmp_path,
               '<text x="150" y="100" font-size="13" text-anchor="middle">Verletzungsgefahr</text>'
               '<path d="M 210 78 Q 150 112 92 88" fill="none" stroke="#d00"/>')
    errors, warns = lint_file(p)
    assert any("PATH" in w and "Verletzungsgefahr" in w for w in warns), warns


def test_filled_path_covering_text_is_flagged(tmp_path):
    # gefuellter <path> (z.B. eine Hand/Blob) liegt ueber der Schrift -
    # der SHAPE-Check pruefte bisher nur polygon/polyline.
    p = _write(tmp_path,
               '<text x="100" y="100" font-size="13">H1</text>'
               '<path d="M 80 86 L 140 86 L 140 110 L 80 110 Z" fill="#e8b98a"/>')
    errors, warns = lint_file(p)
    assert any("SHAPE" in w and "H1" in w for w in warns), warns


def test_label_inside_large_filled_container_is_exempt(tmp_path):
    # Behaelter-Fall (Tank-Symbol im Hydraulik-Kreislauf): ein grosser
    # gefuellter Pfad ENTHAELT sein Label vollstaendig - das ist gewollt
    # (wie Text auf einem Panel-Rect), kein Verdecken durch einen Marker.
    p = _write(tmp_path,
               '<path d="M 40 52 L 40 130 L 160 130 L 160 52" fill="#7fb3d5"/>'
               '<text x="100" y="100" font-size="15" text-anchor="middle">T</text>')
    errors, warns = lint_file(p)
    assert not any("SHAPE" in w for w in warns), warns
