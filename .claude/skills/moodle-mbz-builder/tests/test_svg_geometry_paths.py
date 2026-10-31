from svg_geometry import _path_coords


def test_arc_flags_and_radii_are_not_coordinates():
    xs, ys = _path_coords("M 720 115 A 62 62 0 0 1 725 175")
    # kein Phantom-Punkt aus Radien/Flags (frueher: y=725 aus "1 725")
    assert max(ys) <= 180 and min(ys) >= 110
    # Bogen-Bauch rechts wird real vermessen (endet nicht am Endpunkt-x)
    assert 725 <= max(xs) <= 740 and min(xs) >= 700


def test_h_and_v_commands():
    xs, ys = _path_coords("M 10 20 H 300 V 400")
    assert max(xs) == 300 and max(ys) == 400


def test_quadratic_pairs():
    xs, ys = _path_coords("M 245 118 Q 190 92 135 116")
    # Kurve wird gesampelt: Scheitel liegt ZWISCHEN Endpunkt und Kontrollpunkt
    # (Kontrollpunkt 92 liegt nicht auf der Kurve)
    assert 100 <= min(ys) <= 110 and min(xs) == 135 and max(xs) == 245
