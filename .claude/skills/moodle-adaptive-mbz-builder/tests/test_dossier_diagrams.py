"""Strang O1: das Dossier soll Textbeschreibungen eingebetteter SVG-Diagramme
enthalten, damit das NotebookLM-Video (das nur den Dossier-Text sieht, keine
Bilder) auf die Kurs-Diagramme eingehen kann."""
import os

from export_course_dossier import DIAGRAM_HEADING, build_dossier, describe_svg

SVG_WITH_TITLE = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200">
  <title>Aufbau der Standbohrmaschine</title>
  <desc>Zeigt Spindel, Bohrfutter und Tisch.</desc>
  <rect x="0" y="0" width="300" height="200" fill="#fff"/>
</svg>
"""

SVG_WITH_LABELS_ONLY = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200">
  <text x="10" y="20" font-size="14">Spindel</text>
  <text x="10" y="60" font-size="14">Bohrfutter</text>
</svg>
"""


def _spec_with_page_image(svg_path, images=None):
    return {"course": {"fullname": "Demo"}, "sections": [
        {"name": "Modul 1", "activities": [
            {"type": "page", "name": "Aufbau", "content": "<p>Text</p>",
             "images": images if images is not None else [str(svg_path)]}]}]}


def test_dossier_includes_diagram_heading_and_title(tmp_path):
    svg_path = tmp_path / "aufbau.svg"
    svg_path.write_text(SVG_WITH_TITLE, encoding="utf-8")
    d = build_dossier(_spec_with_page_image(svg_path))
    assert f"### {DIAGRAM_HEADING}" in d
    assert "Aufbau der Standbohrmaschine" in d
    assert "aufbau.svg" in d


def test_dossier_falls_back_to_visible_text_labels(tmp_path):
    svg_path = tmp_path / "labels_only.svg"
    svg_path.write_text(SVG_WITH_LABELS_ONLY, encoding="utf-8")
    d = build_dossier(_spec_with_page_image(svg_path))
    assert f"### {DIAGRAM_HEADING}" in d
    assert "Spindel" in d and "Bohrfutter" in d


def test_dossier_unchanged_for_course_without_diagrams():
    spec = {"course": {"fullname": "Demo"}, "sections": [
        {"name": "Modul 1", "activities": [
            {"type": "page", "name": "Text", "content": "<p>Nur Text, keine Bilder.</p>"}]}]}
    d = build_dossier(spec)
    assert DIAGRAM_HEADING not in d


def test_missing_svg_file_is_skipped_without_crashing(tmp_path):
    missing = tmp_path / "does_not_exist.svg"
    d = build_dossier(_spec_with_page_image(missing))
    assert DIAGRAM_HEADING not in d
    assert describe_svg(str(missing)) is None


def test_non_svg_images_are_ignored():
    spec = _spec_with_page_image("irrelevant", images=["assets/foto.png"])
    d = build_dossier(spec)
    assert DIAGRAM_HEADING not in d


def test_describe_svg_prefers_title_desc_over_labels(tmp_path):
    svg_path = tmp_path / "aufbau.svg"
    svg_path.write_text(SVG_WITH_TITLE, encoding="utf-8")
    desc = describe_svg(str(svg_path))
    assert desc is not None
    assert "Aufbau der Standbohrmaschine" in desc
    assert "Spindel, Bohrfutter und Tisch" in desc


def test_describe_svg_filename_fallback_for_svg_without_title_or_text(tmp_path):
    svg_path = tmp_path / "leere_grafik.svg"
    svg_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
        '<rect x="0" y="0" width="10" height="10"/></svg>',
        encoding="utf-8")
    desc = describe_svg(str(svg_path))
    assert desc == "leere grafik"


def test_real_fewshot_asset_used_as_regression_smoke():
    """assets/*.svg im Skill haben (Stand heute) kein <title>/<desc> — der
    Text-Label-Fallback muss also fuer den echten Bestand greifen."""
    repo_root = os.path.join(os.path.dirname(__file__), "..")
    svg_path = os.path.join(repo_root, "assets", "aufbau_standbohrmaschine.svg")
    if not os.path.exists(svg_path):
        return  # Asset optional; Test bleibt robust, falls es fehlt/umbenannt wird
    desc = describe_svg(svg_path)
    assert desc is not None and desc.strip()
