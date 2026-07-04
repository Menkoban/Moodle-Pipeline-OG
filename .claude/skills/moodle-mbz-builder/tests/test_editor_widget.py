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


def test_field_editors_cover_types(spec):
    out = build_widget(spec)
    for marker in ["function renderEditor(", "edPage(", "edQuiz(", "edAssign(",
                   "edGlossary(", "edChoice(", "edBook(", "edFeedback(",
                   "material_bullets", "_inline_images", "overallfeedback"]:
        assert marker in out, f"fehlt: {marker}"


def test_rich_editors_no_raw_html_textareas(spec):
    out = build_widget(spec)
    # HTML-Inhalte werden als contenteditable-Rich-Felder editiert,
    # nicht als Roh-HTML-Textareas
    for marker in ["function rich(", "contenteditable", "bindRich("]:
        assert marker in out, f"fehlt: {marker}"
    assert "ta(a.content" not in out and "ta(q.questiontext" not in out


def test_ai_assist_wiring(spec):
    out = build_widget(spec)
    for marker in ["AI_PRESETS", "renderAiRow(", "'ai_assist'",
                   "Neu schreiben", "Diagramm neu generieren", "Frage ergänzen",
                   "Rubrik generieren", "Begriffe ergänzen", "Eigener KI-Auftrag"]:
        assert marker in out, f"fehlt: {marker}"


def test_envelope_actions_present(spec):
    out = build_widget(spec)
    for a in ["'save'", "'finalize'", "'video_recap'"]:
        assert a in out


def test_wysiwyg_preview_combination(spec):
    out = build_widget(spec)
    # Vorschau-Optik + WYSIWYG: Diagramme inline im editierbaren Inhalt,
    # beim Serialisieren zurueck zu @@PLUGINFILE@@-img
    for marker in ["function inlineImgs(", "function serializeRich(",
                   "svgwrap", "data-pf", "@@PLUGINFILE@@", "ed-meta"]:
        assert marker in out, f"fehlt: {marker}"
    # separate Diagramm-Anzeige unter dem Inhalt ist ersetzt
    assert "Änderung via KI-Auftrag" not in out


def test_size_fallback_disables_inline_images(spec):
    big = json.loads(json.dumps(spec))
    filler = {"type": "page", "name": "F", "content": "<p>" + "x" * 4000 + "</p>"}
    big["sections"].append({"name": "Bulk", "activities": [dict(filler) for _ in range(120)]})
    out = build_widget(big)
    embedded = json.dumps(extract_embedded(out))
    assert len(out) <= MAX_WIDGET_CHARS or "_inline_images" not in embedded
