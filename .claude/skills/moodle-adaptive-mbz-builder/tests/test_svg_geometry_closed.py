import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import svg_geometry as G


def _boxes(body):
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
           + body + "</svg>")
    return G.collect_boxes(G.fromstring(svg))


def test_path_with_z_is_closed():
    boxes = _boxes('<path d="M 10 10 L 90 10 L 90 90 Z" fill="none" stroke="#000"/>')
    paths = [b for b in boxes if b.tag == "path"]
    assert paths and paths[0].extra.get("path_closed") is True


def test_open_path_is_not_closed():
    boxes = _boxes('<path d="M 10 10 L 90 10 L 90 84" fill="none" stroke="#000"/>')
    paths = [b for b in boxes if b.tag == "path"]
    assert paths and paths[0].extra.get("path_closed") is False


def test_polygon_is_closed():
    boxes = _boxes('<polygon points="10,10 90,10 50,90" fill="none" stroke="#000"/>')
    polys = [b for b in boxes if b.tag == "polygon"]
    assert polys and polys[0].extra.get("path_closed") is True


def test_open_polyline_is_not_closed():
    boxes = _boxes('<polyline points="10,10 90,10 90,84" fill="none" stroke="#000"/>')
    pls = [b for b in boxes if b.tag == "polyline"]
    assert pls and pls[0].extra.get("path_closed") is False
