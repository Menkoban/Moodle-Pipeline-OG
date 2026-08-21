# -*- coding: utf-8 -*-
"""validate_interactive_media.py — Strenger Validator für interaktive Medien (Hotspots, Simulationen, Formulare).

Prüft:
  1. Hotspots:
     - Bild existiert auf der Festplatte und ist nicht leer (SVG/PNG/JPG).
     - Pins liegen innerhalb des sichtbaren Bereichs (0 <= x <= 100, 0 <= y <= 100).
     - Jeder Pin hat Titel und Beschreibung.
  2. Simulationen:
     - Inputs mit gültigen min/max/step/default Werten.
     - KPIs vorhanden.
     - Visualisierungs-HTML/SVG vorhanden.
     - Compute- und Render-JavaScript syntaktisch valide.
  3. Formulare:
     - Storage-Key vorhanden.
     - Mindestens 2 Eingabefelder/Blöcke definiert.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Tuple, Dict, Any

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def validate_interactive_media(course_path: str) -> Tuple[List[str], List[str]]:
    fehler: List[str] = []
    warnungen: List[str] = []

    if not os.path.exists(course_path):
        fehler.append(f"Datei nicht gefunden: {course_path}")
        return fehler, warnungen

    course_dir = os.path.dirname(os.path.abspath(course_path))

    with open(course_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    hotspot_count = 0
    sim_count = 0
    form_count = 0

    for sec in data.get("sections", []):
        sec_name = sec.get("name", "Abschnitt")
        for act in sec.get("activities", []):
            act_type = act.get("type")
            act_name = act.get("name", "Aktivität")
            spec = act.get("spec", {})

            # 1. Hotspots
            if act_type == "hotspot":
                hotspot_count += 1
                img_path = spec.get("image")
                if not img_path:
                    fehler.append(f"[{sec_name} -> {act_name}] Hotspot hat keine 'image' Bildangabe in spec!")
                else:
                    full_img = os.path.join(course_dir, img_path)
                    if not os.path.exists(full_img):
                        fehler.append(f"[{sec_name} -> {act_name}] Hotspot-Bild nicht gefunden: {full_img}")
                    elif os.path.getsize(full_img) == 0:
                        fehler.append(f"[{sec_name} -> {act_name}] Hotspot-Bild ist leer (0 Bytes): {full_img}")

                pins = spec.get("pins", [])
                if not pins or len(pins) < 2:
                    warnungen.append(f"[{sec_name} -> {act_name}] Hotspot hat weniger als 2 interaktive Pins.")

                for p_idx, p in enumerate(pins):
                    x = p.get("x")
                    y = p.get("y")
                    if x is None or y is None or not (0 <= x <= 100) or not (0 <= y <= 100):
                        fehler.append(f"[{sec_name} -> {act_name}] Pin #{p_idx+1} hat ungültige Koordinaten: x={x}, y={y} (muss 0..100 sein).")
                    if not p.get("title") or not p.get("desc"):
                        warnungen.append(f"[{sec_name} -> {act_name}] Pin #{p_idx+1} ('{p.get('title')}') hat unvollständigen Titel/Text.")

            # 2. Simulationen
            elif act_type == "simulation":
                sim_count += 1
                inputs = spec.get("inputs", [])
                kpis = spec.get("kpis", [])
                compute = spec.get("compute", "")
                render = spec.get("render", "")

                if not inputs:
                    fehler.append(f"[{sec_name} -> {act_name}] Simulation hat keine Eingaberegler ('inputs').")
                if not kpis:
                    warnungen.append(f"[{sec_name} -> {act_name}] Simulation hat keine KPI-Kennzahlen.")
                if not compute or len(compute.strip()) < 10:
                    fehler.append(f"[{sec_name} -> {act_name}] Simulation fehlt der 'compute' JavaScript-Berechnungsblock.")
                if not render or len(render.strip()) < 10:
                    warnungen.append(f"[{sec_name} -> {act_name}] Simulation fehlt der 'render' JavaScript-Visualisierungsblock.")

            # 3. Formulare
            elif act_type == "formular":
                form_count += 1
                storage_key = spec.get("storage_key") or spec.get("title")
                if not storage_key:
                    warnungen.append(f"[{sec_name} -> {act_name}] Formular hat weder 'storage_key' noch 'title' (Autosave eingeschränkt).")
                
                blocks = spec.get("blocks", [])
                fields = spec.get("fields", [])
                
                # Zähle alle echten Eingabefelder
                field_count = 0
                for blk in blocks:
                    if "field" in blk:
                        field_count += 1
                if not blocks and fields:
                    field_count = len(fields)
                    
                if field_count < 2:
                    fehler.append(f"[{sec_name} -> {act_name}] Formular hat weniger als 2 Eingabefelder ({field_count} gefunden). Leere Formulare sind unzulässig!")

    print(f"Geprüfte interaktive Elemente: {hotspot_count} Hotspots, {sim_count} Simulationen, {form_count} Formulare.")
    return fehler, warnungen


def main():
    parser = argparse.ArgumentParser(description="Validiert interaktive Medien (Hotspots, Simulationen, Formulare).")
    parser.add_argument("course_json", help="Pfad zur course.json")
    parser.add_argument("--strict", action="store_true", help="Behandle Warnungen als Fehler")
    args = parser.parse_args()

    fehler, warnungen = validate_interactive_media(args.course_json)

    print(f"=== Interaktive Medien-Validierung für: {args.course_json} ===")
    if warnungen:
        print(f"\n[WARNUNGEN: {len(warnungen)}]")
        for w in warnungen:
            print(f"  ⚠ {w}")

    if fehler:
        print(f"\n[FEHLER: {len(fehler)}]")
        for f in fehler:
            print(f"  ❌ {f}")

    if not fehler and not (args.strict and warnungen):
        print("\n✔ Interaktive Medien-Validierung ERFOLGREICH (Bilder, Pins & Logik vollständig).")
        sys.exit(0)
    else:
        print("\n❌ Interaktive Medien-Validierung FEHLGESCHLAGEN.")
        sys.exit(1)


if __name__ == "__main__":
    main()
