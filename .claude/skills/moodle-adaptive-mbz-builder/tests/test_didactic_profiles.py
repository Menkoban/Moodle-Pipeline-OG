"""Didaktik-Profil-Registry des adaptiven Skills: zdq-adaptiv als Default,
API-kompatibel zum linearen Schwester-Skill (get_profile/list_profiles/
section_titles), Registry unveränderlich."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import didactic_profiles as dp  # noqa: E402


def test_default_is_zdq_adaptiv():
    assert dp.DEFAULT_PROFILE_KEY == "zdq-adaptiv"
    assert dp.list_profiles()[0][0] == "zdq-adaptiv"


def test_profile_has_adaptive_mapping():
    p = dp.get_profile()
    titles = [s["title"] for s in p["section_sequence"]]
    assert any("Niveau-Kachel" in t for t in titles)      # Stufen-Eintrag
    assert any("Kurs-Recap" in t for t in titles)          # Abschluss
    assert any(s.get("parametrisch") for s in p["section_sequence"])
    assert p["intro_section"]["pflicht"] is True           # Intro-Kachel Pflicht


def test_get_profile_returns_copy():
    a = dp.get_profile()
    a["section_sequence"].clear()
    assert dp.get_profile()["section_sequence"]            # Registry unberührt


def test_unknown_key_raises():
    try:
        dp.get_profile("gibt-es-nicht")
    except ValueError as e:
        assert "zdq-adaptiv" in str(e)
    else:
        raise AssertionError("ValueError erwartet")


def test_section_titles_nonempty():
    assert len(dp.section_titles()) >= 3
