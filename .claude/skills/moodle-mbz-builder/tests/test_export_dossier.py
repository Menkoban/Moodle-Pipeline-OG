from export_course_dossier import build_dossier

SPEC = {"course": {"fullname": "Demo"}, "sections": [
    {"name": "Einführung", "activities": [
        {"type": "page", "name": "Handlungssituation", "content": "<p>Der <b>Auftrag</b> kommt rein.</p>"},
        {"type": "quiz", "name": "Selbsttest", "questions": [
            {"type": "multichoice", "questiontext": "<p>Was gilt?</p>",
             "generalfeedback": "GEHEIM-FEEDBACK",
             "answers": [{"text": "GEHEIME-ANTWORT-A", "correct": True, "feedback": "GEHEIM"}]}]},
        {"type": "url", "name": "Externer Link", "externalurl": "https://x"},
        {"type": "glossary", "name": "Glossar", "entries": [{"concept": "Ohm", "definition": "<p>Einheit</p>"}]}]},
    {"name": "Lehrkräfte", "visible": 0, "activities": [
        {"type": "page", "name": "Leitfaden", "content": "<p>NUR-LEHRKRAFT</p>"}]}]}


def test_includes_content_and_glossary():
    d = build_dossier(SPEC)
    assert "Der Auftrag kommt rein." in d and "Ohm" in d and "Einheit" in d


def test_excludes_solutions_and_hidden():
    d = build_dossier(SPEC)
    for banned in ["GEHEIME-ANTWORT-A", "GEHEIM-FEEDBACK", "NUR-LEHRKRAFT", "https://x"]:
        assert banned not in d


def test_question_text_included_without_answers():
    d = build_dossier(SPEC)
    assert "Was gilt?" in d


def test_markdown_headings():
    d = build_dossier(SPEC)
    assert "# Demo" in d and "## Einführung" in d and "### Handlungssituation" in d
