import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from didactic_profiles import (
    DEFAULT_PROFILE_KEY,
    PROFILES,
    get_profile,
    list_profiles,
    section_titles,
)

# Die dokumentierte Pflicht-Sequenz der Lernabschnitte
# (references/course-design.md §3 / SKILL.md Schritt 3).
RODE_PFLICHT_SEQUENZ = [
    "Einführung",
    "Grundlagen",
    "Vertiefung",
    "Anwendung / Handlungsprodukt",
    "Kurs-Recap",
    "Glossar",
    "Material für Lehrkräfte",
]


def test_registry_loads():
    assert isinstance(PROFILES, dict) and PROFILES
    assert DEFAULT_PROFILE_KEY in PROFILES
    # jedes Profil trägt die Pflicht-Felder
    for prof in PROFILES.values():
        assert prof["key"] and prof["name"]
        assert isinstance(prof["section_sequence"], list) and prof["section_sequence"]
        assert isinstance(prof["rules"], dict)


def test_default_is_rode():
    assert DEFAULT_PROFILE_KEY == "rode"
    assert get_profile()["key"] == "rode"
    assert get_profile(None)["key"] == "rode"


def test_rode_sequence_matches_pflichtsequenz():
    assert section_titles("rode") == RODE_PFLICHT_SEQUENZ
    # Pflicht-Abschnitte laut Doku sind eine Teilmenge der Sequenz
    rode = get_profile("rode")
    for name in rode["rules"]["pflicht_abschnitte"]:
        assert name in RODE_PFLICHT_SEQUENZ
    # verborgene Lehrkräfte-Sektion bleibt visible=0
    lehrkraefte = rode["section_sequence"][-1]
    assert lehrkraefte["title"] == "Material für Lehrkräfte"
    assert lehrkraefte["visible"] == 0


def test_second_profile_exists_and_differs():
    keys = [k for k, _ in list_profiles()]
    assert len(keys) >= 2
    other = [k for k in keys if k != "rode"][0]
    assert other in PROFILES
    # klar unterscheidbare Sequenz
    assert section_titles(other) != section_titles("rode")


def test_get_profile_unknown_key_raises():
    try:
        get_profile("gibt-es-nicht")
    except ValueError:
        pass
    else:
        assert False, "unbekannter Key sollte ValueError auslösen"


def test_get_profile_returns_copy():
    # Mutation der Rückgabe darf die Registry nicht verändern.
    p = get_profile("rode")
    p["section_sequence"].append({"title": "Hack"})
    assert section_titles("rode") == RODE_PFLICHT_SEQUENZ
