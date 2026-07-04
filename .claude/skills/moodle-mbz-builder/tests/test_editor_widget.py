import json, re
from build_editor_widget import build_widget, MAX_WIDGET_CHARS


def extract_embedded(html_out):
    m = re.search(r'<script type="application/json" id="course-data">(.*?)</script>',
                  html_out, re.S)
    assert m, "eingebettetes Kurs-JSON fehlt"
    return json.loads(m.group(1).replace("<\\/", "</"))


def test_roundtrip_embedded_json_equals_spec(spec):
    out = build_widget(spec)
    embedded = extract_embedded(out)

    def strip(o):
        if isinstance(o, dict):
            return {k: strip(v) for k, v in o.items() if not k.startswith("_")}
        if isinstance(o, list):
            return [strip(v) for v in o]
        return o

    assert strip(embedded) == spec


def test_widget_has_no_doctype_and_no_cdn(spec):
    out = build_widget(spec)
    low = out.lower()
    assert "<!doctype" not in low and "<html" not in low and "<head>" not in low
    # keine externen Ressourcen-Loads (Kurs-Daten duerfen URLs enthalten)
    assert "<link" not in low and "<script src" not in low and "@import" not in low


def test_idempotent(spec):
    assert build_widget(spec) == build_widget(spec)


def test_structure_ops_present(spec):
    out = build_widget(spec)
    for marker in ["function render()", "function addSection()", "moveSection(",
                   "delSection(", "moveAct(", "delAct(", "addActivity(",
                   "data-si", "data-ai", "renderEditor("]:
        assert marker in out, f"fehlt: {marker}"


def test_all_supported_types_in_add_menu(spec):
    out = build_widget(spec)
    for t in ["label", "page", "url", "resource", "folder", "book", "assign",
              "forum", "glossary", "choice", "feedback", "quiz"]:
        assert f'"{t}"' in out


def test_size_fallback_disables_inline_images(spec):
    big = json.loads(json.dumps(spec))
    filler = {"type": "page", "name": "F", "content": "<p>" + "x" * 4000 + "</p>"}
    big["sections"].append({"name": "Bulk", "activities": [dict(filler) for _ in range(120)]})
    out = build_widget(big)
    assert len(out) <= MAX_WIDGET_CHARS or "_inline_images" not in out
