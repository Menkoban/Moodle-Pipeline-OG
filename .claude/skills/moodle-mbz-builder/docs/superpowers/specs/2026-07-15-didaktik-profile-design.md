# Spec — Didaktik-Profile austauschbar (O4)

**Datum:** 2026-07-15
**Skill:** `moodle-mbz-builder`
**Strang:** O4 von ~6 (siehe „Geparkte Stränge" der Schwester-Specs)
**Status:** Design + additiver Scaffold (Registry + Tests) umgesetzt; volle
Verdrahtung offen

## Kontext & Motivation

Das didaktische Konzept des Skills ist heute **fest auf ein einziges Modell
verdrahtet**: das Rode/ZDQ-5-Ebenen-Modell mit einer festen Pflicht-Sequenz der
Lernabschnitte. Wer den Skill für ein anderes didaktisches Konzept nutzen will
(z. B. die vollständige Handlung als sichtbares Gliederungsprinzip statt nur als
Rationale), muss die Guidance-Dateien umschreiben.

Ziel dieses Strangs: das didaktische Konzept zu einem **auswählbaren Profil**
machen — eine Registry benannter Profile, jedes mit eigener Abschnitts-Sequenz
und Regel-Zusammenfassung, im Briefing wählbar, **Default = Rode** (100 %
verhaltensgleich zu heute).

Diese Stufe ist **rein additiv**: Registry-Modul + Spec + Tests. Die Ausgabe
generierter Kurse ändert sich **nicht**; die Verdrahtung in Briefing/Authoring/
Validierung ist als Migrationspfad beschrieben, aber noch nicht ausgeführt.

## Wo das Rode-Konzept heute „hard-coded" ist

Der entscheidende Befund: Die Sequenz und die Regeln sind fast vollständig
**Autoren-Guidance auf Prompt-Ebene** (vom Modell beim Schreiben der Kurs-JSON
befolgt), **nicht** in den Bau-Skripten erzwungen. Das macht diesen Umbau
code-seitig risikoarm.

**A · Prompt/Doku-Ebene (das eigentliche „Gehirn" — die Kopplung):**

- `references/course-design.md`
  - §2 „Das 5-Ebenen-Strukturmodell (Wording)" — das Leitmodell (Rode).
  - §3 „Pflicht-Sequenz der Lernabschnitte" — die verbindliche Tabelle
    (Index 0 „Über dieses Modul", dann 1 Einführung → 2 Grundlagen →
    3 Vertiefung → 4 Anwendung/Handlungsprodukt → 5 Kurs-Recap → 6 Glossar →
    7 Material für Lehrkräfte, mit Zeitbudgets + `visible:0` für Lehrkräfte).
  - §1/§4–§10 — Leitprinzipien, Infoblatt-Bauplan, Mengen-Kalibrierung
    (~25 Wörter/Lernminute), Qualitäts-Checkliste. Alles Rode-spezifische Regeln.
- `SKILL.md`
  - Schritt 3 „Follow the fixed Lernabschnitt sequence: Einführung → Grundlagen
    → Vertiefung → Anwendung/Handlungsprodukt → Kurs-Recap → Glossar → Material
    für Lehrkräfte".
  - Intake (Schritt 1) + Vorschlags-Steckbrief: „Die Pflicht-Sequenz unten
    bleibt das Gerüst" — die Kachelzahl-Frage teilt die feste Sequenz nur feiner.
  - `quality_check` (b): „Pflicht-Sequenz vollständig (Einführung / Vertiefung /
    Anwendung / Recap)".
  - „Reference files" verweist auf „the fixed Lernabschnitt sequence".

**B · Code-Ebene (nur beiläufige Namens-Kopplungen, keine Sequenz-Erzwingung):**

- `scripts/build_mbz.py`, `scripts/preview_mbz.py`, `scripts/validate_mbz.py`
  sind **sequenz-agnostisch** — sie verarbeiten die Sektionen so, wie sie in der
  Kurs-JSON stehen. (`validate_mbz.py` prüft nur die Moodle-cmid-`sequence`, also
  Modul-Reihenfolge, nicht die didaktische Abschnittsfolge.)
- `scripts/make_materials.py` findet/erzeugt die verborgene Sektion über den
  **fixen Namen** `"Material für Lehrkräfte"` (`visible:0`) — die einzige echte
  Code-Kopplung an einen Rode-Abschnittsnamen.
- `scripts/set_recap_video.py` / `scripts/check_delivery.py` finden den
  Video-Recap-Platzhalter über den Aktivitäts-**Namen** (enthält „video"/
  „zusammenfassung") — an den Recap-Abschnitt gebunden, aber namens-, nicht
  sequenz-basiert.

**Konsequenz:** „Profile austauschbar" ist primär eine **Registry- + Prompt-**
Änderung. Die Bau-Pipeline muss dafür kaum angefasst werden.

## Registry-Architektur

### Modul `scripts/didactic_profiles.py` (dieser Scaffold)

Eine reine Datenquelle, an **keiner** Stelle in die Generierung verdrahtet:

- `PROFILES: dict[str, profile]` — Registry, Key → Profil.
- `DEFAULT_PROFILE_KEY = "rode"`.
- Profil-Form `{key, name, beschreibung, intro_section, section_sequence,
  rules}`:
  - `section_sequence`: Liste von Abschnitten
    `{key, title, zeit, visible, pflicht}` — die 7 nummerierten Lernabschnitte;
    `intro_section` hält den Index-0-Wrapper „Über dieses Modul" separat, damit
    die Sequenz exakt der dokumentierten Pflicht-Sequenz entspricht.
  - `rules`: verdichtete Regel-Zusammenfassung (`leitprinzipien`,
    `didaktische_begruendung`, `constructive_alignment`, `pflicht_abschnitte`,
    `wortbudget`, `quelle`).
- Accessoren:
  - `get_profile(key="rode")` → **tiefe Kopie** des Profils (Registry bleibt
    unveränderlich; echo des „deep-frozen"-Musters der Client-Registries);
    unbekannter Key → `ValueError` mit verfügbaren Keys.
  - `list_profiles()` → `[(key, name), …]`, Default zuerst.
  - `section_titles(key)` → Titel der Sequenz (Convenience für Briefing/Tests).

**Enthaltene Profile:**

1. `rode` (Default) — bildet die heutige Pflicht-Sequenz + Regeln 1:1 ab.
2. `vollstaendige-handlung` (Stub, `"stub": True`) — Beispiel-Alternative: die
   sechs Phasen der vollständigen Handlung (Informieren → Planen → Entscheiden →
   Ausführen → Kontrollieren → Bewerten) werden selbst zur Abschnitts-Sequenz.
   Bewusst nur ein Stub (Sequenz + Regel-Skizze), um die Austauschbarkeit zu
   demonstrieren, ohne ein zweites vollständiges didaktisches Modell auszuformen.

### Warum eine Datenstruktur (keine zweite Prompt-Datei pro Profil, jetzt)

Die Sequenz als **Daten** kann sowohl der Mensch (Briefing-Menü) als auch die
spätere Verdrahtung (Steckbrief-Generierung, `quality_check`) konsumieren, ohne
Prosa zu parsen. Profil-spezifische *ausführliche* Guidance (der Infoblatt-Bauplan
etc.) bleibt in `references/` und wird in der vollen Implementierung profil-
parametrisch (siehe unten) — die Registry hält den **strukturellen Kern**
(Reihenfolge, Sichtbarkeit, Pflicht-Flags, Regel-Kurzfassung).

## Wie ein Profil ins Briefing kommt (Migrationspfad — noch nicht umgesetzt)

1. **Briefing-Frage** (`SKILL.md` Schritt 1, Intake): eine neue Auswahlfrage
   „Didaktik-Profil?" — Optionen aus `list_profiles()`, `rode (empfohlen)` als
   Default. Wird i. d. R. übersprungen (sicherer Default), nur bei Bedarf gefragt.
2. **Persistenz in der Kurs-JSON:** neues optionales Feld
   `course.didaktik_profil` (Default `"rode"` bei Abwesenheit) — voll
   rückwärtskompatibel; alte Kurs-JSONs verhalten sich unverändert wie Rode.
3. **Fluss ins Authoring:** der Vorschlags-Steckbrief (benannte Kacheln) wird aus
   `get_profile(key)["section_sequence"]` vorbelegt statt aus der fest
   verdrahteten Sequenz. Die Kachelzahl-Frage verfeinert weiterhin nur innerhalb
   der Profil-Sequenz.
4. **Fluss in die Validierung:** `quality_check` (b) liest die Pflicht-Sequenz aus
   dem aktiven Profil (`rules["pflicht_abschnitte"]`) statt der hartkodierten
   Liste „Einführung / Vertiefung / Anwendung / Recap".

## Welche Dateien eine VOLLE Implementierung ändern würde

| Datei | Änderung | Risiko |
|---|---|---|
| `SKILL.md` | Intake-Frage „Didaktik-Profil"; Schritt 3 + `quality_check` (b) auf „aktives Profil" statt fixe Sequenz umformulieren; Reference-files-Hinweis | mittel (Prompt) |
| `references/course-design.md` | §2/§3 profil-parametrisch rahmen (Rode als Default-Kapitel; alternative Profile in eigenen Abschnitten/Dateien); Sequenz-Tabelle als „des jeweiligen Profils" | mittel (Prompt) |
| `scripts/didactic_profiles.py` | Ausbau des 2. Profils vom Stub zum vollen Modell; ggf. `reference`-Feld pro Profil | niedrig |
| `scripts/make_materials.py` | Lehrkräfte-Sektionsnamen aus dem aktiven Profil beziehen statt Literal `"Material für Lehrkräfte"` | niedrig (1 Stelle) |
| `scripts/build_editor_widget.py` | `quality_check`-Aktion profil-bewusst (Sequenz-Vollständigkeit gegen aktives Profil) | niedrig |
| (optional) `scripts/validate_mbz.py` | beratende Warnung, wenn Sektionen stark von der Profil-Sequenz abweichen — nur wenn gewünscht; heute bewusst agnostisch | niedrig |

**Migrations-/Kompatibilitätsgarantie:** Fehlt `course.didaktik_profil`, greift
`DEFAULT_PROFILE_KEY = "rode"` → identisches Verhalten. Kein Bestandskurs und
kein bestehender Testlauf ändert sich.

## Nicht-Ziele

- **Keine** Änderung an generierter Kurs-Ausgabe in dieser Stufe (rein additiv).
- **Kein** Verdrahten der Registry in Briefing/Authoring/Validierung (Migrations-
  pfad oben; separat umzusetzen).
- **Kein** zweites voll ausgearbeitetes didaktisches Modell — der zweite Eintrag
  ist bewusst ein Stub.
- **Keine** Bearbeitung von `SKILL.md` oder `references/course-design.md` (Shared
  Files; werden separat integriert).

## Tests (`tests/test_didactic_profiles.py`)

- Registry lädt; jedes Profil trägt die Pflicht-Felder.
- `get_profile()` (und `get_profile(None)`) defaulten auf `rode`.
- `rode`s Sequenz == dokumentierte Pflicht-Sequenz (Einführung … Material für
  Lehrkräfte); Lehrkräfte-Sektion `visible:0`.
- Zweites Profil existiert und unterscheidet sich klar (andere Sequenz).
- Unbekannter Key → `ValueError`; `get_profile` liefert eine Kopie (Registry
  bleibt nach Mutation der Rückgabe intakt).

## Akzeptanz

- Volle Test-Suite grün (`python -m pytest tests/ -q`).
- Default-Ausgabe unverändert: kein Bau-Skript importiert `didactic_profiles`;
  die Registry ist reine, nicht verdrahtete Datenquelle.

## Volle Verdrahtung — UMGESETZT (2026-07-15)

Entscheidungen (Autor-Input): Default = **Rode** (Handlungssituation am Anfang,
Recap am Ende); die Auswahl wird im Briefing **IMMER** angeboten, auch bei nur
einem Profil (Anzahl ≥ 1); Skill-Split pro Konzept ist ein **Zukunfts**-Ziel
(jetzt nur vorbereiten, nicht umsetzen).

Umgesetzt (rein Prompt-/Doku-Ebene — Bau-Skripte bleiben sequenz-agnostisch,
Default `rode` = byte-identische Ausgabe):
- **SKILL.md Schritt 1:** neue Pflicht-Briefing-Frage „Didaktisches Konzept
  (IMMER fragen — auch bei nur einem Profil)" → Profile via
  `python scripts/didactic_profiles.py`, Persistenz in `course.didaktik_profil`
  (Default `"rode"`).
- **SKILL.md Schritt 3:** „Follow the section sequence of the CHOSEN didactic
  profile" statt fester Rode-Sequenz; `rode` = unveränderte Sequenz.
- **SKILL.md `quality_check` (b):** prüft die Pflicht-Sequenz des aktiven Profils.
- **course-design.md §3:** als profil-parametrisch gekennzeichnet (Tabelle = `rode`).
- **`make_materials.py`:** unverändert nötig — findet die Lehrkraft-Sektion bereits
  über `visible:0`, nicht über den Namen (profil-agnostisch).
- **Split-Bereitschaft:** je Profil `guidance_ref` (Rode → `course-design.md`
  Kap. 1–7; Stub → offen). So lässt sich ein Profil samt Leitfaden später zu
  einem eigenständigen Konzept-Skill herauslösen; der kombinierte Skill behält
  die Auswahl über ALLE Profile.

## Geparkt / Folge

- **Skill-Split pro Konzept** (Zukunft): ein Profil + `guidance_ref`-Doku zu einem
  eigenständigen Skill herauslösen (nur vorbereitet, nicht umgesetzt).
- 2. Profil (`vollstaendige-handlung`) vom Stub zum vollen Modell ausbauen (inkl.
  eigener `references/`-Guidance).
