# moodle-kurs-grill-me 🎯📋

[![Gate 0](https://img.shields.io/badge/Pipeline-Gate%200-blue.svg)](README.md)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Interaktives didaktisches Alignment-Interview („Grill-Me“) für berufliche, mathematische und technische Moodle-Kurse.**

Dieser Skill fungiert als **verbindliches Gate 0 (Didaktik-Gate)** der gesamten Moodle-Kurs-Pipeline. Bevor eine einzige Zeile Kurs-Code geschrieben oder eine Kurssicherung gebaut wird, führt der Skill ein tiefgehendes, adaptives Befragungs-Interview in **8 didaktischen Clustern** mit dem Kursautor durch. Das Ergebnis ist ein vollständig spezifizierter, schema-validierter **Kurs-Steckbrief** (`kurs-steckbrief.json`), der als unverrückbare Bauanleitung für `moodle-mbz-builder` dient.

---

## 🌟 Kern-Prinzipien & Features

- ❓ **Strikter Interview-Vertrag (Sequenziell & Interaktiv):**
  - Genau **eine Frage zur Zeit** über das interaktive `ask_question`-Tool mit 5 konkreten Optionen und `(Empfohlen)` an erster Stelle.
  - **Verbot von One-Shot-Vorausfüllung:** Keine unaufgeforderten Block-Tabellen oder eigenmächtigen Vorab-Generierungen — der Kursautor behält die volle didaktische Hoheit.
- 📚 **Automatisches KMK- & CuVo-Retrieval (`fetch_curriculum.py`):**
  - Automatisierte Extraktion von Ausbildungsberufen, Lernfeldern, Handlungsphasen, Normen und Fachbegriffen aus der integrierten Lehrplan-Datenbank.
- 📥 **Inbox-Primat & Material-Ingestion (`ingest_material.py`):**
  - Automatisierte Extraktion und Übernahme bestehender Lehrkraft-Materialien (PDF, DOCX, Skripte, Aufgabenblätter). Reale Aufgaben haben stets Vorrang vor generischen MC-Fragen.
- 🔗 **Continuous Narrative Architecture:**
  - Sicherstellung eines durchgehenden roten Fadens: Jede Kachel ist eine handlungsorientierte Etappe zur Lösung desselben authentischen Gesamtauftrags.
- 📐 **MINT- & Mathematik-Standards:**
  - Standardisierte Kompetenzformeln (*„Die Schülerinnen und Schüler sind in der Lage...“*), Spoiler-Verbot in der Ausgangssituation und mathematische Formelqualität.

---

## 🧩 Die 8 didaktischen Cluster

| Cluster | Thema | Didaktischer Schwerpunkt |
|---|---|---|
| **1.1 – 1.3** | **Curriculares Profil & Lerngruppe** | Präziser Ausbildungsberuf / Schulform, Lernfeld, Vorwissen, Heterogenität, Sprachförderung (DaZ). |
| **2.1 – 2.2** | **Handlungssituation & Continuous Narrative** | Authentischer betrieblicher Auftrag, Schadensfall, messbares Handlungsprodukt, roter Faden über alle Kacheln. |
| **3.1 – 3.2** | **Fachinhalte, Normen & Formeln** | Fachbegriffe, 5-Punkte-Musterrechnungen, DIN/ISO/VDE/DGUV-Normen, 5 Sicherheitsregeln. |
| **4.1 – 4.2** | **E-Learning-Format & Fachmethoden** | Blended Learning, Flipped Classroom, Szenariolernen, Auswahl aus 35 Fachmethoden via `method_recommender.py`. |
| **5.1 – 5.3** | **Lernziel- & Aufgaben-Architektur** | Standard-Lernziele mit Lehrerduplikat, echte Aufgabenblätter mit nachgelagerten `assign`-Abgaben. |
| **6.1 – 6.3** | **Interaktive Medien-Trias** | Feindefinition von Hotspot-Labor (`hotspot`), Schieberegler-Canvas (`simulation`) und Digitalprotokoll (`formular`). |
| **7.1 – 7.2** | **Kachelstruktur & Transfer** | ZDQ-5-Ebenen-Phasen, Zeitbudgets, SPC-/Toleranz-Transfer für Leistungsstarke. |
| **8.1 – 8.3** | **Cover-Design & Lehrer-Paket** | Textfreie Cover in der Unten-Rechts-Safe-Zone ($y=45\dots85\%$), 5-Fallen-Leitfaden, Musterlösungen. |

---

## 💻 Installation & Setup

**Antigravity / Gemini CLI:**
```powershell
# Windows (PowerShell)
git clone https://github.com/Menkoban/moodle-kurs-grill-me.git "$HOME\.gemini\config\skills\moodle-kurs-grill-me"
```
```bash
# Linux / macOS
git clone https://github.com/Menkoban/moodle-kurs-grill-me.git ~/.gemini/config/skills/moodle-kurs-grill-me
```

**Claude Code:**
```powershell
git clone https://github.com/Menkoban/moodle-kurs-grill-me.git "$HOME\.claude\skills\moodle-kurs-grill-me"
```

---

## 🚀 Workflow & Steckbrief-Validierung

1. **Interview starten:** Die KI ruft den Skill auf, sobald ein neuer Kursauftrag erteilt wird.
2. **Materialien einlesen (falls vorhanden):**
   ```bash
   python scripts/ingest_material.py pfad/zu/skript.pdf
   ```
3. **Lehrplan abrufen:**
   ```bash
   python scripts/fetch_curriculum.py --beruf "Elektroniker für Betriebstechnik" --lernfeld 4
   ```
4. **Steckbrief validieren (Gate 0 Abschluss):**
   ```bash
   python scripts/validate_steckbrief.py kurs-steckbrief.json
   ```
   *Erst bei erfolgreicher Validierung (Exit 0) wird an `moodle-mbz-builder` übergeben!*

---

## 📄 Lizenz

Dieses Projekt ist unter der **MIT-Lizenz** lizenziert.
