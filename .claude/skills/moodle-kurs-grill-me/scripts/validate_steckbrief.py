#!/usr/bin/env python3
"""Validiert einen Moodle-Kurs-Steckbrief (kurs-steckbrief.json) auf didaktische Vollständigkeit.

Prüft alle 6 Cluster:
  1. Curriculum & Lerngruppe
  2. Handlungssituation & Handlungsprodukt
  3. Fachlichkeit & Normen (Musterrechnung, Formeln)
  4. Aufgabenkaskade (Erkundung, Formular-Protokoll, Praxisauftrag)
  5. Medien & Simulation (Simulationsmodell, Schaltpläne)
  6. Kachelstruktur & Foto-Motive
"""

import json
import sys
import os

REQUIRED_KEYS = [
    "titel",
    "shortname",
    "curriculum",
    "handlungssituation",
    "fachlichkeit",
    "aufgaben_kaskade",
    "medien_simulation",
    "kachelstruktur"
]

def validate_steckbrief(file_path):
    if not os.path.exists(file_path):
        print(f"Error: Datei '{file_path}' existiert nicht.", file=sys.stderr)
        return False

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Ungültiges JSON-Format: {e}", file=sys.stderr)
        return False

    errors = []

    # 1. Root-Keys
    for k in REQUIRED_KEYS:
        if k not in data:
            errors.append(f"Fehlender Hauptschlüssel: '{k}'")

    # 1b. E-Learning-Format & Didaktische Methoden
    if not data.get("elearning_format"):
        errors.append("Fehlende Angabe: 'elearning_format' (z.B. blended_learning, flipped_classroom, scenario_based_pbl)")
    if not data.get("didaktische_methoden") or len(data.get("didaktische_methoden", [])) == 0:
        errors.append("Fehlende Angabe: 'didaktische_methoden' (mindestens 1–2 Methoden angeben)")

    # 2. Cluster 1: Curriculum
    curr = data.get("curriculum", {})
    for ck in ["beruf", "ausbildungsjahr", "lernfeld"]:
        if not curr.get(ck):
            errors.append(f"Cluster 1 (Curriculum): Fehlende Angabe '{ck}'")

    # 3. Cluster 2: Handlungssituation
    hs = data.get("handlungssituation", {})
    for hk in ["betrieb", "problem", "leitfrage", "handlungsprodukt"]:
        if not hs.get(hk):
            errors.append(f"Cluster 2 (Handlungssituation): Fehlende Angabe '{hk}'")

    # 4. Cluster 3: Fachlichkeit
    fach = data.get("fachlichkeit", {})
    for fk in ["begriffe", "formeln", "normen"]:
        if not fach.get(fk):
            errors.append(f"Cluster 3 (Fachlichkeit): Fehlende Liste '{fk}'")

    # 5. Cluster 4: Aufgabenkaskade
    aufg = data.get("aufgaben_kaskade", {})
    if not aufg.get("grundlagen_erkundung"):
        errors.append("Cluster 4 (Aufgaben): 'grundlagen_erkundung' fehlt")
    if not aufg.get("vertiefung_formular"):
        errors.append("Cluster 4 (Aufgaben): 'vertiefung_formular' fehlt (ausfüllbares Protokoll)")
    if not aufg.get("anwendung_praxisauftrag"):
        errors.append("Cluster 4 (Aufgaben): 'anwendung_praxisauftrag' fehlt (vollständige Handlung)")

    # 6. Cluster 5: Medien & Simulation
    med = data.get("medien_simulation", {})
    if med.get("hat_simulation") and not med.get("simulation"):
        errors.append("Cluster 5 (Simulation): 'hat_simulation' ist true, aber 'simulation'-Objekt fehlt")

    # 7. Cluster 6: Kachelstruktur
    ks = data.get("kachelstruktur", {})
    kacheln = ks.get("kacheln", [])
    if not kacheln or len(kacheln) < 3:
        errors.append("Cluster 6 (Kachelstruktur): Mindestens 3 Kacheln erforderlich")
    for i, kc in enumerate(kacheln):
        if not kc.get("titel"):
            errors.append(f"Cluster 6 (Kachelstruktur): Kachel {i+1} hat keinen Titel")
        if not kc.get("kachelfoto_motiv"):
            errors.append(f"Cluster 6 (Kachelstruktur): Kachel {i+1} ('{kc.get('titel')}') hat kein 'kachelfoto_motiv'")

    if errors:
        print(f"FAIL: {len(errors)} didaktische Unvollständigkeit(en) gefunden:")
        for err in errors:
            print(f"  - {err}")
        return False

    print(f"OK: Kurs-Steckbrief '{data.get('titel')}' ({len(kacheln)} Kacheln) ist vollständig und freigabereif!")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_steckbrief.py <path_to_steckbrief.json>")
        sys.exit(1)

    ok = validate_steckbrief(sys.argv[1])
    sys.exit(0 if ok else 1)
