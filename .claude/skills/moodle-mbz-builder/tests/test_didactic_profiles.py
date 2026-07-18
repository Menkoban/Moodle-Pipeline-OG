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
    assert DEFAULT_PROFILE_KEY == "zdq"
    assert get_profile()["key"] == "zdq"
    assert get_profile(None)["key"] == "zdq"


def test_rode_sequence_matches_pflichtsequenz():
    assert section_titles("zdq") == RODE_PFLICHT_SEQUENZ
    # Pflicht-Abschnitte laut Doku sind eine Teilmenge der Sequenz
    zdq = get_profile("zdq")
    for name in zdq["rules"]["pflicht_abschnitte"]:
        assert name in RODE_PFLICHT_SEQUENZ
    # verborgene Lehrkräfte-Sektion bleibt visible=0
    lehrkraefte = zdq["section_sequence"][-1]
    assert lehrkraefte["title"] == "Material für Lehrkräfte"
    assert lehrkraefte["visible"] == 0


def test_second_profile_exists_and_differs():
    keys = [k for k, _ in list_profiles()]
    assert len(keys) >= 2
    other = [k for k in keys if k != "zdq"][0]
    assert other in PROFILES
    # klar unterscheidbare Sequenz
    assert section_titles(other) != section_titles("zdq")


def test_get_profile_unknown_key_raises():
    try:
        get_profile("gibt-es-nicht")
    except ValueError:
        pass
    else:
        assert False, "unbekannter Key sollte ValueError auslösen"


def test_get_profile_returns_copy():
    # Mutation der Rückgabe darf die Registry nicht verändern.
    p = get_profile("zdq")
    p["section_sequence"].append({"title": "Hack"})
    assert section_titles("zdq") == RODE_PFLICHT_SEQUENZ


def test_every_profile_has_guidance_ref():
    # Split-Bereitschaft: jedes Profil verweist auf seinen Autoren-Leitfaden,
    # damit es später zu einem eigenständigen Konzept-Skill werden kann.
    for prof in PROFILES.values():
        assert prof.get("guidance_ref"), f"{prof['key']} ohne guidance_ref"


def test_list_profiles_default_first_for_briefing():
    # Das Briefing bietet IMMER eine Auswahl an (auch bei nur einem Profil),
    # Default (zdq) zuerst.
    listed = list_profiles()
    assert listed and listed[0][0] == DEFAULT_PROFILE_KEY
    assert all(isinstance(name, str) and name for _, name in listed)
