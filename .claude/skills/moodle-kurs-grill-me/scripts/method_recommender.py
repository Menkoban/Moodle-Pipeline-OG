#!/usr/bin/env python3
"""method_recommender.py — Didaktische Methoden-Empfehlungs-Engine fuer Moodle-Kurse.

Enthaelt ein strukturiertes Register von ueber 40 berufsdidaktischen Methoden
und berechnet anhand von Fachbereich, Schulform, Ausbildungsniveau und
E-Learning-Format eine massgeschneiderte Top-3-Methodenempfehlung mit Begruendung.
"""

import json
import os
import sys
import argparse

METHODEN_REGISTER = [
    # 1. HANDLUNGSORIENTIERTE & PRAXIS-METHODEN
    {
        "id": "leittextmethode",
        "name": "Leittextmethode (Selbstgesteuertes Handeln)",
        "kategorie": "Handlungsorientierung",
        "phasen": ["Informieren", "Planen", "Entscheiden", "Ausführen", "Kontrollieren", "Bewerten"],
        "moodle_tools": ["formular", "assign", "quiz"],
        "beschreibung": "Lernende erarbeiten komplexe Handlungsabläufe anhand von Leitfragen, erstellen selbstständig einen Arbeitsplan und überprüfen ihr Ergebnis mit Kontrollbögen.",
        "vorteil": "Fördert maximale Selbstständigkeit und Methodenkompetenz bei betrieblichen Aufträgen.",
        "tags": ["technik", "wirtschaft", "gesundheit", "it", "gastro", "bs", "bfs", "fs", "blended_learning", "leittext_digital"]
    },
    {
        "id": "6_stufen_methode",
        "name": "6-Stufen-Methode der vollständigen Handlung",
        "kategorie": "Handlungsorientierung",
        "phasen": ["Informieren", "Planen", "Entscheiden", "Ausführen", "Kontrollieren", "Bewerten"],
        "moodle_tools": ["assign", "formular", "rubrik"],
        "beschreibung": "Klassischer didaktischer Handlungszyklus für ganzheitliche Werkstatt- und Montageprojekte.",
        "vorteil": "Feste KMK-Verankerung; sichert den Übergang von kognitiver Planung zu praktischem Tun.",
        "tags": ["technik", "gastro", "bs", "bfs", "blended_learning", "scenario_based_pbl"]
    },
    {
        "id": "projektmethode",
        "name": "Projektmethode (Komplexer Projektauftrag)",
        "kategorie": "Handlungsorientierung",
        "phasen": ["Planen", "Entscheiden", "Ausführen", "Bewerten"],
        "moodle_tools": ["assign", "forum", "wiki"],
        "beschreibung": "Lernende bearbeiten im Team ein offenes, mehrwöchiges Projekt mit realem Endprodukt.",
        "vorteil": "Hohe Eigenverantwortung, Teamkompetenz und interdisziplinäres Arbeiten.",
        "tags": ["it", "technik", "wirtschaft", "fos", "bgy", "fs", "blended_learning"]
    },
    {
        "id": "werkstattauftrag",
        "name": "Realer Werkstattauftrag mit Fertigungs-/Prüfplan",
        "kategorie": "Handlungsorientierung",
        "phasen": ["Informieren", "Planen", "Ausführen", "Kontrollieren"],
        "moodle_tools": ["formular", "assign", "hotspot"],
        "beschreibung": "Authentischer Kundenauftrag mit Materialauswahl, Sicherheitsunterweisung und Werkstattdokumentation.",
        "vorteil": "Direkter Praxisbezug zur betrieblichen Ausbildung.",
        "tags": ["technik", "gastro", "bs", "blended_learning"]
    },
    {
        "id": "4_stufen_unterweisung",
        "name": "4-Stufen-Methode (Arbeitsunterweisung)",
        "kategorie": "Handlungsorientierung",
        "phasen": ["Informieren", "Ausführen", "Kontrollieren"],
        "moodle_tools": ["page", "hotspot", "quiz"],
        "beschreibung": "1. Vorbereiten, 2. Vormachen/Erklären, 3. Nachmachen/Erklären lassen, 4. Üben.",
        "vorteil": "Ideal für motorische Grundfertigkeiten, Geräteeinweisungen und UVV-Sicherheitsregeln.",
        "tags": ["technik", "gesundheit", "gastro", "av", "bs", "microlearning"]
    },
    {
        "id": "erkundungsauftrag",
        "name": "Erkundungsauftrag (Betrieb / Baustelle / Anlage)",
        "kategorie": "Handlungsorientierung",
        "phasen": ["Informieren", "Ausführen", "Bewerten"],
        "moodle_tools": ["formular", "assign"],
        "beschreibung": "Gezielte Recherche- und Dokumentationsaufgabe im eigenen Ausbildungsbetrieb oder an realen Maschinen.",
        "vorteil": "Verzahnung von Lernort Schule und Lernort Betrieb (Lernortkooperation).",
        "tags": ["technik", "wirtschaft", "gesundheit", "bs", "blended_learning"]
    },

    # 2. PROBLEM- & DIAGNOSE-METHODEN
    {
        "id": "stoerungsanalyse_diagnose",
        "name": "Störungsanalyse & Fehlersuche (Bug-Hunt)",
        "kategorie": "Problem- & Diagnose",
        "phasen": ["Informieren", "Planen", "Entscheiden", "Ausführen", "Kontrollieren"],
        "moodle_tools": ["hotspot", "simulation", "formular"],
        "beschreibung": "Systematische Eingrenzung eines Fehlers anhand von Symptomen, Schaltplänen, Messwerten und Prüfschritten.",
        "vorteil": "Schult analytisches Denken und methodische Fehlerdiagnose nach DIN VDE.",
        "tags": ["technik", "it", "bs", "fs", "flipped_classroom", "scenario_based_pbl"]
    },
    {
        "id": "fallstudie_case_study",
        "name": "Fallstudie (Case Study)",
        "kategorie": "Problem- & Diagnose",
        "phasen": ["Informieren", "Planen", "Entscheiden", "Bewerten"],
        "moodle_tools": ["page", "forum", "assign"],
        "beschreibung": "Analyse einer realistischen Unternehmenssituation mit Zielkonflikten und Erarbeitung begründeter Handlungsoptionen.",
        "vorteil": "Schult Urteilsvermögen, betriebswirtschaftliche Abwägungen und Entscheidungsfreude.",
        "tags": ["wirtschaft", "gesundheit", "it", "fos", "bgy", "fs", "flipped_classroom", "scenario_based_pbl"]
    },
    {
        "id": "incident_methode",
        "name": "Incident-Methode (Kritischer Zwischenfall)",
        "kategorie": "Problem- & Diagnose",
        "phasen": ["Informieren", "Entscheiden", "Bewerten"],
        "moodle_tools": ["forum", "formular"],
        "beschreibung": "Ein dramatischer Vorfall (z.B. Netzausfall, Chemieunfall, Reklamation) erfordert sofortige Informationsbeschaffung und Sofortmaßnahmen.",
        "vorteil": "Hohe Emotionalisierung und Training von Notfall- und Krisenkompetenz.",
        "tags": ["gesundheit", "technik", "it", "bs", "fs", "microlearning"]
    },
    {
        "id": "ishikawa_ursache_wirkung",
        "name": "Ursache-Wirkungs-Analyse (Ishikawa / Fischgräten-Diagramm)",
        "kategorie": "Problem- & Diagnose",
        "phasen": ["Informieren", "Planen", "Bewerten"],
        "moodle_tools": ["formular", "assign"],
        "beschreibung": "Systematische Strukturierung von Fehlerursachen nach den 5M (Mensch, Maschine, Material, Methode, Mitwelt).",
        "vorteil": "Fördert ganzheitliches Qualitätsmanagement und strukturierte Ursachenforschung.",
        "tags": ["technik", "wirtschaft", "it", "fs", "bgy", "blended_learning"]
    },
    {
        "id": "5_why_methode",
        "name": "5-Why-Methode (Root Cause Analysis)",
        "kategorie": "Problem- & Diagnose",
        "phasen": ["Informieren", "Planen", "Kontrollieren"],
        "moodle_tools": ["formular", "quiz"],
        "beschreibung": "Fünffaches Hinterfragen ('Warum ist das passiert?'), um zur wahren Grundursache eines Problems vorzudringen.",
        "vorteil": "Einfach anzuwenden, verhindert oberflächliche Scheinlösungen.",
        "tags": ["technik", "wirtschaft", "gesundheit", "av", "bs", "microlearning"]
    },
    {
        "id": "moralisches_dilemma",
        "name": "Moralisches Dilemma / Ethische Urteilsbildung",
        "kategorie": "Problem- & Diagnose",
        "phasen": ["Informieren", "Entscheiden", "Bewerten"],
        "moodle_tools": ["forum", "assign"],
        "beschreibung": "Diskussion einer Situation ohne eindeutig richtige Lösung (z.B. Datenschutz vs. Effizienz, Triage, Whistleblowing).",
        "vorteil": "Fördert ethische Reflexion, Argumentationskompetenz und Wertebewusstsein.",
        "tags": ["allgemeinbildung", "gesundheit", "it", "fos", "bgy", "flipped_classroom"]
    },

    # 3. KOOPERATIVE & INTERAKTIVE METHODEN
    {
        "id": "think_pair_share",
        "name": "Think-Pair-Share digital",
        "kategorie": "Kooperatives Lernen",
        "phasen": ["Informieren", "Planen", "Bewerten"],
        "moodle_tools": ["formular", "forum"],
        "beschreibung": "1. Think: Individuelle Aufgabenbearbeitung im Formular. 2. Pair: Tandem-Abgleich im Chat/Forum. 3. Share: Plenumsdiskussion.",
        "vorteil": "Aktiviert 100% aller Lernenden und senkt Hemmschwellen durch Partnerabsicherung.",
        "tags": ["technik", "wirtschaft", "allgemeinbildung", "it", "bs", "bfs", "fos", "flipped_classroom", "theorie_praxis_tandem"]
    },
    {
        "id": "expertenpuzzle_jigsaw",
        "name": "Expertenpuzzle (Jigsaw digital)",
        "kategorie": "Kooperatives Lernen",
        "phasen": ["Informieren", "Ausführen", "Bewerten"],
        "moodle_tools": ["forum", "glossar", "assign"],
        "beschreibung": "Lernende werden in Expertengruppen zu Spezialthemen geschult und unterrichten anschließend ihre Stammgruppe.",
        "vorteil": "Verantwortungsübernahme für den Lernerfolg der Mitschüler und Entlastung der Lehrkraft.",
        "tags": ["technik", "gesundheit", "wirtschaft", "bs", "fos", "bgy", "blended_learning"]
    },
    {
        "id": "reziprokes_lehren",
        "name": "Reziprokes Lehren (Peer-Teaching)",
        "kategorie": "Kooperatives Lernen",
        "phasen": ["Informieren", "Ausführen", "Kontrollieren"],
        "moodle_tools": ["forum", "assign"],
        "beschreibung": "Lernende schlüpfen abwechselnd in die Rolle des Lehrers (Zusammenfassen, Fragen stellen, Klären, Vorhersagen).",
        "vorteil": "Höchste Behaltensrate nach Hattie (d = 0.74); tiefes Text- und Fachverständnis.",
        "tags": ["gesundheit", "wirtschaft", "allgemeinbildung", "fos", "bgy", "flipped_classroom"]
    },
    {
        "id": "placemat_digital",
        "name": "Placemat-Methode (Digitale Schreibkonferenz)",
        "kategorie": "Kooperatives Lernen",
        "phasen": ["Informieren", "Entscheiden"],
        "moodle_tools": ["forum", "formular"],
        "beschreibung": "Vier individuelle Textfelder um ein zentrales Konsensfeld zur gemeinsamen Lösungsfindung.",
        "vorteil": "Gleichberechtigte Teilhabe; verhindert die Dominanz einzelner Wortführer.",
        "tags": ["wirtschaft", "allgemeinbildung", "bfs", "fos", "blended_learning"]
    },
    {
        "id": "stationenlernen_lerntheke",
        "name": "Digitale Lerntheke / Stationenlernen",
        "kategorie": "Kooperatives Lernen",
        "phasen": ["Informieren", "Ausführen", "Kontrollieren"],
        "moodle_tools": ["hotspot", "formular", "quiz"],
        "beschreibung": "Kacheln als modulare Stationen mit Pflichtaufgaben (Basics) und Wahlaufgaben (Vertiefung/Experte).",
        "vorteil": "Exzellente Binnendifferenzierung und Lerntempo-Individualisierung.",
        "tags": ["technik", "wirtschaft", "gesundheit", "av", "bfs", "sek1_2", "lerntheke_stationen"]
    },
    {
        "id": "world_cafe_digital",
        "name": "World Café digital (Themen-Rondell)",
        "kategorie": "Kooperatives Lernen",
        "phasen": ["Planen", "Entscheiden", "Bewerten"],
        "moodle_tools": ["forum", "wiki"],
        "beschreibung": "Lernende rotieren digital zwischen thematischen Diskussionsforen und entwickeln Ideen weiter.",
        "vorteil": "Erzeugt viele Perspektiven und kreative Lösungsansätze in kurzer Zeit.",
        "tags": ["wirtschaft", "allgemeinbildung", "fs", "bgy", "blended_learning"]
    },

    # 4. KREATIVITÄTS- & VISUALISIERUNGS-METHODEN
    {
        "id": "concept_mapping",
        "name": "Concept Mapping & Strukturskizze",
        "kategorie": "Kreativität & Visualisierung",
        "phasen": ["Informieren", "Planen"],
        "moodle_tools": ["hotspot", "assign"],
        "beschreibung": "Visuelle Verknüpfung von Fachbegriffen mit beschrifteten Beziehungspfeilen ('ist Teil von', 'führt zu').",
        "vorteil": "Macht mentale Modelle sichtbar und entlarvt fachliche Fehlvorstellungen sofort.",
        "tags": ["technik", "gesundheit", "it", "bgy", "fs", "flipped_classroom"]
    },
    {
        "id": "brainwriting_635",
        "name": "Brainwriting 6-3-5 digital",
        "kategorie": "Kreativität & Visualisierung",
        "phasen": ["Planen", "Entscheiden"],
        "moodle_tools": ["formular", "forum"],
        "beschreibung": "6 Teilnehmer schreiben 3 Ideen in 5 Minuten und entwickeln die Ideen der Vorgänger schrittweise weiter.",
        "vorteil": "Liefert bis zu 108 strukturierte Ideen in 30 Minuten ohne Diskussionsblockaden.",
        "tags": ["it", "wirtschaft", "technik", "fos", "bgy", "fs", "blended_learning"]
    },
    {
        "id": "walt_disney_methode",
        "name": "Walt-Disney-Methode (3 Rollen: Träumer, Realist, Kritiker)",
        "kategorie": "Kreativität & Visualisierung",
        "phasen": ["Planen", "Entscheiden", "Bewerten"],
        "moodle_tools": ["forum", "assign"],
        "beschreibung": "Systematische Betrachtung einer Lösung aus drei Perspektiven: Visionär $\rightarrow$ Pragmatiker $\rightarrow$ Bedenkenträger.",
        "vorteil": "Führt von kühnen Ideen zu praxistauglichen, krisenfesten Konzepten.",
        "tags": ["wirtschaft", "it", "technik", "bgy", "fs", "scenario_based_pbl"]
    },
    {
        "id": "morphologischer_kasten",
        "name": "Morphologischer Kasten (Systematische Variantenbildung)",
        "kategorie": "Kreativität & Visualisierung",
        "phasen": ["Planen", "Entscheiden"],
        "moodle_tools": ["formular", "assign"],
        "beschreibung": "Zerlegung eines Problems in Parameter und Ausprägungen zur systematischen Kombination neuer Lösungen.",
        "vorteil": "Klassisches Ingenieur- und Konstruktionswerkzeug.",
        "tags": ["technik", "it", "fs", "bgy", "blended_learning"]
    },

    # 5. FEEDBACK-, BEWERTUNGS- & REFLEXIONSMETHODEN
    {
        "id": "kriteriengeleitetes_peer_feedback",
        "name": "Kriteriengeleitetes Peer-Feedback mit Bewertungsrubrik",
        "kategorie": "Reflexion & Bewertung",
        "phasen": ["Kontrollieren", "Bewerten"],
        "moodle_tools": ["assign", "workshop"],
        "beschreibung": "Gegenseitige Beurteilung von Arbeitsergebnissen anhand einer transparenten Matrix mit Notenstufen.",
        "vorteil": "Schult Fachsprache, Qualitätsbewusstsein und professionelle Feedback-Kultur.",
        "tags": ["technik", "wirtschaft", "gesundheit", "it", "gastro", "bs", "fos", "bgy", "fs", "theorie_praxis_tandem"]
    },
    {
        "id": "one_minute_paper",
        "name": "One-Minute-Paper / Blitzlicht-Reflexion",
        "kategorie": "Reflexion & Bewertung",
        "phasen": ["Bewerten"],
        "moodle_tools": ["formular", "quiz"],
        "beschreibung": "Kurze 60-Sekunden-Rückmeldung: 1. Was war das Wichtigste heute? 2. Welche Frage ist noch offen?",
        "vorteil": "Liefert der Lehrkraft in Sekundenschnelle formatives Feedback zum Lernstand.",
        "tags": ["allgemeinbildung", "technik", "wirtschaft", "av", "bs", "bfs", "microlearning"]
    },
    {
        "id": "3_2_1_reflexion",
        "name": "3-2-1-Transfer-Reflexion",
        "kategorie": "Reflexion & Bewertung",
        "phasen": ["Bewerten"],
        "moodle_tools": ["formular", "forum"],
        "beschreibung": "3 Dinge, die ich gelernt habe; 2 Dinge, die ich im Betrieb anwenden werde; 1 Frage, die bleibt.",
        "vorteil": "Starker Transferbezug zur betrieblichen Praxis.",
        "tags": ["bs", "bfs", "fs", "blended_learning"]
    },
    {
        "id": "kompetenzraster_selbsteinschaetzung",
        "name": "Kompetenzraster & Selbsteinschätzung (Ich-kann-Check)",
        "kategorie": "Reflexion & Bewertung",
        "phasen": ["Informieren", "Bewerten"],
        "moodle_tools": ["formular", "quiz"],
        "beschreibung": "Abgleich des eigenen Könnens mit operationalisierten Kann-Beschreibungen vor und nach dem Modul.",
        "vorteil": "Macht Lernfortschritte unmittelbar sichtbar und stärkt die Selbstwirksamkeit.",
        "tags": ["av", "bfs", "bs", "sek1_2", "lerntheke_stationen", "mastery_learning"]
    },
    {
        "id": "gestufte_hilfen_scaffolding",
        "name": "Gestufte Lernhilfen (Scaffolding / Tipp-Karten)",
        "kategorie": "Binnendifferenzierung",
        "phasen": ["Informieren", "Planen", "Ausführen"],
        "moodle_tools": ["formular", "page"],
        "beschreibung": "Aufklappbare Hilfestellungen (Stufe 1: Begriff, Stufe 2: Formelansatz, Stufe 3: Teillösung).",
        "vorteil": "Ermöglicht schwächeren Lernenden Erfolgserlebnisse ohne Frustration.",
        "tags": ["technik", "wirtschaft", "gesundheit", "av", "bfs", "bs", "theorie_praxis_tandem"]
    },

    # 6. SIMULATIONS- & ROLLENSPIEL-METHODEN
    {
        "id": "beratungssimulation_kundengespraech",
        "name": "Kundengespräch & Fachberatungssimulation",
        "kategorie": "Simulation & Rollenspiel",
        "phasen": ["Informieren", "Planen", "Entscheiden", "Ausführen"],
        "moodle_tools": ["formular", "forum", "assign"],
        "beschreibung": "Bedarfsanalyse, Angebotserläuterung und Einwandbehandlung im simulierten Kundenszenario.",
        "vorteil": "Verknüpft Fachkompetenz unmittelbar mit Sozial- und Kommunikationskompetenz.",
        "tags": ["wirtschaft", "gesundheit", "it", "gastro", "bs", "fos", "blended_learning"]
    },
    {
        "id": "reklamationsgespraech_konfliktloesung",
        "name": "Reklamationsbearbeitung & Deeskalation",
        "kategorie": "Simulation & Rollenspiel",
        "phasen": ["Informieren", "Entscheiden", "Ausführen"],
        "moodle_tools": ["formular", "forum"],
        "beschreibung": "Umgang mit verärgerten Kunden, rechtliche Einordnung (Gewährleistung/Garantie) und lösungsorientierte Einigung.",
        "vorteil": "Praxisnahes Konflikt- und Krisenmanagement nach BGB/HGB.",
        "tags": ["wirtschaft", "gastro", "bs", "scenario_based_pbl"]
    },
    {
        "id": "interaktive_prozess_simulation",
        "name": "Interaktive physikalisch-technische Simulation",
        "kategorie": "Simulation & Rollenspiel",
        "phasen": ["Informieren", "Planen", "Kontrollieren"],
        "moodle_tools": ["simulation", "hotspot"],
        "beschreibung": "Dynamische Erkundung nicht sichtbarer Größen (Ströme, Kräfte, Drücke, Drehzahlen) mit Schiebereglern.",
        "vorteil": "Macht abstrakte physikalische Zusammenhänge visuell und haptisch begreifbar.",
        "tags": ["technik", "it", "bs", "fos", "bgy", "fs", "theorie_praxis_tandem", "flipped_classroom"]
    }
]


def recommend_methods(fachbereich, schulform, niveau="fachstufe", format="blended_learning", elearning_format=None, top_n=3):
    """Berechnet ein Scoring fuer alle Methoden und liefert die Top-Empfehlungen zurueck."""
    fb = (fachbereich or "").lower()
    sf = (schulform or "").lower()
    fmt = (elearning_format or format or "").lower()
    
    scored_methods = []
    
    for m in METHODEN_REGISTER:
        score = 10  # Basis-Score
        tags = [t.lower() for t in m.get("tags", [])]
        
        # Fachbereichs-Match (+15)
        if any(f in fb for f in tags):
            score += 15
        elif any(f in ["technik", "wirtschaft", "gesundheit", "it", "gastro", "allgemeinbildung"] if f in fb else False for f in tags):
            score += 10
            
        # Schulform-Match (+15)
        if any(s in sf for s in tags):
            score += 15
            
        # E-Learning-Format Match (+20)
        if any(f in fmt for f in tags):
            score += 20
            
        # Bonus fuer Moodle-Passgenauigkeit
        if "formular" in m.get("moodle_tools", []):
            score += 5
        if "hotspot" in m.get("moodle_tools", []) or "simulation" in m.get("moodle_tools", []):
            score += 5
            
        scored_methods.append({
            "id": m["id"],
            "name": m["name"],
            "kategorie": m["kategorie"],
            "beschreibung": m["beschreibung"],
            "vorteil": m["vorteil"],
            "moodle_tools": m["moodle_tools"],
            "score": score
        })
        
    scored_methods.sort(key=lambda x: x["score"], reverse=True)
    
    # Diversitaet sichern: Nicht 3 Methoden aus exakt derselben Kategorie waehlen
    selected = []
    seen_cats = set()
    for sm in scored_methods:
        if sm["kategorie"] not in seen_cats or len(seen_cats) >= 2:
            selected.append(sm)
            seen_cats.add(sm["kategorie"])
        if len(selected) >= top_n:
            break
            
    # Erste Methode als (Empfohlen) markieren
    for i, sm in enumerate(selected):
        sm["is_recommended"] = (i == 0)
        sm["badge"] = "(Empfohlen)" if i == 0 else f"Option {i+1}"
        
    return selected


def main():
    parser = argparse.ArgumentParser(description="Berechnet didaktische Methodenempfehlungen.")
    parser.add_argument("--fachbereich", default="Technik", help="Fachbereich (Technik, Wirtschaft, Gesundheit, etc.)")
    parser.add_argument("--schulform", default="bs", help="Schulform (bs, bfs, fos, bgy, av, fs)")
    parser.add_argument("--format", default="blended_learning", help="E-Learning-Format (blended_learning, flipped_classroom, etc.)")
    parser.add_argument("--json", action="store_true", help="JSON-Ausgabe")

    args = parser.parse_args()
    recs = recommend_methods(args.fachbereich, args.schulform, format=args.format)

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    if args.json:
        print(json.dumps(recs, indent=2, ensure_ascii=False))
        return 0

    print(f"\n=======================================================")
    print(f"DIDAKTISCHE METHODEN-EMPFEHLUNG FUER:")
    print(f"Fachbereich: {args.fachbereich} | Schulform: {args.schulform.upper()} | Format: {args.format}")
    print(f"=======================================================\n")

    for r in recs:
        prefix = "* [EMPFOHLEN]" if r["is_recommended"] else f"  [{r['badge']}]"
        print(f"{prefix} {r['name']} ({r['kategorie']})")
        print(f"    Beschreibung: {r['beschreibung']}")
        print(f"    Vorteil:      {r['vorteil']}")
        print(f"    Moodle-Tools: {', '.join(r['moodle_tools'])}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
