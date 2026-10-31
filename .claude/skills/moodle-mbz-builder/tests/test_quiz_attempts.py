import io
import os
import re
import sys
import tarfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from build_mbz import MbzBuilder


def _build_spec(quiz_extra):
    quiz = {
        "type": "quiz",
        "name": "Selbsttest",
        "intro": "<p>Test</p>",
        "questions": [
            {
                "type": "truefalse",
                "name": "Frage 1",
                "questiontext": "<p>Stimmt das?</p>",
                "correct": True,
            }
        ],
    }
    quiz.update(quiz_extra)
    return {
        "filename": "attempts-test.mbz",
        "course": {
            "fullname": "Attempts Testkurs",
            "shortname": "ATT-TEST",
            "format": "topics",
        },
        "sections": [{"name": "Abschnitt 1", "activities": [quiz]}],
    }


def _quiz_xml_from_build(spec):
    data = MbzBuilder(spec, "https://moodle.example.edu").build()
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        for member in tar.getmembers():
            if re.match(r"activities/quiz_\d+/quiz\.xml$", member.name):
                return tar.extractfile(member).read().decode("utf-8")
    raise AssertionError("quiz.xml nicht im Archiv gefunden")


def test_attempts_from_spec():
    # "attempts": 3 am Quiz -> Wiederholungs-Deckel landet im quiz.xml
    xml = _quiz_xml_from_build(_build_spec({"attempts": 3}))
    assert "<attempts_number>3</attempts_number>" in xml


def test_attempts_default_unlimited():
    # ohne attempts-Key bleibt 0 (= unbegrenzt), Bestandskurse unveraendert
    xml = _quiz_xml_from_build(_build_spec({}))
    assert "<attempts_number>0</attempts_number>" in xml
