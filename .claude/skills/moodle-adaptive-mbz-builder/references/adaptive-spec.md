# Adaptive Kursdefinition — JSON-Schema (Eingabe für build_adaptive.py)

Der adaptive Expander (`scripts/build_adaptive.py`) verwandelt eine
**Stufen-Definition** in eine normale `course.json` (Sections + Aktivitäten +
availability + Gradebook), die dann durch die Standard-Pipeline läuft
(`build_simulation → make_materials → build_mbz → validate_mbz →
simulate_pathways`). Didaktik/Herleitung: `adaptive-lernpfade.md`.

## Eingabeformat

```json
{
  "course": { … wie gehabt (fullname, shortname, format "tiles", …) … },
  "adaptive": {
    "einstieg": "mittel",
    "gewichte": { "anfaenger": 1.0, "mittel": 1.5, "fortgeschritten": 2.0 },
    "schwellen": {
      "aufstieg": 80,
      "abstieg": 40,
      "fortgeschritten_halten": 50,
      "hysterese_abstieg": null
    },
    "wiederholung": { "max_versuche": 3 },
    "intro_section": { "name": "Über diesen Kurs", "activities": [ … ] },
    "stufen": [
      {
        "name": "Stufe 1 · Druck und Pascal",
        "niveaus": {
          "anfaenger": {
            "titel": "Grundlagen behutsam",
            "image": "assets/….png",
            "activities": [ …Standard-Aktivitäten… ],
            "test": { "name": "Test Stufe 1 (Anfänger)", "questions": [ … ] }
          },
          "mittel":          { … },
          "fortgeschritten": { … }
        },
        "foerder": {
          "titel": "Nochmal anders erklärt",
          "activities": [ … ]
        }
      }
    ],
    "abschluss_section": { "name": "Abschluss", "activities": [ … ] }
  }
}
```

## Feste Regeln des Expanders

- **Einstieg** (`einstieg: "mittel"`): Stufe 1 besteht NUR aus der
  Mittel-Kachel + Mittel-Test (alle starten gleich). `"wahl"`: alle drei
  Stufe-1-Kacheln offen. Ab Stufe 2 greifen immer die Niveau-Fenster.
- **Niveau-Fenster (Stufe s ≥ 2)** — OR über die Tests der Vorstufe,
  harte Kanten (Moodle-grade-Bedingung: erfüllt wenn `min ≤ note < max`):
  - Anfänger(s):  `anf(s-1) ∈ [abstieg, aufstieg)` ODER `mittel(s-1) < abstieg`
  - Mittel(s):    `anf(s-1) ≥ aufstieg` ODER `mittel(s-1) ∈ [abstieg, aufstieg)`
                  ODER `fort(s-1) < fortgeschritten_halten`
  - Fortgeschritten(s): `mittel(s-1) ≥ aufstieg` ODER `fort(s-1) ≥ fortgeschritten_halten`
  - Anfänger(s) zusätzlich: `anf(s-1) < abstieg` → bleibt Anfänger, aber die
    **Förder-Kachel der Vorstufe** wird sichtbar (Wiederholschleife).
- **Wiederholschleife + Deckel**: Förder-Kachel(s-1) sichtbar wenn irgendein
  Test(s-1) unter seiner Mindestschwelle liegt; die Tests erlauben
  `max_versuche` Versuche (Bewertungsmethode: bester Versuch) — der Deckel
  ist die Quiz-Versuchsbegrenzung, die Fördervariante der „andere Zugang".
- **Kein toter Pfad**: Für jeden Test deckt die Vereinigung der Fenster
  aller Folgekacheln lückenlos [0, 100] ab (prüft `simulate_pathways.py`).
- **Ratschen-Verbot**: KEINE availability-Bedingung referenziert das
  kumulative Item (prüft `validate_mbz.py`).
- **Gradebook**: je Test ein Quiz-grade_item (idnumber `test-s{s}-{niveau}`);
  EIN kumulatives Calculated-Item „Gesamtscore (gewichtet)" =
  Σ Test × Gewicht — reine Doku-/Zeugnisgröße.
- **Hysterese** (`hysterese_abstieg`, z. B. 35): ersetzt nur die
  Abstiegsschwelle in den Fenstern (asymmetrischer Puffer). Das gleitende
  2-Test-Mittel aus §4.3 der Referenz ist bewusst noch NICHT umgesetzt
  (dokumentierte Option).

## Symbolische Grade-Referenzen

Der Expander schreibt in availability-Bedingungen niemals numerische IDs,
sondern `{"type":"grade","ref":"test-s1-mittel","min":…,"max":…}`.
`build_mbz.py` löst `ref` beim Bauen gegen die ID-Map der erzeugten
grade_items auf und serialisiert das finale Moodle-JSON.
