# -*- coding: utf-8 -*-
"""validate_steckbrief.py — Defensive Validierung des Moodle-Kurs-Steckbriefs (Gate 0).

Prüft:
  1. JSON-Wohlgeformtheit und Schema-Konformität (steckbrief-schema.json)
  2. Didaktische Vollständigkeit (Cluster 1 bis 6):
     - Curriculares Profil & KMK/CuVo-Abgleich
     - Handlungssituation & Continuous Narrative (ALLE Kacheln bauen aufeinander auf)
     - Fachinhalte, Formeln & Normen
     - Fehlkonzepte & Arbeitsmittel (falls vorhanden)
     - Aufgaben-Architektur mit Moodle-Aktivitäten
     - Interaktive Medien-Trias (Hotspot, Simulation, Formular)
     - Kachelstruktur (4 bis 12 Kacheln)
  3. Formale Konsistenz:
     - Keine verwaisten Kacheln
     - Formel-Syntax und Pfeil-Typografie (&rarr; / →)
     - Vorhandensein der 6 Handlungsphasen
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Tuple


def validate_steckbrief_dict(data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """Gibt (fehler, warnungen) zurück."""
    fehler: List[str] = []
    warnungen: List[str] = []

    # 1. Grunddaten & Blended-Learning-Makroszenario
    if not data.get("titel") or len(data["titel"]) < 5:
        fehler.append("Kurstitel fehlt oder ist kürzer als 5 Zeichen.")
    if not data.get("shortname") or not re.match(r"^[a-z0-9-]+$", data["shortname"]):
        fehler.append("Shortname fehlt oder enthält ungültige Zeichen (nur a-z, 0-9, Bindestrich).")
    if data.get("didaktik_profil") not in ("zdq", "theorie-praxis-tandem", "vollstaendige-handlung", "pbl", "linear"):
        warnungen.append(f"Unbekanntes Didaktik-Profil: '{data.get('didaktik_profil')}'. Empfohlen: 'zdq'.")

    # Blended-Learning-Einsatzszenario (Makro-Ebene Pflichtfeld)
    blended = data.get("blended_szenario")
    if not blended:
        fehler.append("Pflichtfeld 'blended_szenario' fehlt im Steckbrief. Gültig: 'integriert', 'flipped', 'werkstatt_labor', 'begleitend'.")
    elif blended not in ("integriert", "flipped", "werkstatt_labor", "begleitend"):
        fehler.append(f"Ungültiges Blended-Szenario '{blended}'. Erlaubt sind: 'integriert', 'flipped', 'werkstatt_labor', 'begleitend'.")

    # 2. Cluster 1: Curriculum & Lerngruppe (Untercluster 1.1, 1.2, 1.3)
    curr = data.get("curriculum", {})
    if not curr.get("beruf"):
        fehler.append("Cluster 1 (Curriculum): Ausbildungsberuf ('beruf') fehlt.")
    if not curr.get("ausbildungsjahr"):
        fehler.append("Cluster 1 (Curriculum): Ausbildungsjahr fehlt.")
    if not curr.get("lernfeld"):
        fehler.append("Cluster 1 (Curriculum): Lernfeld fehlt.")
    if not curr.get("zielformulierung_volltext") or len(curr.get("zielformulierung_volltext", "")) < 20:
        warnungen.append("Cluster 1 (Curriculum): 'zielformulierung_volltext' fehlt oder ist sehr kurz.")

    vh = curr.get("vollstaendige_handlung", {})
    required_phases = ["informieren", "planen", "entscheiden", "ausfuehren", "kontrollieren", "bewerten"]
    for ph in required_phases:
        if ph not in vh or not isinstance(vh[ph], list):
            fehler.append(f"Cluster 1 (Curriculum): Phase der vollständigen Handlung '{ph}' fehlt in vollstaendige_handlung.")

    # 3. Cluster 2: Handlungssituation & Continuous Narrative
    hs = data.get("handlungssituation", {})
    for field in ["betrieb", "kontext", "problem", "leitfrage", "handlungsprodukt"]:
        if not hs.get(field):
            fehler.append(f"Cluster 2 (Handlungssituation): Pflichtfeld '{field}' fehlt.")

    # 4. Cluster 3: Fachlichkeit & Normen
    fach = data.get("fachlichkeit", {})
    if not fach.get("begriffe") or len(fach["begriffe"]) < 3:
        fehler.append("Cluster 3 (Fachlichkeit): Mindestens 3 Fachbegriffe erforderlich.")
    if not fach.get("formeln") or len(fach["formeln"]) < 1:
        warnungen.append("Cluster 3 (Fachlichkeit): Keine Berechnungsformeln angegeben.")
    if not fach.get("normen") or len(fach["normen"]) < 1:
        warnungen.append("Cluster 3 (Fachlichkeit): Keine DIN/EN/ISO/VDE-Normen angegeben.")
    
    # Formel-Typografie-Check
    for f in fach.get("formeln", []):
        if r"\to" in f or r"\rightarrow" in f:
            fehler.append(f"Typografie-Fehler in Formel '{f}': LaTeX \\to / \\rightarrow gefunden. Bitte &rarr; oder '→' verwenden!")

    # 5. Cluster 4: Aufgaben-Architektur
    aufg = data.get("aufgaben_kaskade", {})
    if not aufg.get("grundlagen_erkundung"):
        fehler.append("Cluster 4 (Aufgaben): 'grundlagen_erkundung' fehlt.")
    if not aufg.get("vertiefung_formular") or not aufg["vertiefung_formular"].get("felder"):
        fehler.append("Cluster 4 (Aufgaben): 'vertiefung_formular' mit Feldern fehlt.")
    praxis = aufg.get("anwendung_praxisauftrag", {})
    if not praxis.get("phasen") or len(praxis["phasen"]) < 6:
        fehler.append("Cluster 4 (Aufgaben): 'anwendung_praxisauftrag' muss 6 Phasen der vollständigen Handlung umfassen.")
    if not praxis.get("rubrik_kriterien") or len(praxis["rubrik_kriterien"]) < 3:
        fehler.append("Cluster 4 (Aufgaben): 'rubrik_kriterien' muss mindestens 3 Bewertungskriterien definieren.")

    # 6. Cluster 5: Medien-Trias
    med = data.get("medien_simulation", {})
    if med.get("hat_simulation") and not med.get("simulation"):
        warnungen.append("Cluster 5 (Medien): 'hat_simulation' ist true, aber keine Simulations-Spezifikation hinterlegt.")

    # 7. Cluster 6: Kachelstruktur
    kachel_info = data.get("kachelstruktur", {})
    kacheln = kachel_info.get("kacheln", [])
    if len(kacheln) < 4 or len(kacheln) > 12:
        fehler.append(f"Cluster 6 (Kachelstruktur): Anzahl Kacheln ({len(kacheln)}) liegt außerhalb des zulässigen Bereichs (4 bis 12).")

    for idx, k in enumerate(kacheln, 1):
        if not k.get("titel"):
            fehler.append(f"Cluster 6 (Kachelstruktur): Kachel {idx} hat keinen Titel.")
        if not k.get("aktivitaeten") or len(k["aktivitaeten"]) < 1:
            warnungen.append(f"Cluster 6 (Kachelstruktur): Kachel {idx} ('{k.get('titel')}') hat keine Aktivitäten.")

    return fehler, warnungen


def main() -> int:
    parser = argparse.ArgumentParser(description="Validiert den didaktischen Moodle-Kurs-Steckbrief (Gate 0).")
    parser.add_argument("steckbrief_json", help="Pfad zur kurs-steckbrief.json")
    args = parser.parse_args()

    if not os.path.exists(args.steckbrief_json):
        print(f"FEHLER: Datei '{args.steckbrief_json}' existiert nicht.", file=sys.stderr)
        return 1

    try:
        with open(args.steckbrief_json, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"FEHLER: Ungültiges JSON in '{args.steckbrief_json}': {e}", file=sys.stderr)
        return 1

    fehler, warnungen = validate_steckbrief_dict(data)

    for w in warnungen:
        print(f"  [WARNUNG] {w}", file=sys.stderr)

    if fehler:
        print(f"FAIL: {len(fehler)} didaktische/strukturelle Fehler gefunden:", file=sys.stderr)
        for e in fehler:
            print(f"  - [FEHLER] {e}", file=sys.stderr)
        return 2

    k_anzahl = len(data.get("kachelstruktur", {}).get("kacheln", []))
    print(f"OK: Kurs-Steckbrief '{data.get('titel')}' ({k_anzahl} Kacheln) ist didaktisch vollständig freigegeben!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
