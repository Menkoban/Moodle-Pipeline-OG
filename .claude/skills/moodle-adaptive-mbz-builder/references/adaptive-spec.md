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
    "niveaus": [
      { "key": "anfaenger", "label": "Anfänger" },
      { "key": "mittel", "label": "Mittel" },
      { "key": "fortgeschritten", "label": "Fortgeschritten" }
    ],
    "differenzierung": ["niveau"],
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

- **Pfade (`niveaus`)**: geordnete Liste (niedrigste → höchste Anforderung),
  **2–4 Pfade**, keys frei wählbar (auch Kurzform als Strings:
  `"niveaus": ["basis", "standard", "profi"]`). Fehlt das Feld, gelten die
  klassischen drei (anfaenger/mittel/fortgeschritten). Jede Stufe MUSS
  unter `stufe.niveaus` für jeden key einen Eintrag haben.
- **`differenzierung`**: Liste der Dimensionen (`niveau`, `sprache`,
  `fachsprache`, frei) — reine Autoren-/Briefing-Metadaten; die Mechanik
  (Fenster, Gewichte) ist für alle Dimensionen identisch, die Inhalte je
  Pfad setzen die Differenzierung um.
- **Einstieg** (`einstieg`): Pfad-Key → Stufe 1 besteht NUR aus dieser
  Kachel (alle starten gleich; Default: der mittlere Pfad). `"frei"`:
  alle Stufe-1-Kacheln offen. Ab Stufe 2 greifen immer die Fenster.
- **Verzweigungsmatrix (generisch, Pfad-Index i von 0..k−1)** — OR über
  die Tests der Vorstufe, harte Kanten (`min ≤ note < max`):
  - oberster Pfad (i = k−1): `≥ fortgeschritten_halten` hält, sonst → k−2
  - alle anderen: `≥ aufstieg` → i+1 · `[abstieg, aufstieg)` → i ·
    `< abstieg` → max(i−1, 0)
  - **Erreichbarkeit**: Ein Pfad, den aus der Vorstufe kein Fenster
    erreichen kann (z. B. der unterste direkt nach einem hohen Einstieg),
    wird in dieser Stufe NICHT emittiert — sonst stünde er ohne Bedingung
    dauerhaft offen. Er taucht wieder auf, sobald er erreichbar ist.
- **Gewichte-Default**: linear 1,0 → 2,0 über die Pfad-Reihenfolge
  (k=2: 1,0/2,0 · k=3: 1,0/1,5/2,0 · k=4: 1,0/1,33/1,67/2,0); per
  `gewichte` je key überschreibbar.
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
- **Pfad-Lock (Null-Item-Invariante)**: Der erste Versuch im Stufentest
  wählt den Pfad der Stufe verbindlich. Kachel-Bedingung: `(Fenster UND
  alle Geschwister-Tests unberührt) ODER eigener Test angefasst`;
  zusätzlich Modul-Lock auf jedem Test. „Unberührt" = `!|`-Knoten über
  completion e=1 + e=3 (exakt Zustand 0 — e=0 allein matcht in Moodle auch
  „durchgefallen"). Tests werden auf `completion: 2` +
  `completionusegrade` gestellt. Schützt vor Doppel-Füllung zweier
  Null-Items derselben Stufe durch Vortest-Retakes (bester Versuch) und
  gilt auch für `einstieg: "frei"` in Stufe 1. Prüft
  `simulate_pathways.py` (RETAKE-Check).
- **grademax des kumulativen Items** = Σ je Stufe (max. Gewicht der dort
  emittierten Pfade × 100) — das real erreichbare Maximum des besten Wegs,
  damit die Prozentanzeige lesbar ist. Moodle klemmt Calculated-Ergebnisse
  auf grademax (`grade_item::bounded_grade`). Prüfen beide:
  `simulate_pathways.py` (GRADEMAX-Check).

## Symbolische Grade-/CM-Referenzen

Der Expander schreibt in availability-Bedingungen niemals numerische IDs,
sondern `{"type":"grade","ref":"test-s1-mittel","min":…,"max":…}` bzw.
`{"type":"completion","cmref":"test-s2-anfaenger","e":1}`.
`build_mbz.py` löst `ref` gegen die grade_item-ID-Map und `cmref` gegen
die cmid-Map auf (beide im Pre-Pass gefüllt, Vorwärtsreferenzen erlaubt)
und serialisiert das finale Moodle-JSON. Verschachtelte op-Knoten sind
erlaubt; show/showc setzt der Resolver nur an der Wurzel (Moodle-
Restore-Invariante).
