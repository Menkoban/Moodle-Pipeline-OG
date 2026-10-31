import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from validate_mbz import _check_null_in_attributes


def test_null_placeholder_in_attribute_is_problem():
    # $@NULL@$ in einem XML-Attribut -> Moodle schreibt den literalen String
    # in eine int-Spalte -> dmlwriteexception beim Restore (realer Bug 2026-07-12)
    contents = {
        "gradebook.xml": '<grade_settings><grade_setting id="$@NULL@$">'
                         "<name>x</name></grade_setting></grade_settings>",
    }
    problems = []
    _check_null_in_attributes(contents, problems)
    assert len(problems) == 1
    assert "grade_setting" in problems[0]
    assert "id" in problems[0]
    assert "$@NULL@$" in problems[0]


def test_null_placeholder_in_element_text_is_ok():
    # In Element-TEXTEN ist der Platzhalter legitim (Moodle dekodiert ihn dort)
    contents = {
        "users.xml": "<user><mnethosturl>$@NULL@$</mnethosturl></user>",
    }
    problems = []
    _check_null_in_attributes(contents, problems)
    assert problems == []


def test_clean_attributes_are_ok():
    contents = {
        "gradebook.xml": '<grade_setting id=""><name>x</name></grade_setting>'
                         '<grade_setting id="5"><name>y</name></grade_setting>',
    }
    problems = []
    _check_null_in_attributes(contents, problems)
    assert problems == []


def test_non_xml_paths_are_skipped():
    contents = {
        "files/ab/notes.txt": 'id="$@NULL@$"',
    }
    problems = []
    _check_null_in_attributes(contents, problems)
    assert problems == []
