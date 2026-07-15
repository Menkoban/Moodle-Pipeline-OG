# Spec — Recap-Video zeigt/bespricht die Kurs-Diagramme (O1)

**Datum:** 2026-07-15
**Skill:** `moodle-mbz-builder`
**Strang:** O1 von ~6 (siehe „Geparkte Stränge" in
`2026-07-15-diagramm-validatoren-design.md`)
**Status:** Design → Umsetzung in diesem Durchlauf

## Kontext & Motivation

`references/notebooklm-video-recap.md` beschreibt den erprobten Ablauf für das
Kurs-Recap-Video: `scripts/export_course_dossier.py` erzeugt EIN
Markdown-Dossier aus `course.json`, das als „Kopierter Text" in NotebookLM
eingebracht wird (Datei-Upload aus der Sandbox ist blockiert). NotebookLM
generiert daraus eine Videoübersicht.

**Problem:** Das Dossier ist reiner Text. Die Kurse enthalten aber sorgfältig
gebaute SVG-Diagramme (Aufbau/Anatomie, Sicherheits-Piktogramme,
Schaubilder — siehe `references/course-design.md` Abschnitt 6). NotebookLM
„sieht" diese Diagramme nicht, wenn nur der Dossier-Text als Quelle dient —
das Video kann sie also weder zeigen noch inhaltlich referenzieren.

**Locked direction (Auftrag):** robuster Weg zuerst — das Dossier wird um
**Textbeschreibungen** der Diagramme angereichert, damit die Video-Narration
zumindest darauf Bezug nehmen kann („Wie im Diagramm zu Aufbau und Anatomie
gezeigt, …"). Ein echter Datei-Upload der Original-SVGs/PDF-Vorschau bleibt ein
**sekundärer, manueller** Schritt (siehe §4) — keine Browser-Automatisierung
dafür.

## Ziele / Nicht-Ziele

**Ziele**
- `export_course_dossier.py` hängt pro Abschnitt einen Block „Abbildungen in
  diesem Modul" an, wenn Seiten dieses Abschnitts `.svg`-Diagramme referenzieren
  (`images`-Feld der `page`-Aktivität).
- Beschreibung je Diagramm mit klarer Prioritätskette: `<title>`/`<desc>` des
  SVG > sichtbare Textlabels (`<text>`) > lesbar gemachter Dateiname.
- Robust: fehlende Datei → übersprungen (kein Crash, keine Erwähnung); kaputtes
  SVG → Dateiname-Fallback; Kurs ganz ohne Diagramme → **identischer** Output
  wie vor der Änderung (additiv).
- `references/notebooklm-video-recap.md` dokumentiert die Erweiterung + den
  optionalen manuellen Upload-Schritt.

**Nicht-Ziele**
- Kein echter Bild-/PDF-Upload per Browser-Automatisierung an NotebookLM (die
  „Kopierter Text"-Route bleibt der robuste Standardweg, siehe bestehende
  Spike-Erkenntnis in `notebooklm-video-recap.md`: Datei-Upload aus der
  Claude-Sandbox ist unzuverlässig, nur session-geteilte Dateien funktionieren).
- Keine Bildbeschreibung per Vision-Modell/OCR — reine strukturelle SVG-Analyse
  (Text-Inhalt), kein zusätzlicher API-Call, keine neue Abhängigkeit über das
  bereits genutzte `svg_geometry.py`/`reportlab` hinaus.
- Keine Änderung an `SKILL.md` oder `references/course-design.md` (separat
  integriert).

## 1 · Woher kommen die Diagramme im Dossier-Kontext?

Diagramme werden laut `references/course-spec.md` und `course-design.md`
Abschnitt 6 als `.svg`-Dateien in der `images`-Liste einer `page`-Aktivität
geführt und im HTML-`content` via `@@PLUGINFILE@@/<dateiname>` referenziert
(Beispiel: `assets/fewshot_bohrmaschine.json`). `book`-Kapitel binden aktuell
keine echten Dateien ein (kein `images`-Wiring in `build_mbz.py`s `b_book`) —
daher beschränkt sich diese Erweiterung bewusst auf `page`-Aktivitäten, dieselbe
Quelle, die auch tatsächlich ins `.mbz` eingebettet wird.

Nur `.svg`-Einträge zählen als „Diagramm" — andere Bildtypen in `images` sind in
der Praxis Kachel-/Dekofotos, keine Fachdiagramme.

## 2 · Beschreibungs-Priorität (`describe_svg(path)`)

1. **`<title>`/`<desc>`** — direkte Kind-Elemente von `<svg>`, Standard-SVG-
   Metadaten. Werden zusammengefügt: `"Titel — Beschreibung"`.
2. **Sichtbare Textlabels** — falls kein `<title>`/`<desc>`: bis zu 6
   `<text>`-Inhalte in Dokumentreihenfolge (Duplikate entfernt), per
   `svg_geometry.load()` + `svg_geometry.collect_boxes()` (dieselbe
   Text-Extraktion, die auch `validate_svg.py`/`autofit_svg.py` nutzen — inkl.
   `tspan`-Konkatenation). **Praxisrelevant:** die vorhandenen SVGs im Skill
   (`assets/*.svg`) haben aktuell **kein** `<title>`, sondern beschriften über
   `<text>` — dieser Zweig greift also für den heutigen Bestand.
3. **Dateiname** — letzter Rückfall (`_`/`-` → Leerzeichen), z. B.
   `bohrmaschine_aufbau.svg` → „bohrmaschine aufbau". Auch der Rückfall, wenn
   die Datei existiert, aber nicht parsbar ist, oder wenn `svg_geometry`
   mangels `reportlab` gar nicht importierbar ist.
4. **Datei fehlt** (`os.path.exists` false) → `None`, das Diagramm wird
   komplett übersprungen (kein Eintrag, kein Crash).

`svg_geometry` wird **lazy/optional** importiert (`try/except`, analog zum
bestehenden Muster in `build_mbz.py`s SVG-Check): fehlt `reportlab`, degradiert
`describe_svg()` auf den Dateiname-Rückfall statt den gesamten Dossier-Export
zu blockieren.

## 3 · Platzierung im Dossier

Pro **Abschnitt** (`##`-Überschrift im Dossier) wird nach den regulären
Aktivitäts-Blöcken ein zusätzlicher Block angehängt, nur wenn mindestens ein
Diagramm im Abschnitt existiert:

```markdown
## Abschnittsname
...reguläre Aktivitäts-Inhalte...

### Abbildungen in diesem Modul

- **bohrmaschine_aufbau.svg** (Aufbau): Aufbau einer Standbohrmaschine, Spindel, Bohrfutter, Tisch, Ständer
```

Kein Diagramm im Abschnitt → kein Block, **kein** Unterschied zum bisherigen
Output. Kein Diagramm im ganzen Kurs → Dossier ist byte-identisch zu vorher.

## 4 · Sekundärer manueller Schritt: Material-PDF/Vorschau als Extra-Quelle hochladen

Die robuste Standardroute bleibt „Kopierter Text" für das Dossier (Schritt 3 in
`notebooklm-video-recap.md`). **Optional**, wenn der Nutzer möchte, dass
NotebookLM die Diagramme *tatsächlich sieht* statt nur textuell referenziert zu
bekommen: der Nutzer lädt zusätzlich die Material-PDFs (`make_materials.py`-
Output, enthält die SVGs eingebettet) oder eine Vorschau-Datei manuell als
weitere NotebookLM-Quelle hoch (**„Quellen hinzufügen → Dateien hochladen"**).

Dieser Schritt bleibt **manuell** und wird **nicht automatisiert**:
- Datei-Upload aus der Claude-Sandbox an NotebookLM ist laut bestehender
  Spike-Erkenntnis unzuverlässig (nur session-geteilte Dateien funktionieren
  zuverlässig über die Browser-Tools).
- Keine neue Browser-Automatisierung für diesen Pfad — das widerspräche der
  Locked Direction dieses Strangs.
- Der Nutzer entscheidet pro Kurs, ob ihm der Zusatzaufwand (echte Bilder als
  Quelle) den Mehrwert wert ist; die Textbeschreibung aus §2/§3 liefert bereits
  ohne diesen Schritt einen Mehrwert.

## 5 · Tests

Neue `tests/test_dossier_diagrams.py`:

| Fixture | Erwartung |
|---|---|
| Seite mit SVG, `<title>`+`<desc>` gesetzt | Dossier enthält `### Abbildungen in diesem Modul` + Titeltext |
| Seite mit SVG, nur `<text>`-Labels | Dossier enthält die Textlabels |
| Seite ohne `images` | Dossier enthält `Abbildungen in diesem Modul` **nicht** (Regression) |
| `images`-Pfad zeigt auf fehlende Datei | kein Crash, kein Eintrag, `describe_svg()` gibt `None` |
| `images`-Eintrag ist kein `.svg` (z. B. `.png`) | wird ignoriert, kein Diagramm-Block |
| SVG ohne `<title>`/`<desc>`/`<text>` | Dateiname-Fallback (`leere_grafik.svg` → „leere grafik") |
| echtes Asset `assets/bohrmaschine_aufbau.svg` (Regressions-Smoke) | liefert eine nicht-leere Beschreibung über den Text-Label-Fallback |

Bestehende `tests/test_export_dossier.py` bleibt unverändert grün (keine
Verhaltensänderung für den bisher abgedeckten Fall ohne `images`).

## Umsetzungsschritte

1. `scripts/export_course_dossier.py`: `describe_svg()`, `section_diagrams_md()`,
   Verdrahtung in `build_dossier()` (additiv, nach den Aktivitäts-Blöcken je
   Abschnitt).
2. `tests/test_dossier_diagrams.py`.
3. `references/notebooklm-video-recap.md`: Abschnitt zur Diagramm-Anreicherung
   + manuellem Upload-Fallback ergänzen (kein Eingriff in den erprobten
   Kern-Ablauf).
4. Diese Spec.

## Geparkt / Folge

- Ein echter, automatisierter Datei-Upload an NotebookLM (falls Google die
  Sandbox-Upload-Beschränkung künftig lockert) wäre eine spätere, eigene
  Iteration — nicht Teil dieses Strangs.
- `book`-Kapitel bekommen aktuell kein `images`-Wiring in `build_mbz.py`;
  sollte sich das ändern, müsste `section_diagrams_md()` um `book` erweitert
  werden (heute bewusst nicht, um keine Diagramme zu „finden", die gar nicht
  im `.mbz` landen).
- Übrige Stränge: O2 Pipeline-Speed, O3 Sims, O4 Didaktik-Profile.
