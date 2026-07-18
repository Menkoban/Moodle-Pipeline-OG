#!/usr/bin/env python3
"""Didaktik-Profile: auswählbare didaktische Konzepte für den Kursbau.

Bisher ist das didaktische Konzept des Skills fest verdrahtet auf das
ZDQ-5-Ebenen-Modell mit der Pflicht-Sequenz
Einführung → Grundlagen → Vertiefung → Anwendung → Kurs-Recap → Glossar →
Material für Lehrkräfte (siehe `references/course-design.md` §2–3 und
`SKILL.md` Schritt 3). Diese Sequenz + Regeln sind heute reine Autoren-Guidance
(vom Modell beim Schreiben der Kurs-JSON befolgt), nicht in `build_mbz.py`/
`preview_mbz.py`/`validate_mbz.py` erzwungen – die Bau-Skripte verarbeiten die
Sektionen so, wie sie in der Kurs-JSON stehen.

Diese Datei macht das didaktische Konzept zu einem **auswählbaren Profil**: eine
Registry benannter Profile, jedes mit eigener Abschnitts-Sequenz und
Regel-Zusammenfassung. `DEFAULT_PROFILE_KEY = "zdq"` bildet exakt das heutige
Verhalten ab.

VERDRAHTUNG (Prompt-Ebene): Das gewählte Profil wird im **Briefing** immer
abgefragt (auch bei nur einem Profil) und in `course.didaktik_profil`
(Default `"zdq"`) persistiert; SKILL.md („Follow the section sequence…",
`quality_check` (b)) und `references/course-design.md` §3 folgen der
`section_sequence` / den `pflicht_abschnitte` des aktiven Profils. Die
Bau-Skripte bleiben sequenz-agnostisch → Default `zdq` = byte-identische
Ausgabe wie zuvor.

SPLIT-BEREITSCHAFT (Zukunft, NICHT umgesetzt): Jedes Profil ist ein
self-contained Dict (name, beschreibung, section_sequence, rules, guidance_ref).
`guidance_ref` zeigt auf den Autoren-Leitfaden des Konzepts. So lässt sich später
ein Profil samt Leitfaden zu einem eigenständigen Konzept-Skill herauslösen,
während der kombinierte Skill die Auswahl über ALLE Profile behält. Details:
`docs/superpowers/specs/2026-07-15-didaktik-profile-design.md`.
"""
import copy
import sys

DEFAULT_PROFILE_KEY = "zdq"


# --- Profil 1: ZDQ – 5-Ebenen-Modell (DEFAULT, heutiges Verhalten) ------
# Sektions-Reihenfolge exakt nach references/course-design.md §3
# („Pflicht-Sequenz der Lernabschnitte") und SKILL.md Schritt 3.
_ZDQ = {
    "key": "zdq",
    "name": "ZDQ – 5-Ebenen-Modell",
    "beschreibung": (
        "Handlungsorientiertes 5-Ebenen-Strukturmodell des ZDQ (vom Autor erweitert) "
        "(Lernelement → Lernbaustein → Lernabschnitt → Lerneinheit/Modul → "
        "Lernkurs) für die berufliche Bildung. Default-Konzept des Skills."
    ),
    # Autoren-Leitfaden dieses Konzepts (für einen späteren eigenständigen
    # Konzept-Skill vollständig hier referenzierbar):
    "guidance_ref": "references/course-design.md (Kap. 1–7)",
    # Index-0-Wrapper vor den nummerierten Lernabschnitten (course-design.md §3).
    "intro_section": {
        "key": "ueber-modul",
        "title": "Über dieses Modul",
        "zeit": None,
        "visible": 1,
        "pflicht": False,
    },
    # Die 7 nummerierten Lernabschnitte = die dokumentierte Pflicht-Sequenz.
    "section_sequence": [
        {"key": "einfuehrung", "title": "Einführung",
         "zeit": "~5 min", "visible": 1, "pflicht": True},
        {"key": "grundlagen", "title": "Grundlagen",
         "zeit": "~25 min", "visible": 1, "pflicht": False},
        {"key": "vertiefung", "title": "Vertiefung",
         "zeit": "~50 min", "visible": 1, "pflicht": True},
        {"key": "anwendung", "title": "Anwendung / Handlungsprodukt",
         "zeit": None, "visible": 1, "pflicht": True},
        {"key": "recap", "title": "Kurs-Recap",
         "zeit": "~10 min", "visible": 1, "pflicht": True},
        {"key": "glossar", "title": "Glossar",
         "zeit": None, "visible": 1, "pflicht": False},
        {"key": "lehrkraefte", "title": "Material für Lehrkräfte",
         "zeit": None, "visible": 0, "pflicht": False},
    ],
    "rules": {
        "leitprinzipien": [
            "Handlungsorientierung (Handlungssituation → Handlungsprodukt)",
            "Kompetenzorientierung (beobachtbares Können, nicht 'kennen')",
            "Aktiv statt konsumierend + formatives Feedback je Phase",
            "Chunking (ein Thema pro Lernabschnitt/Infoblatt)",
            "Niedrigschwelligkeit (einfache Sprache, viel Visualisierung)",
        ],
        "didaktische_begruendung": (
            "Vollständige Handlung (Informieren → Planen → Entscheiden → "
            "Ausführen → Kontrollieren → Bewerten) + AVIVA-Bogen als Rationale; "
            "spielt sich v. a. im Lernabschnitt 'Anwendung' ab."
        ),
        "constructive_alignment": (
            "Rückwärts planen: erst Ziele, dann Prüfung "
            "(Praxisauftrag/Test), dann Input."
        ),
        "pflicht_abschnitte": [
            "Einführung", "Vertiefung", "Anwendung / Handlungsprodukt",
            "Kurs-Recap",
        ],
        "wortbudget": "~25 Wörter Lerninhalt pro Lernminute",
        "quelle": "references/course-design.md §2–3; SKILL.md Schritt 3",
    },
}


# --- Profil 2: Vollständige Handlung / AVIVA (Beispiel-Stub) ------------------
# Beispiel für ein alternatives Konzept: die Phasen der vollständigen Handlung
# werden nicht nur Rationale (wie beim ZDQ-Modell), sondern selbst zur Abschnitts-
# Sequenz. STUB – zur Demonstration der Austauschbarkeit, noch nicht ausgebaut.
_VOLLSTAENDIGE_HANDLUNG = {
    "key": "vollstaendige-handlung",
    "name": "Vollständige Handlung / AVIVA",
    "beschreibung": (
        "Alternatives Konzept-Profil (Stub): die sechs Phasen der vollständigen "
        "Handlung strukturieren den Kurs unmittelbar, statt nur didaktische "
        "Begründung im Hintergrund zu sein. Für stark handlungszentrierte "
        "Projektaufträge."
    ),
    "guidance_ref": "STUB – eigener Konzept-Leitfaden noch zu schreiben",
    "intro_section": {
        "key": "auftrag",
        "title": "Der Auftrag",
        "zeit": None,
        "visible": 1,
        "pflicht": False,
    },
    "section_sequence": [
        {"key": "informieren", "title": "Informieren",
         "zeit": None, "visible": 1, "pflicht": True},
        {"key": "planen", "title": "Planen",
         "zeit": None, "visible": 1, "pflicht": True},
        {"key": "entscheiden", "title": "Entscheiden",
         "zeit": None, "visible": 1, "pflicht": True},
        {"key": "ausfuehren", "title": "Ausführen",
         "zeit": None, "visible": 1, "pflicht": True},
        {"key": "kontrollieren", "title": "Kontrollieren",
         "zeit": None, "visible": 1, "pflicht": True},
        {"key": "bewerten", "title": "Bewerten",
         "zeit": None, "visible": 1, "pflicht": True},
    ],
    "rules": {
        "leitprinzipien": [
            "Handlungsorientierung mit den sechs Phasen als sichtbarer Struktur",
            "Selbstständigkeit über den vollen Handlungszyklus",
        ],
        "didaktische_begruendung": (
            "Vollständige Handlung als Gliederungsprinzip (nicht nur Rationale)."
        ),
        "constructive_alignment": (
            "Bewerten schließt den Zyklus; Kriterien schon in 'Planen' offenlegen."
        ),
        "pflicht_abschnitte": [
            "Informieren", "Planen", "Ausführen", "Bewerten",
        ],
        "wortbudget": "~25 Wörter Lerninhalt pro Lernminute",
        "quelle": "STUB – noch nicht in references/ ausgearbeitet",
    },
    "stub": True,
}


PROFILES = {
    _ZDQ["key"]: _ZDQ,
    _VOLLSTAENDIGE_HANDLUNG["key"]: _VOLLSTAENDIGE_HANDLUNG,
}


def list_profiles():
    """Liste aller Profile als (key, name)-Paare, Default zuerst."""
    keys = [DEFAULT_PROFILE_KEY] + [
        k for k in PROFILES if k != DEFAULT_PROFILE_KEY]
    return [(k, PROFILES[k]["name"]) for k in keys]


def get_profile(key=DEFAULT_PROFILE_KEY):
    """Profil zu `key` (Default: 'zdq') als tiefe Kopie – die Registry bleibt
    unveränderlich. Unbekannter Key -> ValueError mit verfügbaren Keys."""
    if key is None:
        key = DEFAULT_PROFILE_KEY
    if key not in PROFILES:
        raise ValueError(
            f"Unbekanntes Didaktik-Profil {key!r}. "
            f"Verfügbar: {', '.join(sorted(PROFILES))}")
    return copy.deepcopy(PROFILES[key])


def section_titles(key=DEFAULT_PROFILE_KEY):
    """Die Abschnitts-Titel der Sequenz eines Profils (ohne intro_section)."""
    return [s["title"] for s in get_profile(key)["section_sequence"]]


if __name__ == "__main__":
    try:  # Windows-Konsole (cp1252) an Umlaute/Pfeil anpassen
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    for k, name in list_profiles():
        mark = "  (Default)" if k == DEFAULT_PROFILE_KEY else ""
        print(f"- {k}: {name}{mark}")
        print("    " + " -> ".join(section_titles(k)))
