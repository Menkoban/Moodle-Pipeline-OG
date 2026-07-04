from svg_geometry import _path_coords


def test_arc_flags_and_radii_are_not_coordinates():
    xs, ys = _path_coords("M 720 115 A 62 62 0 0 1 725 175")
    assert max(ys) == 175 and max(xs) == 725
    assert 62 not in xs and 1 not in ys


def test_h_and_v_commands():
    xs, ys = _path_coords("M 10 20 H 300 V 400")
    assert max(xs) == 300 and max(ys) == 400


def test_quadratic_pairs():
    xs, ys = _path_coords("M 245 118 Q 190 92 135 116")
    assert min(ys) == 92 and min(xs) == 135
