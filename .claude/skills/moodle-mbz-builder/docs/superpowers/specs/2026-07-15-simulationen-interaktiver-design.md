# Spec — Simulationen interaktiver (O3)

**Datum:** 2026-07-15
**Skill:** `moodle-mbz-builder`
**Strang:** 4 von ~6 (siehe [MbZ-Builder-Überarbeitung])
**Status:** Design gelockt (Autor-Q&A 2026-07-15); Autor delegiert Umsetzung mit Agents.

## Kontext & Motivation

Heute ist die „Live-Ansicht" einer Simulation (`scripts/sim_engine.py`) ein
**statisches SVG**, in dem `render()` nur **Text-Labels** aktualisiert — es
bewegt sich faktisch nichts, nur Zahlen ändern sich. Der Autor will: **mehr
Bewegung, mehr sehen, mehr machen.** Konkret gelockt:

- **Animierte Live-Grafik** — die Grafik selbst reagiert (Balken/Zeiger/Pfeile
  wachsen, Farbintensität, Stromfluss, Kurve zeichnet sich neu). *Standard.*
- **Zeitbasierte Animation** — Play/Pause über die Zeit mit Geschwindigkeit
  (Sinus läuft, Kolben bewegt, Ladevorgang). *Standard, wo sinnvoll.*
- **Mehr Manipulation** — Lernende schalten/wählen (Schalter, Szenarien),
  nicht nur Schieberegler. *Standard.*
- **Challenge-Modus** — die Sim stellt eine Aufgabe („stelle R so, dass I = …")
  und gibt Feedback. **Opt-in**: nur auf konkrete Anforderung, als Option ins
  **Briefing**.

## Ziele / Nicht-Ziele

**Ziele**
- `sim_engine.py` generisch erweitern um: (1) Zeit-Animationsschleife mit
  Play/Pause/Speed, (2) erweiterte Eingaben (select/toggle) für Manipulation,
  (3) opt-in Challenge-Karte. Alles **rückwärtskompatibel** (bestehende Specs
  ohne die neuen Felder rendern unverändert).
- Kompakt-Layout (kein Scrollen, `grid-template-columns:300px …`) bleibt — der
  `validate_mbz.py`-Sim-Layout-Check bleibt gültig.
- 2–3 Bibliotheks-Sims exemplarisch aufwerten (Animation + Manipulation) + eine
  neue zeitbasierte Sim als Muster.
- Briefing (Skill-Doku) bietet Challenge-Modus als Option an.

**Nicht-Ziele**
- Keine externe Animations-/Physik-Bibliothek (offline, CSP-sicher, self-
  contained bleibt Pflicht).
- Kein Zwang zur Animation, wo ein Thema nichts „Bewegtes" hat.

## 1 · Engine-Erweiterungen (`scripts/sim_engine.py`)

Alle Spec-Felder **optional**; fehlen sie, verhält sich die Engine wie bisher.

**(a) Zeit-Animation** — neues Spec-Feld `animate` (JS-Body, bekommt
`(root, s, o, t)`; `t` = Sekunden seit Play, geschwindigkeits-skaliert):
- Ist `animate` vorhanden, rendert die Engine eine **Play/Pause**-Schaltfläche
  und einen **Geschwindigkeits**-Regler (0,25×–4×). Default: **pausiert**
  (Lernende starten selbst).
- `requestAnimationFrame`-Schleife: pro Frame `t += dt·speed`, dann
  `animate(root, s, o, t)`. Regler-Änderungen rufen weiter `update()`.
- Ein **Reset** setzt `t=0`.

**(b) Erweiterte Eingaben (Manipulation)** — `inputs[i].type`:
- `"range"` (Default, wie bisher: min/max/step/default),
- `"select"` (`options:[{value,label}]`) → `<select>`,
- `"toggle"` (`on/off`-Werte, Default an/aus) → Checkbox/Schalter.
- `state()` liest alle Typen einheitlich (Zahl für range/toggle, String/Number
  für select). `compute/render/animate` nutzen sie wie gehabt.
- Ermöglicht Szenario-Umschaltung (z. B. „Schalter offen/geschlossen",
  „Betriebsart") ohne Sondercode.

**(c) Challenge-Modus (opt-in)** — Spec-Feld `challenge`:
```
challenge: { prompt:str, check:"<JS body> // gets (s,o) -> return bool",
             success:str, hint:str }
```
- Vorhanden → die Engine rendert eine **Challenge-Karte** (Prompt + „Prüfen"-
  Button). Klick wertet `check(s,o)` aus → `success` (grün) oder `hint` (gelb).
- Fehlt `challenge` → keine Karte (Standardverhalten).

**Layout:** Play/Speed/Challenge sitzen in der linken Steuer-/Ergebnis-Spalte
(bzw. unter der Grafik), sodass das Kompakt-Grid und der No-Scroll-Anspruch
erhalten bleiben.

## 2 · Bibliotheks-Aufwertung (`SIM_LIBRARY`)

- **reihenschaltung / parallelschaltung:** animierte **Stromfluss-Punkte**
  entlang der Leiter (Geschwindigkeit ∝ Strom), Balken/Farbe reagieren live
  (nutzt `animate` + bestehendes `render`).
- **Neue zeitbasierte Muster-Sim** (eine, als Vorlage): z. B. **Wechselspannung
  (Sinus)** — `u(t)=û·sin(2π·f·t)`, laufende Kurve + Zeiger; Regler û, f;
  optional Challenge („stelle f so, dass Periode = 20 ms").
- Mindestens eine Sim mit **Manipulation** (select/toggle), z. B. Schalter offen/
  geschlossen.

## 3 · Briefing / Doku

- `references/course-design.md` (Sim-Abschnitt) + `SKILL.md` (Sim-Kapitel):
  Animation/Manipulation sind der neue Standard; **Challenge-Modus** als Option
  nennen (nur auf Wunsch). Kurzes Spec-Feld-Referenz-Update (`animate`,
  `inputs[].type`, `challenge`).
- Falls ein Intake-/Briefing-Formular existiert: Challenge als ankreuzbare
  Option ergänzen (sonst nur Doku).

## 4 · Rückwärtskompatibilität & Validierung

- Bestehende Specs (nur `range`-Inputs, `render`, kein `animate`/`challenge`)
  müssen **unverändert** rendern. Regressions-Check: bestehende Sims
  (`build_simulation.py --list`/`--emit`) bauen weiter.
- `validate_mbz.py`-Sim-Check (`grid-template-columns:300px`) bleibt grün.

## 5 · Tests

Neue `tests/test_sim_engine_interactive.py`:
- `render(spec)` mit `animate` enthält Play/Pause + Speed-Control + rAF-Loop.
- `render(spec)` mit `inputs[].type:"select"`/`"toggle"` erzeugt die richtigen
  Controls; State-Auslesen deckt alle Typen.
- `render(spec)` mit `challenge` erzeugt die Challenge-Karte + Prüf-Logik;
  ohne `challenge` keine Karte.
- Ein **Alt-Spec** (nur range + render) rendert wie bisher (kein Play, keine
  Challenge) — Rückwärtskompatibilität.
- Smoke: `build_simulation.py --emit <lib> -o f.html` für die aufgewerteten
  Sims erzeugt valides, self-contained HTML.

## Umsetzung mit Agents (Grobskizze)

- **Agent A:** Engine-Kern (`sim_engine.py`: animate-Loop, erweiterte Inputs,
  Challenge) + `tests/test_sim_engine_interactive.py` (TDD).
- **Agent B:** Bibliotheks-Aufwertung (Reihen-/Parallelschaltung animiert) +
  neue Sinus-Sim.
- **Agent C:** Doku/Briefing (`course-design.md`, `SKILL.md`).
- Integration + Regressions-/Smoke-Tests + Merge durch mich.
- (Agenten-Aufteilung erst nach fertigem Plan; B/C bauen auf A's Interfaces auf.)

## Geparkt / Folge

- Übrige Stränge: O4 Didaktik-Profile, O1 Recap, O2 Speed.
