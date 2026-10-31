# Diagnose-Modul-Modell — JSON-Schema (Eingabe für build_modular.py)

Zweites adaptives Modell dieses Skills (neben dem Stufen-Modell aus
`adaptive-spec.md`), umgesetzt nach dem Nutzer-Konzept „Modulares adaptives
Lernsystem v3" (Teil B dort ist normativ). Auswahl über
`adaptive.modell: "diagnose"`.

**Kernidee:** Jedes Modul (= Kachel) diagnostiziert FRISCH und konvergiert
auf EINEN gemeinsamen bewerteten Sicherungstest. Nur EINE Dimension (Niveau)
erzeugt echte Pfade (multiplikativ); alle weiteren Dimensionen sind additive
**Schichten-Overlays**, die einzelne Elemente ein-/ausblenden — Wachstum
3+2+2 statt 3×2×2, Bedingungsbäume flach (Tiefe ≤ 2, ≤ 3 Blätter, hart
validiert statt still gekürzt).

## Strukturmodell je Modul

1. **Diagnose** — Quiz 5–8 Items, Bewertungskategorie `einstufung`
   (**Gewicht 0** — entkoppelte Scoring-Architektur, hart validiert),
   `gradepass=0` ist PFLICHT: so ist der completion-Zustand nach dem Versuch
   exakt 1 und das Diagnose-Gate (`e=1`) greift auch bei 0 Punkten.
2. **Drei Niveaupfade** — `basic`/`standard`/`advanced` über grade-Fenster
   auf die Diagnose. Schwellen aus `level_thresholds` werden auf harte
   Kanten normalisiert: `[0,50) [50,80) [80,∞)` — die 49,99-Schreibweise des
   Konzepts ist UI-Kosmetik, reelle Noten kennen keine Lücke.
3. **Konvergenzpunkt** — Quiz in Kategorie `leistung`, einzige Note des
   Moduls. Gate: `|`-Baum über completion (`e=1`) des **letzten
   Pflichtelements je Pfad** (nur Typen mit Ansehen-Abschluss:
   page/book/url/file/folder).
4. **Freischaltung/Remediation** — Folgemodul-Section öffnet per
   `grade ≥ pass` auf die Konvergenz (`pacing.unlock_rule: "grade_min"`,
   alternativ `"completion"` = bestanden via `e=2`); der Remediationsblock
   erscheint exakt im Fenster `[0, pass)`.

## Eingabeformat

```json
{
  "course": { … wie gehabt (fullname, shortname, format "tiles", …) … },
  "adaptive": {
    "modell": "diagnose",
    "occupation": "Elektroniker/-in für Betriebstechnik",
    "active_layers": ["language_support", "practice_experience", "wiederholer"],
    "level_thresholds": [ … Default basic/standard/advanced 0/50/80 … ],
    "pacing": {"unlock_rule": "grade_min", "unlock_threshold": 50.0,
               "remediation": true},
    "wiederholung": {"max_versuche": 3},
    "diagnose_versuche": 1,
    "layer_config": {"pruefungsnaehe": {"quelle": "datum", "ab": "2026-04-01"}},
    "grade_categories": [ … Default einstufung 0.0 / leistung 1.0 … ],
    "intro_section": { … }, "abschluss_section": { … },
    "modules": [
      {
        "id": "M01", "titel": "Motorschutz auslegen", "image": "assets/….png",
        "diagnostic": {"name": "…", "questions": [ … ]},
        "elements": [
          {"id": "M01-E01", "type": "page", "role": "advance_organizer",
           "name": "…", "content": "…", "visibility": {}},
          {"id": "M01-E02", "type": "page", "role": "erarbeitung",
           "visibility": {"level": ["basic"]}, …},
          {"id": "M01-E05", "type": "page", "role": "sprachhilfe",
           "visibility": {"language_support": true}, …},
          {"id": "M01-E06", "type": "assign", "role": "praxis_anknuepfung",
           "visibility": {"practice_experience": "with"}, …},
          {"id": "M01-E07", "type": "page", "role": "praxis_kompensation",
           "visibility": {"practice_experience": "without"}, …},
          {"id": "M01-E09", "type": "page", "role": "vertiefung",
           "visibility": {"level": ["advanced"], "optional_self_select": true}, …}
        ],
        "convergence": {"name": "…", "questions": [ … ], "pass": 50.0},
        "remediation": {"name": "…", "activities": [ … ]}
      }
    ]
  }
}
```

## Layer-Registry (Overlays)

Datengetrieben in `build_modular.LAYER_REGISTRY` — je Layer: Bedingungsart,
erlaubte `visibility`-Werte, Selbsteinschätzungs-Frage. Kern: 1–2. Optional
(User-Freigabe 2026-07-18): 3–7.

| # | Schlüssel | Art | Werte | Bedingung |
|---|---|---|---|---|
| 1 | `language_support` | Gruppe GRP-SPRACHE | nur `true` | group |
| 2 | `practice_experience` | Gruppe GRP-PRAXIS, tri-state | `"with"`/`"without"` | group / negiert `!|` |
| 3 | `pruefungsnaehe` | Gruppe ODER Stichtag (`layer_config.quelle: "datum"`, `ab`) | `true` | group / date `>=` |
| 4 | `wiederholer` | leistungsbasiert | `true` | grade auf Konvergenz `< pass` |
| 5 | `anschlussorientierung` | Selbstwahl-Gruppe | `true`/`with`/`without` | group |
| 6 | `verkuerzer` | Gruppe, tri-state | `true`/`with`/`without` | group |
| 7 | `umschueler` | Gruppe, tri-state | `true`/`with`/`without` | group |

Kompositionsregel (B.3, deterministisch): Wurzel immer `&`; Kinder in der
Reihenfolge Diagnose-Gate → Niveau-Fenster (zusammenhängende Level
verschmelzen zu EINEM Fenster) → Sprache → Praxis → weitere aktive Layer.
`visibility`-Schlüssel außerhalb `active_layers` = Abbruch.

## Feste Regeln & Validierung (B.4, Auswahl)

- `einstufung` MUSS Gewicht 0 haben (Abbruch); je Level ≥ 1
  `erarbeitung`-Element (kein leerer Pfad, Abbruch); `praxis_anknuepfung`
  ohne `without`-Gegenstück = Warnung; Nicht-Overlay-Rollen mit ≥ 2
  Overlay-Bedingungen = Abbruch; > 3 optionale Overlays = Warnung.
- **Elementtyp `h5p` wird abgelehnt** (User-Entscheid: erst weglassen,
  vorbereitet als künftiger ACTIVITY_BUILDER `h5pactivity`) — bis dahin
  `page` (+ Simulation/Video) nutzen.
- Pfadelemente erhalten automatisch `completion: 2` + `completionview: 1`
  (Ansehen-Abschluss). **Lab-E2E-Fund 2026-07-18:** ohne echtes
  completion-Kriterium bleibt der Zustand ewig 0 und das Konvergenz-Gate
  ist tot — validate_mbz prüft das jetzt statisch („completion=2 ohne
  Kriterium").
- Selbsteinschätzung (B.6): je aktiver Gruppen-Schicht eine unbewertete
  choice-Aktivität im Startabschnitt + Lehrkraft-Hinweis (Gruppen kommen
  OHNE Mitglieder aus dem Backup; Zuweisung macht die Lehrkraft).
- **Nachteilsausgleich** läuft bewusst NICHT über Sichtbarkeit, sondern
  über Nutzerüberschreibungen (Quiz-Zeitverlängerung) auf der Zielinstanz —
  nur Doku/Hinweis, keine Kurslogik.

## Golden-Template-Fakten (echtes Moodle-4.5-Backup, 2026-07-17)

- group-Bedingung `{"type":"group","id":N}`, Negation `{"op":"!|","c":[…]}`,
  date `{"type":"date","d":">=","t":<unix>}` — Restore remappt Gruppen-IDs
  über das `group`-Mapping, date verschiebt der Kurs-Offset.
- Gruppen wandern über `groups.xml` + Root-Setting `groups=1`; **inforef
  bleibt LEER** (das Konzeptpapier vermutet inforef-Pflicht — das echte
  Backup widerlegt das).
- Kategorien-Gewichte: `aggregationcoef2` + `weightoverride=1` am
  **Kategorie-Item** (itemtype `category`, iteminstance=Kategorie,
  aggregation 13 = natürlich).
- Symbolische Referenzen im Builder: `ref` (grade→Quiz-idnumber), `cmref`
  (completion→Aktivitäts-idnumber), `groupref` (group→spec.groups-id).

## Präzisierung gegenüber dem Konzeptpapier

B.7.4 („Testnutzer B sieht keine Overlay-Elemente") widerspricht der
normativen Semantik B.3.5: Wer NICHT in der Praxis-Gruppe ist, sieht die
Kompensation — auch Testnutzer B ohne Gruppen. Umgesetzt ist B.3.5
(didaktisch korrekt: ohne nachgewiesene Praxiserfahrung → kompensierende
Anschauung); der Abnahmetest dokumentiert das explizit.

## Pipeline & Gates

```
build_modular.py     modular.json -o course.json     # Module -> Sections
                                                     #  + <course>.modmap.json
build_simulation.py / make_materials.py              # wie gehabt (optional)
build_mbz.py         … --wwwroot …                   # groups.xml, Kategorien,
                                                     # group/date/completion-Refs
validate_mbz.py      kurs.mbz                        # + group/date/Kriterium-Checks
simulate_modular.py  kurs.mbz kurs.modmap.json       # PFLICHT: B.7-Abnahme
```

`simulate_modular.py` prüft statisch an der gebauten mbz: Kategorien-
Entkopplung, Diagnose-Gate, Level-Abdeckung 0–100, Testnutzer A/B/C,
Konvergenz-OR, Remediation-/Freischalt-Kanten, ein Testpaar je aktivem
Overlay, Gruppen-Konsistenz. `check_delivery.py` erkennt das Modell an
`*.modmap.json` automatisch. E2E-Referenz: 22/22 PASS im Moodle-4.5-Lab
mit echten Nutzern A/B/C inkl. Beweis „Diagnose 30→95 ändert die Kursnote
nicht" (2026-07-18, Demo `Moodle-Kurse/motorschutz-diagnose/`).
