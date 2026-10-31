#!/usr/bin/env python3
"""Didaktik-Profile: auswählbare didaktische Konzepte für den ADAPTIVEN Kursbau.

Angepasste Fassung der Registry aus dem linearen Schwester-Skill
(moodle-mbz-builder/scripts/didactic_profiles.py). Der adaptive Skill folgt
demselben ZDQ-5-Ebenen-Modell — aber VERZWEIGT: die flache lineare
Pflicht-Sequenz (Einführung → Grundlagen → Vertiefung → Anwendung → Recap)
mappt hier auf Stufen und Niveau-Kacheln (SKILL.md, Abschnitt
„ZDQ-Strukturmodell im adaptiven Kurs — VERBINDLICH"):

    Lerneinheit/Modul = Stufe (Themen-Etappe mit Testpunkt)
    Lernabschnitt     = Niveau-Kachel (+ Förder-Kachel als Vertiefung)
    Grundlagen/Vertiefung/Anwendung = Dreischritt IN jeder Niveau-Kachel
                        (Infoblatt → Übung → Niveau-Test)

Deshalb hat dieses Profil einen eigenen Key `zdq-adaptiv` (Default) — die
Abschnitts-Sequenz ist PARAMETRISCH über die Stufenzahl (der Eintrag mit
`parametrisch: True` wiederholt sich je Stufe). Die Bau-Skripte bleiben
sequenz-agnostisch: `build_adaptive.py` erzeugt die Struktur aus der
Stufen-Spec; dieses Profil ist Briefing-/Autoren-Guidance und wird im
Briefing IMMER abgefragt (auch bei nur einem Profil) und in
`course.didaktik_profil` persistiert.

VERDRAHTUNG (Prompt-Ebene): wie im linearen Skill — SKILL.md fragt das
Konzept im Pflicht-Intake ab; die Regeln unten spiegeln den
VERBINDLICH-Abschnitt. SPLIT-BEREITSCHAFT: self-contained Dict mit
`guidance_ref`, so lässt sich das Konzept später als eigenständiger
Konzept-Skill herauslösen.
"""
import copy
import sys

DEFAULT_PROFILE_KEY = "zdq-adaptiv"


# --- Profil 1: ZDQ – 5-Ebenen-Modell, VERZWEIGT (DEFAULT) ---------------
# Zuordnung + Pflicht-Sequenz exakt nach SKILL.md „ZDQ-Strukturmodell im
# adaptiven Kurs — VERBINDLICH" und references/course-design.md §2–3.
_ZDQ_ADAPTIV = {
    "key": "zdq-adaptiv",
    "name": "ZDQ – 5-Ebenen-Modell, verzweigt (adaptiv)",
    "beschreibung": (
        "Das handlungsorientierte 5-Ebenen-Strukturmodell des ZDQ (vom Autor erweitert) — "
        "verzweigt für adaptive Lernpfade: Stufe = Lerneinheit mit Testpunkt, "
        "Niveau-Kachel = Lernabschnitt (Grundlagen/Vertiefung/Anwendung als "
        "Dreischritt IN der Kachel), Förder-Kachel = Vertiefung 'anders "
        "erklärt'. Default-Konzept des adaptiven Skills."
    ),
    "guidance_ref": (
        "SKILL.md 'ZDQ-Strukturmodell im adaptiven Kurs — VERBINDLICH'; "
        "references/course-design.md (Kap. 1–7); references/adaptive-lernpfade.md"
    ),
    "intro_section": {
        "key": "intro",
        "title": "Einführung (Intro-Kachel)",
        "zeit": "~5 min",
        "visible": 1,
        "pflicht": True,
        "hinweis": ("Handlungssituation + Funktionsweise des adaptiven "
                    "Systems; fügt build_adaptive.py automatisch ein."),
    },
    # Parametrische Sequenz: der Stufen-Eintrag wiederholt sich je Stufe 1..N.
    "section_sequence": [
        {"key": "stufe", "title": "Stufe n: Niveau-Kacheln (+ Förder-Kachel)",
         "zeit": "je Kachel ~45–60 min", "visible": 1, "pflicht": True,
         "parametrisch": True,
         "hinweis": ("Je Stufe eine Kachel pro Niveau-Pfad; in JEDER Kachel "
                     "der Dreischritt Infoblatt (material:true, eigenes SVG) "
                     "→ Übung/Anwendung → Niveau-Test. Förder-Kachel = "
                     "Vertiefung 'anders erklärt' unterhalb der Schwelle.")},
        {"key": "abschluss", "title": "Kurs-Recap (Abschluss-Kachel)",
         "zeit": "~10 min", "visible": 1, "pflicht": True,
         "hinweis": ("Videozusammenfassung-Platzhalter + Pflicht-Attribution "
                     "ergänzt build_adaptive.py automatisch.")},
        {"key": "lehrkraefte", "title": "Material für Lehrkräfte",
         "zeit": None, "visible": 0, "pflicht": False},
    ],
    "rules": {
        "leitprinzipien": [
            "Handlungsorientierung (Handlungssituation → Handlungsprodukt)",
            "Kompetenzorientierung (beobachtbares Können, nicht 'kennen')",
            "Einstufung ⊥ Bewertung (Fenster nur am letzten Test; kumulativer "
            "Score ist reine Doku — sonst Ratschen-Effekt)",
            "Durchlässigkeit (Auf-/Abstieg symmetrisch, kein toter Pfad)",
            "Niveaus differenzieren nach Komplexität, nicht nur Textmenge",
        ],
        "didaktische_begruendung": (
            "Vollständige Handlung als Rationale des Dreischritts in jeder "
            "Niveau-Kachel; die Verzweigung ist Binnendifferenzierung im "
            "5-Ebenen-Modell, keine eigene Didaktik."
        ),
        "constructive_alignment": (
            "Rückwärts planen: erst Ziele je Niveau, dann Niveau-Test "
            "(Fenster-Schwellen), dann Input."
        ),
        "pflicht_abschnitte": [
            "Einführung (Intro-Kachel)",
            "Stufe n: Niveau-Kacheln (+ Förder-Kachel)",
            "Kurs-Recap (Abschluss-Kachel)",
        ],
        "wortbudget": "~25 Wörter Lerninhalt pro Lernminute (je Kachel)",
        "quelle": ("SKILL.md 'ZDQ-Strukturmodell im adaptiven Kurs'; "
                   "references/adaptive-lernpfade.md §4"),
    },
}


PROFILES = {
    _ZDQ_ADAPTIV["key"]: _ZDQ_ADAPTIV,
}


def list_profiles():
    """Liste aller Profile als (key, name)-Paare, Default zuerst."""
    keys = [DEFAULT_PROFILE_KEY] + [
        k for k in PROFILES if k != DEFAULT_PROFILE_KEY]
    return [(k, PROFILES[k]["name"]) for k in keys]


def get_profile(key=DEFAULT_PROFILE_KEY):
    """Profil zu `key` (Default: 'zdq-adaptiv') als tiefe Kopie – die Registry
    bleibt unveränderlich. Unbekannter Key -> ValueError mit verfügbaren Keys."""
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
