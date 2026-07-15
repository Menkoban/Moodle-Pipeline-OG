# Spec — Diagramm-Validatoren (V1, V3, V4)

**Datum:** 2026-07-15
**Skill:** `moodle-mbz-builder`
**Strang:** 1 von ~6 (siehe „Geparkte Stränge" am Ende)
**Status:** Design freigegeben (Autor: „passt", 2026-07-15) → Spec zur Durchsicht

## Kontext & Motivation

Der Skill lintet eingebettete SVG-Diagramme bereits umfassend über
`scripts/validate_svg.py` (Text-Messung via `scripts/svg_geometry.py`): viewBox-
Clipping (OVERFLOW), Text-Overlaps, Linien/Formen die durch Labels laufen,
Tofu-Glyphen, deutsche Typografie (², ³, Malpunkt ·, Umlaute, Dezimalkomma,
Indizes), Schriftgröße, Bündigkeit, Kontrast. Der Check läuft automatisch in
`make_materials.py` und `build_mbz.py` und ist als `validate_svg.py --strict`
**Pflicht-Gate** in der Pipeline (SKILL.md, Schritt 2).

Drei Diagramm-Defekte fängt er heute **nicht** ab:

- **V1 — Achsenbeschriftung:** ein Koordinaten-Diagramm ohne Achsentitel.
- **V3 — Skalierung:** eine Achse ohne Teilung/Skalenwerte.
- **V4 — Geschlossene Figuren:** Figuren mit einer sichtbaren Lücke (nicht
  geschlossen) oder mit über eine Ecke hinausstehenden Linien-Enden.

Diese drei werden als neue Checks in den bestehenden Linter integriert.

## Ziele / Nicht-Ziele

**Ziele**
- V1/V3/V4 als zusätzliche Checks in `validate_svg.py`, ohne die bestehende
  Architektur zu brechen.
- **Keine Fehlalarme** auf dem vorhandenen guten SVG-Bestand (harte
  Akzeptanzbedingung, s. §7) — weil das `--strict`-Gate jede Warnung blockt.
- Erweiterung ohne neues Skript und ohne Änderung an `build_mbz.py` /
  `make_materials.py` (die rufen `validate_svg` bereits auf).

**Nicht-Ziele**
- Automatisches Korrigieren der Defekte (der Linter meldet, `autofit_svg.py`
  bleibt für Größenanpassung zuständig).
- Prüfung von V1/V3 auf Nicht-Chart-Grafiken (Schaltpläne, Anatomiebilder,
  Piktogramme) — diese haben bewusst keine Achsen.
- V2 (Bruchstrich) — eigener Strang, betrifft Seitentext/Formulare, nicht SVG.

## 1 · Chart-Erkennung: expliziter Marker

Nur **explizit markierte** Diagramme werden auf V1/V3 (Achsen/Skala) geprüft.
Marker = **Root-Attribut** am `<svg>`:

```xml
<svg viewBox="0 0 640 400" data-diagram-type="chart" xmlns="http://www.w3.org/2000/svg">
```

- `validate_svg.lint_file` liest nach `G.load(path)`:
  `is_chart = (root.get("data-diagram-type") == "chart")`.
- `data-diagram-type` ist ein attributloser (namespace-freier) String → von
  `xml.etree.ElementTree` problemlos gelesen; kein Namespace-Handling nötig.
- Funktioniert bei jedem Aufrufweg von `validate_svg` (einzelne `.svg`, Ordner,
  `course.json`), weil immer die echte SVG-Datei geöffnet wird.
- **Muss `autofit_svg.py` überstehen:** in der Umsetzung verifizieren, dass
  autofit (das viewBox + Hintergrund-Rect editiert) das Root-Attribut nicht
  entfernt. Falls doch: autofit so anpassen, dass unbekannte Root-Attribute
  erhalten bleiben.

**Verworfen:** Dateiname-Konvention (`*_chart.svg`, brüchig) und Feld in
`course.json` (großer Blast-Radius; `images` sind heute reine Pfad-Strings;
greift nicht beim Einzel-Lint).

**V4 braucht KEINEN Marker** — „geschlossene Figuren" gilt für alle Diagramme.

## 2 · V1 — Achsenbeschriftung *(warn, nur markierte Charts)*

**Achsenerkennung (gemeinsamer Helfer für V1+V3):**
Aus den `line`-Boxen (`extra["seg"]`) und den Geraden-Segmenten der `path`-Boxen
(`extra["pts"]`, aufeinanderfolgende Punktpaare):
- **x-Achse:** längstes **fast-waagerechtes** Segment (|y2−y1| ≤ 2) in der
  **unteren** Hälfte (Segment-y ≥ vy + 0.5·vh), Länge ≥ 0.4·vw.
- **y-Achse:** längstes **fast-senkrechtes** Segment (|x2−x1| ≤ 2) im **linken**
  Bereich (Segment-x ≤ vx + 0.4·vw), Länge ≥ 0.4·vh.
- Wird auf einem markierten Chart **keine** plausible Achse gefunden →
  `warn: ACHSE keine <x|y>-Achsenlinie erkennbar` (ein Chart sollte Achsen haben).

**Titel-Prüfung je Achse:** existiert ein **Achsentitel-Text** in Achsennähe,
dessen Inhalt **nicht rein numerisch** ist (enthält Buchstaben / Einheit, z. B.
„t in s", „U / V", „Kraft F")?
- **x-Titel:** nicht-numerischer Text mit Zentrum **unterhalb** der x-Achse
  (y > axis_y) **oder** nahe deren rechtem Ende.
- **y-Titel:** nicht-numerischer Text im **linken Drittel** des Charts
  (Zentrum-x < vx + vw/3), Tick-Zahlen ausgenommen. **Lenient**, weil
  y-Titel oft um −90° rotiert sind und `svg_geometry` `rotate()` ignoriert
  (die Box-Position rotierter Texte ist unzuverlässig) — daher genügt
  *irgendein* nicht-numerischer Text in der linken Marge.
- Fehlt der Titel → `warn: ACHSE <x|y>-Achse ohne Beschriftung`.

Rein numerische Texte (Skalenwerte) zählen **nicht** als Titel.

## 3 · V3 — Skalierung *(warn, nur markierte Charts)*

Kernsignal einer skalierten Achse = **numerische Skalenwerte** entlang der Achse.

Je Achse (Achsenerkennung wie §2):
- **Skalenwerte zählen:** Text-Boxen mit rein numerischem Label
  (`^-?\d+([.,]\d+)?$`), positioniert **unter** der x-Achse bzw. **links** der
  y-Achse. Anzahl < 2 → `warn: SKALA <x|y>-Achse ohne Skalierung (Werte fehlen)`.
- **Teilstriche (sekundär, nur informativ in der Meldung):** kurze Segmente
  (Länge ≤ ~10 px) **quer** zur Achse (senkrecht bei x, waagerecht bei y),
  verteilt entlang der Achse. Fehlen sie, aber Werte sind da → kein eigener
  Fehler; wenn beides fehlt, Meldung ergänzt „…(auch keine Teilstriche)".

Der harte Auslöser bleibt „< 2 numerische Werte" — das ist präzise und
fehlalarm-arm. Teilstrich-Erkennung dient nur der Meldungsqualität.

## 4 · V4 — Geschlossene Figuren / keine Über-/Durchstriche *(warn, ALLE Diagramme, konservativ)*

**Ergänzung in `svg_geometry.py`:** für `path`-Boxen zusätzlich
`extra["path_closed"] = bool` setzen — True, wenn das `d`-Attribut ein `Z`/`z`
enthält **oder** erster ≈ letzter Sample-Punkt (Abstand ≤ 0.5 px). `extra["pts"]`
existiert bereits (Start = pts[0], Ende = pts[-1]).

**V4a — Beinahe-Schluss (near-miss closure):** für jede `path`/`polyline`-Box,
die **nicht** geschlossen ist und **≥ 3** Punkte hat (echte Figur, keine
2-Punkt-Linie). **`polygon` ist ausgenommen** — SVG-Polygone sind per
Spezifikation immer geschlossen, und `svg_geometry.collect_boxes` hängt bei
`polygon` den Startpunkt ohnehin automatisch an (`extra["pts"]` endet stets am
Start). Betroffen sind also offene `path`/`polyline`-Umrisse:
- `gap = dist(pts[0], pts[-1])`
- Melden, wenn **alle** gelten:
  - `2 px < gap ≤ 12 px` (nah dran, aber offen — kalibrierbares Band),
  - Figur ist **flächig** (bbox-Breite > 10 **und** -Höhe > 10 → keine Gerade),
  - `gap < 0.15 · bbox-Diagonale` (Endpunkte kehren fast zum Start zurück →
    schließende Figur, **kein** offener Funktionsgraph/Leader — dessen Endpunkte
    liegen weit auseinander und fallen aus dem Band).
- → `warn: FIGUR nicht geschlossen (Lücke ~{gap:.0f}px) — Pfad mit Z schließen
  oder Endpunkte treffen lassen`.

**V4b — Überstand (overshoot) — FP-riskantester Check, konservativ:** ein
gerader Segment-Endpunkt E, der **2–12 px über eine Ecke hinausragt**, die das
Segment mit einem anderen bildet:
- E verbindet sich mit **keinem** anderen Endpunkt (min. Abstand zu allen
  anderen Endpunkten > 3 px), **und**
- E liegt 2–12 px **jenseits** eines Treffpunkts J, an dem sein Segment ein
  anderes Segment trifft (E kollinear mit dem Segment, Stub hinter J).
- → `warn: LINIE steht ~{d:.0f}px über die Ecke hinaus`.
- **Kalibrieren-oder-verschieben:** lässt sich V4b in der Umsetzung nicht auf
  dem Bestand fehlalarmfrei bekommen (§7), wird es zunächst **nicht
  ausgeliefert** (V4a allein deckt den Hauptfall „Figur nicht geschlossen").

*(Später optional, hier bewusst raus: Linie quer durch gefüllte Figur —
fehlalarm-anfällig.)*

## 5 · Meldungs-Konvention

Neue Schlüsselwörter im bestehenden Stil (Großbuchstabe voran, wie
OVERFLOW/OVERLAP/BOXFIT): `ACHSE`, `SKALA`, `FIGUR`, `LINIE`. Alle als
**warn** (`warns.append(...)`), keine `errors`.

## 6 · Härtegrad + Gate-Verhalten

Alle neuen Checks = **warn**. Konsequenz mit der bestehenden Mechanik:
- `validate_svg.py` (ohne `--strict`): Exit 0, nur Ausgabe.
- `validate_svg.py --strict` (Pipeline-Gate, SKILL.md Schritt 2): **Exit 1** bei
  jeder Warnung. → Ein **markierter Chart ohne Achsen/Skala** und eine **offene
  Figur** blockieren das Gate. Genau gewünscht.
- `build_mbz.py`: lintet warn-only (Default), `--strict-svg` bricht ab — Verhalten
  unverändert; die neuen warns erscheinen dort als Hinweis.

## 7 · Fehlalarm-Schutz (harte Akzeptanzbedingung)

Weil `--strict` jede Warnung zum Gate-Fehler macht, dürfen die neuen Checks auf
**bestehenden, guten** Diagrammen **nicht** anschlagen.

**Akzeptanzkriterium:** `validate_svg.py` mit den neuen Checks über den gesamten
vorhandenen SVG-Bestand laufen lassen:
- `<skill>/assets/*.svg`,
- alle `C:/Users/User/OneDrive - HSOS/Desktop/Moodle-Kurse/*/assets/*.svg`.

Ergebnis muss sein: **null neue Warnungen** (verglichen mit dem Lauf vor der
Änderung). Die Toleranzbänder in V4 (2–12 px, 0.15·Diagonale) und die
V1/V3-Schwellen werden daran kalibriert. V4b wird nur ausgeliefert, wenn es
diese Bedingung erfüllt; sonst verschoben.

*Hinweis:* Bestehende Charts sind evtl. noch **nicht** mit
`data-diagram-type="chart"` markiert → sie lösen V1/V3 zunächst gar nicht aus
(kein Fehlalarm). Das nachträgliche Markieren + Ausbessern vorhandener Charts
ist ein separater, optionaler Retrofit-Schritt (nicht Teil der
Akzeptanzbedingung).

## 8 · Tests

Neue `tests/test_validate_svg_charts.py` mit In-Line-SVG-Fixtures:

| Fixture | Erwartung |
|---|---|
| markierter Chart mit x/y-Achse, Titeln, Werten | sauber |
| markierter Chart, x-Titel fehlt | genau 1 ACHSE-warn |
| markierter Chart, y-Achse < 2 Werte | genau 1 SKALA-warn |
| **un**markierter chart-artiger Schaltplan ohne Titel | **keine** ACHSE/SKALA-warn |
| offene Box (Pfad ohne Z, Lücke ~6 px) | genau 1 FIGUR-warn |
| saubere geschlossene Box (Pfad mit Z) | keine FIGUR-warn |
| offener Funktionsgraph (Endpunkte weit auseinander) | keine FIGUR-warn |
| (falls V4b aktiv) Linie mit ~6 px Überstand | genau 1 LINIE-warn |

Plus ein **Regressions-/Korpus-Check** (§7) als Test oder als dokumentierter
manueller Schritt: 0 neue warns auf dem Bestand.

Bestehende Suites (`test_validate_svg_paths.py`, `test_svg_geometry_paths.py`)
müssen grün bleiben.

## 9 · Autorenregeln (Doku)

Kurzer Zusatz in `references/course-design.md`, Abschnitt „SVG-Autorenregeln":
- Koordinaten-Diagramm → `data-diagram-type="chart"` aufs Wurzel-`<svg>`.
- Markierte Charts brauchen **Achsentitel** (nicht nur Zahlen) **und
  Skalenwerte** (≥ 2 je Achse).
- Figuren **schließen** (Pfad mit `Z`, Polygon statt offener Linienkette);
  keine über Ecken hinausstehenden Linien-Enden.

Und ein Satz im Kopf-Docstring von `validate_svg.py` (Check-Liste ergänzen).

## Umsetzungsschritte (Grobskizze für den Plan)

1. `svg_geometry.py`: `extra["path_closed"]` für path-Boxen.
2. `validate_svg.py`: Achsen-Helfer, V1, V3 (hinter `is_chart`), V4a (immer),
   V4b (hinter Korpus-Kalibrierung).
3. `tests/test_validate_svg_charts.py`.
4. Korpuslauf §7 → Bänder kalibrieren; V4b-Entscheidung.
5. Doku: `references/course-design.md` + `validate_svg.py`-Docstring.
6. Optionaler Retrofit: bestehende Charts markieren (separat).

## Geparkte Stränge (Entscheidungen stehen, je eigener Design→Plan→Umsetzung-Zyklus)

- **V2 Bruchstrich** — echte Bruchdarstellung in Seitentext-Rechnungen +
  Formular-Aktivitäten (nicht SVG); Einheiten (1/min, N/cm², km/h) behalten `/`.
- **V5–V7 Inhalt** — Rechenbeispiel-Struktur (geg/ges → Formel → einsetzen →
  Ergebnis → Einheit), echte Aufgaben aus realen Situationen, Einheiten
  mitführen. Durchsetzung: Autorenregel + KI-`quality_check` + weiche
  Heuristik-Warnung.
- **O1 Recap** — Recap-Video soll die Kurs-Diagramme zeigen: Datei-Upload der
  Material-PDF/Vorschau (session-geteilt) versuchen, Fallback Bildbeschreibungen
  ins Dossier. (Randnotiz: NotebookLM-Fokus-Feld evtl. seit 2026-07-15 weg —
  im O1-Design prüfen.)
- **O2 Pipeline-Speed** — Kurserstellung schneller/schlanker (Schritte
  parallelisieren, weniger Babysitting).
- **O3 Sims** — animierte Live-Grafik + Zeitanimation + mehr Manipulation als
  **Standard**; **Challenge-Modus** nur auf konkrete Anforderung → als Option
  ins Briefing.
- **O4 Didaktik-Profile** — Rode/ZDQ herauslösen in **auswählbare Konzept-
  Profile** (Registry, Default Rode), im Briefing wählbar; jedes Profil bringt
  eigene Sektions-Sequenz + Regeln mit.
