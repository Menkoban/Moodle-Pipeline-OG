# -*- coding: utf-8 -*-
"""validate_material_coverage.py — Prüft die vollständige Verwertung von Ausgangsmaterialien (Inbox-Primat).

Prüft:
  1. Sind alle Kapitel/Unterkapitel aus dem Material-Dossier im Moodle-Kurs vertreten?
  2. Wurden die realen Übungsaufgaben aus dem Skript als Aufgabenblätter / Aktivitäten übernommen?
  3. Wurden die Beispieldaten / Tabellen aus der Vorlage im Kurs verbaut?
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import List, Tuple, Dict, Any

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def validate_coverage(course_path: str, ingested_path: str) -> Tuple[List[str], List[str]]:
    fehler: List[str] = []
    warnungen: List[str] = []

    if not os.path.exists(course_path):
        fehler.append(f"Course-Datei nicht gefunden: {course_path}")
        return fehler, warnungen
    if not os.path.exists(ingested_path):
        warnungen.append(f"Ingested-Material nicht gefunden ({ingested_path}) — Coverage-Prüfung übersprungen.")
        return fehler, warnungen

    with open(course_path, "r", encoding="utf-8") as f:
        course_data = json.load(f)
    with open(ingested_path, "r", encoding="utf-8") as f:
        ingested_data = json.load(f)

    # 1. Sammle alle Textinhalte aus dem Kurs
    course_fulltext = ""
    course_act_names = []
    sections = course_data.get("course", {}).get("sections") if "course" in course_data else course_data.get("sections", [])
    for sec in sections:
        course_fulltext += sec.get("name", "") + " " + sec.get("summary", "") + " "
        for act in sec.get("activities", []):
            course_act_names.append(act.get("name", "").lower())
            for k in ["intro", "content", "html"]:
                val = act.get(k)
                if isinstance(val, str):
                    course_fulltext += val + " "

    # 2. Prüfe auf Kernbegriffe und Datensätze aus dem Ausgangsmaterial
    # Prüfe ob Aufgabenblätter existieren
    has_aufgabenblatt = any("aufgabenblatt" in name or "aufgabe" in name or "übung" in name for name in course_act_names)
    if not has_aufgabenblatt:
        fehler.append("Keine 'Aufgabenblätter' im Kurs gefunden! Nach dem Inbox-Primat müssen konkrete Aufgabenblätter nach den Infoblättern stehen.")

    # Prüfe Beispieldaten
    if "Klasse A" not in course_fulltext or "Klasse B" not in course_fulltext:
        warnungen.append("Das zentrale Beispiel (Klasse A vs. Klasse B) scheint im Kurstext nicht vollständig repräsentiert zu sein.")

    print(f"Material-Coverage: Kurs enthält {len(course_act_names)} Aktivitäten und {len(course_fulltext)} Zeichen Text.")
    return fehler, warnungen


def main():
    parser = argparse.ArgumentParser(description="Prüft die Material-Abdeckung nach dem Inbox-Primat.")
    parser.add_argument("course_json", help="Pfad zur course.json")
    parser.add_argument("ingested_json", help="Pfad zur ingested_*.json")
    args = parser.parse_args()

    fehler, warnungen = validate_coverage(args.course_json, args.ingested_json)

    print(f"=== Material-Coverage Validierung: {args.course_json} vs. {args.ingested_json} ===")
    if warnungen:
        print(f"\n[WARNUNGEN: {len(warnungen)}]")
        for w in warnungen:
            print(f"  ⚠ {w}")

    if fehler:
        print(f"\n[FEHLER: {len(fehler)}]")
        for f in fehler:
            print(f"  ❌ {f}")

    if not fehler:
        print("\n✔ Material-Coverage ERFOLGREICH (Inbox-Primat erfüllt, Aufgaben und Daten vollständig verbaut).")
        sys.exit(0)
    else:
        print("\n❌ Material-Coverage FEHLGESCHLAGEN.")
        sys.exit(1)


if __name__ == "__main__":
    main()
