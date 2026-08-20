#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_curriculum_engine.py — Umfassende Test-Suite für das Curricula-Retrieval & Parsing-Ökosystem.

Testet:
  1. curriculum_parser.py: Header-Parsing, Zeitrichtwert, Phasen der vollständigen Handlung,
     Mindestinhalte, Normen-Extraktion.
  2. fetch_curriculum.py: Cache-Lookup, Lernfeld-Isolation, Multi-Lernfeld-Übersicht,
     Fehlerbehandlung (Domain-Whitelist, Cache-Miss).
  3. validate_steckbrief.py: Curriculare Validierung des Steckbriefs.
"""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

# Pfade
SKILL_DIR = Path(__file__).resolve().parent.parent
SHARED_DIR = SKILL_DIR.parent / "shared"
sys.path.insert(0, str(SHARED_DIR))
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from curriculum_parser import (
    clean_text, clean_title, parse_lernfeld_header,
    extract_action_phases, extract_norms, extract_mindestinhalte,
    parse_lernfeld_full, parse_all_lernfelder_from_document
)


class TestCurriculumParser(unittest.TestCase):
    """Testet die semantische Analyse von Lernfeld-Texten."""

    def setUp(self):
        self.sample_lf_text = """
Lernfeld 3: Steuerungen und Regelungen analysie- 1. Ausbildungsjahr
ren und realisieren Zeitrichtwert: 80 Stunden

Die Schülerinnen und Schüler verfügen über die Kompetenz, Steuerungen und Regelungen zu analysieren und zu realisieren.
Die Schülerinnen und Schüler analysieren Anlagen und Geräte gemäß Kundenaufträgen und visualisieren deren strukturellen Aufbau sowie die funktionalen Zusammenhänge (Blockschaltbild, EVA-Prinzip, Sensoren, Aktoren, Schnittstellen, logische Grundverknüpfungen).
Dazu werten sie Dokumentationen aus, bei fremdsprachigen auch unter Nutzung von Hilfsmitteln.
Die Schülerinnen und Schüler planen Steuerungen und Regelungen nach Kundenvorgaben (Wirkungskette, Funktionsbeschreibungen, Speicherfunktionen).
Die Schülerinnen und Schüler unterscheiden zwischen Steuerungs- und Regelungsprozessen (verbindungs- und speicherprogrammierte Signalverarbeitung). Sie vergleichen Techniken zur Realisierung von Steuerungen und Regelungen, bewerten deren Vor- und Nachteile auch unter ökonomischen, ökologischen und sicherheitstechnischen Aspekten und entscheiden sich auftragsbasiert, auch im Team, für eine der Varianten.
Die Schülerinnen und Schüler realisieren Steuerungen sowie Regelungen und führen Änderungen und Anpassungen unter Beachtung geltender Normen nach DIN EN 60617 und DIN VDE 0100-600 durch. Dazu wählen sie Baugruppen und deren Komponenten nach Kundenanforderungen aus. Sie nehmen die Systeme in Betrieb und erfassen messtechnisch deren Betriebswerte unter Beachtung der 5 Sicherheitsregeln.
Sie dokumentieren die technische Umsetzung unter Nutzung von Standardsoftware (Technische Dokumentationen).
Die Schülerinnen und Schüler prüfen die Funktionsfähigkeit der Steuerungen und Regelungen und nehmen notwendige Einstellungen vor.
Sie analysieren, reflektieren und bewerten, auch im Team, die im Arbeitsprozess gewonnenen Erkenntnisse hinsichtlich einer Optimierung zukünftiger Vorgehensweisen.
"""

    def test_clean_text_and_title(self):
        cleaned = clean_text("analysie-\nren und realisie- ren")
        self.assertIn("analysieren", cleaned)
        self.assertIn("realisieren", cleaned)

        raw_title = "Steuerungen und Regelungen analysieren 1. Ausbildungsjahr Zeitrichtwert: 80 Ustd."
        cleaned_title = clean_title(raw_title)
        self.assertEqual(cleaned_title, "Steuerungen und Regelungen analysieren")

    def test_parse_lernfeld_header(self):
        header = parse_lernfeld_header(self.sample_lf_text)
        self.assertEqual(header["nr"], 3)
        self.assertEqual(header["zeitrichtwert_ustd"], 80)
        self.assertEqual(header["ausbildungsjahr"], 1)
        self.assertIn("Steuerungen und Regelungen", header["titel"])

    def test_extract_norms(self):
        norms = extract_norms(self.sample_lf_text)
        self.assertIn("DIN EN 60617", norms)
        self.assertIn("DIN VDE 0100-600", norms)
        self.assertIn("5 Sicherheitsregeln", norms)

    def test_extract_mindestinhalte(self):
        inhalte = extract_mindestinhalte(self.sample_lf_text)
        self.assertIn("Blockschaltbild", inhalte)
        self.assertIn("EVA-Prinzip", inhalte)
        self.assertIn("Sensoren", inhalte)
        self.assertIn("Aktoren", inhalte)
        self.assertIn("Wirkungskette", inhalte)

    def test_extract_action_phases(self):
        phases = extract_action_phases(self.sample_lf_text)
        self.assertTrue(len(phases["informieren"]) > 0, "Phase 'informieren' sollte Sätze enthalten")
        self.assertTrue(len(phases["planen"]) > 0, "Phase 'planen' sollte Sätze enthalten")
        self.assertTrue(len(phases["entscheiden"]) > 0, "Phase 'entscheiden' sollte Sätze enthalten")
        self.assertTrue(len(phases["ausfuehren"]) > 0, "Phase 'ausfuehren' sollte Sätze enthalten")
        self.assertTrue(len(phases["kontrollieren"]) > 0, "Phase 'kontrollieren' sollte Sätze enthalten")
        self.assertTrue(len(phases["bewerten"]) > 0, "Phase 'bewerten' sollte Sätze enthalten")

    def test_parse_lernfeld_full(self):
        res = parse_lernfeld_full(self.sample_lf_text)
        self.assertEqual(res["lernfeld_nr"], 3)
        self.assertEqual(res["zeitrichtwert_ustd"], 80)
        self.assertEqual(res["ausbildungsjahr"], 1)
        self.assertTrue(len(res["mindestinhalte"]) >= 5)
        self.assertTrue(len(res["normen"]) >= 2)


class TestFetchCurriculumCLI(unittest.TestCase):
    """Testet das CLI-Skript fetch_curriculum.py."""

    def test_cache_miss_exit_code(self):
        script = SKILL_DIR / "scripts" / "fetch_curriculum.py"
        res = subprocess.run(
            [sys.executable, str(script), "--beruf", "UnbekannterNichtExistierenderBeruf123", "--check-cache"],
            capture_output=True,
            text=True
        )
        self.assertEqual(res.returncode, 5)
        data = json.loads(res.stdout)
        self.assertEqual(data["status"], "cache_miss")

    def test_illegal_domain_rejected(self):
        script = SKILL_DIR / "scripts" / "fetch_curriculum.py"
        res = subprocess.run(
            [sys.executable, str(script), "--beruf", "TestBeruf", "--url", "https://unauthorized-blog.com/test.pdf"],
            capture_output=True,
            text=True
        )
        self.assertEqual(res.returncode, 2)
        data = json.loads(res.stdout)
        self.assertIn("nicht_zulaessig", data["status"])

    def test_cached_elektroniker_lookup(self):
        script = SKILL_DIR / "scripts" / "fetch_curriculum.py"
        res = subprocess.run(
            [sys.executable, str(script), "--beruf", "Elektroniker", "--lernfeld", "3", "--check-cache"],
            capture_output=True,
            text=True
        )
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["ausgewaehltes_lernfeld"]["lernfeld_nr"], 3)
        self.assertEqual(data["ausgewaehltes_lernfeld"]["zeitrichtwert_ustd"], 80)


class TestSteckbriefValidation(unittest.TestCase):
    """Testet die Validierung des Kurs-Steckbriefs."""

    def test_valid_example_steckbrief(self):
        script = SKILL_DIR / "scripts" / "validate_steckbrief.py"
        steckbrief = SKILL_DIR / "assets" / "beispiel_wendeschuetz_steckbrief.json"
        res = subprocess.run(
            [sys.executable, str(script), str(steckbrief)],
            capture_output=True,
            text=True
        )
        self.assertEqual(res.returncode, 0, f"Validierung fehlgeschlagen: {res.stderr}\n{res.stdout}")
        self.assertIn("vollständig freigegeben", res.stdout)


if __name__ == "__main__":
    unittest.main()
