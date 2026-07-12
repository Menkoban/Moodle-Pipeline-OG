import json, os, sys
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

@pytest.fixture
def spec():
    p = os.path.join(os.path.dirname(__file__), "..", "assets", "example_course.json")
    return json.load(open(p, encoding="utf-8"))
