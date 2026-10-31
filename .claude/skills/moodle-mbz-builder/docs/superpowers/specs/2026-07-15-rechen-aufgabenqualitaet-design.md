# Spec — Rechen- & Aufgabenqualität (V5, V6, V7)

**Datum:** 2026-07-15
**Skill:** `moodle-mbz-builder`
**Strang:** 2 von ~6 (siehe [MbZ-Builder-Überarbeitung])
**Status:** Design freigegeben (Autor: „ansonsten gut", 2026-07-15) → Spec zur Durchsicht

## Kontext & Motivation

Kurse sollen fachlich saubere, nachvollziehbare Rechenbeispiele und **echte**
Aufgaben aus realen Situationen enthalten — nicht „hier sind Zahlen, rechne aus".
Heute gibt es dafür **keine** Autorenregel: `references/course-design.md`
behandelt Rechnungen nur indirekt (SVG-Typografie: hochgestellte Einheiten,
tiefgestellte Indizes). Es fehlen drei Dinge:

- **V5 — Rechenbeispiel-Struktur:** geg/ges → Formel → Einsetzen → Ergebnis, mit
  Einheiten, Schritt für Schritt nachvollziehbar.
- **V6 — Echte Aufgaben:** in eine reale Handlungssituation eingebettet.
- **V7 — Einheiten mitführen:** jede Größe trägt in jeder Zeile ihre Einheit.

**Durchsetzung (vom Autor gewählt: „Beides kombiniert"):** Autorenregel +
KI-`quality_check` + weiche Heuristik-Warnung.

## Ziele / Nicht-Ziele

**Ziele**
- Verbindliches Rechenbeispiel-Muster + Aufgaben-/Einheiten-Regeln in
  `course-design.md`.
- Drei neue `quality_check`-Prüfpunkte in `SKILL.md` (Widget-Aktion).
- Eine **konservative, nicht-fatale** Heuristik in `validate_mbz.py`, die eine
  wahrscheinliche Rechnung ohne Einheit meldet.

**Nicht-Ziele**
- **V2 Bruchdarstellung** (echter Bruchstrich statt Slash) — eigener Strang 3;
  Grund: der PDF-Pfad (`make_materials.py` → ReportLab) rendert weder MathJax
  noch CSS-Brüche, das braucht eine eigene Rendering-Entscheidung. In diesem
  Strang bleibt Division als Slash (`U/I`).
- Harte, gate-blockierende Inhaltsprüfung (semantischer Text ist zu fehlalarm-
  anfällig für ein `--strict`-Gate; die Heuristik bleibt beratend).

## 1 · Autorenregeln (`references/course-design.md`)

Neuer Abschnitt **„Rechenbeispiele & Aufgaben"** mit:

**V5 — Rechenbeispiel-Bauplan (kopierbares HTML-Muster):**
```html
<div class="rechenbeispiel">
  <h4>Rechenbeispiel: <Titel></h4>
  <p><b>Situation:</b> <realer Kontext + konkrete Frage></p>
  <p><b>Gegeben:</b> <Größe = Wert Einheit; …></p>
  <p><b>Gesucht:</b> <Größe in Einheit></p>
  <p><b>Formel:</b> <symbolische Formel></p>
  <p><b>Einsetzen:</b> <Werte mit Einheiten eingesetzt></p>
  <p><b>Ergebnis:</b> <Wert Einheit></p>
</div>
```
- Nur ReportLab-sicheres HTML (`<b>`, `<sub>`, `<sup>`) → rendert in Moodle-
  Seite, Vorschau **und** PDF-Material.
- Schritt für Schritt, jede Zeile nachvollziehbar; optionale Plausibilitätszeile.

**V7 — Einheiten:** jede physikalische Größe trägt in **jeder** Zeile ihre
Einheit (gegeben, eingesetzt, Ergebnis). Keine nackten Zahlen. Einheiten-
Konventionen wie in der SVG-Typografie (echte ²/³, Malpunkt ·, `1/min`).

**V6 — Echte Aufgaben:** jede Aufgabe/Rechnung ist in die **Handlungssituation**
des Kurses eingebettet — realer betrieblicher Kontext, Bedarf, Zweck („In der
Steuerung …, damit …"). Kein nacktes „Berechne R". Baut auf der bestehenden
Handlungssituations-/Praxisauftrag-Guidance auf.

## 2 · `quality_check`-Erweiterung (`SKILL.md`)

Die `quality_check`-Widget-Aktion listet Prüfpunkte (a)–(e). Ergänzen um:
- **(f) Rechenbeispiel-Bauplan:** jede Rechnung folgt geg/ges → Formel →
  Einsetzen → Ergebnis.
- **(g) Einheiten vollständig:** jede Größe/jedes Ergebnis trägt eine Einheit.
- **(h) Aufgaben situativ:** Aufgaben sind in die Handlungssituation eingebettet,
  kein nacktes „rechne aus".

Befunde je Baustein im Chat, konkrete Fixes vorschlagen, auf Wunsch als
`ai_assist` anwenden (wie die bestehenden Punkte). Kein Build.

## 3 · Weiche Heuristik (`validate_mbz.py`, nicht-fatal)

Heimat: `validate_mbz.py` — dort sind **Warnungen nicht fatal** (Exit 1 nur bei
Fehlern; SKILL.md „warnings don't fail"). Ideal für eine beratende Heuristik
(anders als das `--strict`-SVG-Gate).

**Was geprüft wird — „Rechnung ohne Einheit" (konservativ):**
- Gescannt wird der **aus dem `.mbz`-Archiv extrahierte HTML-Text** von
  `page`-, `book`-Kapitel- und `formular`-Inhalten (Tags gestrippt) — dieselben
  Inhalte, die `validate_mbz.py` für seine anderen Tiefen-Checks (Attribution,
  Formularfelder) bereits ausliest.
- Ein Text-Segment gilt als **Rechenkontext**, wenn es ein `=` **und**
  irgendwo einen erkannten Einheiten-Token enthält (V, A, mA, Ω, W, N, Pa, bar,
  mm, cm, m, s, min, h, °C, kg, g, Hz, % …). Nur so wird der reine Zähl-Fall
  („Anzahl = 150") vermieden.
- In solchen Segmenten wird ein **Ergebnis** `=\s*Zahl` gemeldet, dem **kein**
  Einheiten-Token folgt: `WARN Rechnung ohne Einheit? '… = 150' (Einheit ergänzen)`.
- Rein **beratend** — erhöht nie den Exit-Code.

**Einbindung:** Die reine Erkennung ist ein **testbarer Text-Helfer**
`_calc_unit_warnings(text: str) -> list[str]`. `validate_mbz.py` ruft ihn auf
dem extrahierten Inhalt jeder relevanten Aktivität auf und hängt die Treffer an
die **Warnungs**-Liste (nicht an die Fehler-Liste). Die genaue Stelle, an der
`validate_mbz` die HTML-Inhalte bereits extrahiert, wird im Plan nach Lesen von
`validate_mbz.py` fixiert.

## 4 · Tests

Neue `tests/test_validate_calc_units.py` — rufen den Helfer
`_calc_unit_warnings(text)` direkt mit Text-Schnipseln auf (kein `.mbz`-Bau nötig):

| Fixture (Text) | Erwartung |
|---|---|
| Rechnung mit Einheit: „R = 3 V / 0,02 A = 150 Ω" | keine WARN |
| Ergebnis ohne Einheit im Rechenkontext: „… U = 5 V; R = 150" | 1 WARN |
| Nicht-Rechenkontext: „Anzahl der Bauteile = 150" (kein Einheiten-Token) | keine WARN |
| reiner Fließtext ohne `=` | keine WARN |

Bestehende `validate_mbz`-Tests bleiben grün.

## 5 · Akzeptanz

- Volle Test-Suite grün.
- **Korpuslauf:** `validate_mbz.py` über die vorhandenen Kurse in
  `Moodle-Kurse/*/*.mbz` laufen lassen; die neue Heuristik darf keine **offen-
  sichtlich falschen** „Rechnung ohne Einheit"-Warnungen auf gut gemachten
  Rechenbeispielen produzieren. Da beratend (nicht-fatal), sind vereinzelte
  Grenzfälle tolerierbar — aber die Trefferquote soll stimmen (Stichprobe
  sichten). Bei zu vielen Fehltreffern: Rechenkontext-Bedingung verschärfen.

## Umsetzungsschritte (Grobskizze für den Plan)

1. `validate_mbz.py`: `_calc_unit_warnings(spec)` + Einbindung in die
   Warnungs-Liste; Tests.
2. `course-design.md`: Abschnitt „Rechenbeispiele & Aufgaben" (Muster + V5/V6/V7).
3. `SKILL.md`: `quality_check` um (f)/(g)/(h) erweitern.
4. Korpuslauf-Stichprobe → ggf. Einheiten-Token / Kontextbedingung kalibrieren.

## Geparkt / Folge

- **V2 Bruchdarstellung → Strang 3** (Rendering-Entscheidung: echter Bruch nur
  im Browser / diagonaler Unicode-Bruch überall / Slash beibehalten).
- Übrige Stränge: O3 Simulationen, O4 Didaktik-Profile, O1 Recap, O2 Speed.
