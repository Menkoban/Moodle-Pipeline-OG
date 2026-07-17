import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from build_mbz import _section_images, _section_image_warnings


# --- Alias-Auflösung: images / image / tilephoto ------------------------------

def test_section_images_list():
    assert _section_images({"images": ["a.svg", "b.svg"]}) == ["a.svg", "b.svg"]


def test_section_images_single():
    assert _section_images({"image": "b.svg"}) == ["b.svg"]


def test_section_images_tilephoto_alias():
    # tilephoto darf NICHT mehr still verpuffen -> als Bildquelle gelesen
    assert _section_images({"tilephoto": "c.svg"}) == ["c.svg"]


def test_section_images_none():
    assert _section_images({}) == []


# --- Guard: Kachelfoto verpufft (tilephoto ohne tiles-Format) ------------------

def test_warn_tilephoto_without_tiles_format():
    spec = {"course": {"format": "topics"},
            "sections": [{"name": "K1", "tilephoto": "assets/x.svg"}]}
    warns = _section_image_warnings(spec)
    assert any("tilephoto" in w and "tiles" in w for w in warns), warns


def test_no_warn_tilephoto_with_tiles_format():
    spec = {"course": {"format": "tiles"},
            "sections": [{"name": "K1", "tilephoto": "assets/x.svg"}]}
    assert _section_image_warnings(spec) == []


def test_warn_tiles_format_without_any_photo():
    spec = {"course": {"format": "tiles"},
            "sections": [{"name": "K1"}, {"name": "K2"}]}
    warns = _section_image_warnings(spec)
    assert any("ohne" in w.lower() or "keine" in w.lower() for w in warns), warns


def test_no_warn_plain_topics_without_tilephoto():
    spec = {"course": {"format": "topics"},
            "sections": [{"name": "K1", "image": "assets/x.svg"}]}
    assert _section_image_warnings(spec) == []
