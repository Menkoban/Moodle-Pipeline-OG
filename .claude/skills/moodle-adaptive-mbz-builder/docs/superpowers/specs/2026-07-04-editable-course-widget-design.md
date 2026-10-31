# Design: Bearbeitbares Kurs-Widget für den moodle-mbz-builder-Skill

**Datum:** 2026-07-04
**Status:** Vom User freigegeben (Ansatz A, Chat vom 2026-07-04)

## 1. Ziel

Nach der Kurs-Generierung zeigt Claude den Kurs in einem **interaktiven,
bearbeitbaren Inline-Widget** (via `mcp__visualize__show_widget`). Der Autor
editiert dort klassisch (Texte, Felder) **und** KI-gestützt (Buttons pro
Baustein) und kann die **Struktur** verändern (Sektionen/Aktivitäten
hinzufügen, löschen, umbenennen, umsortieren). Erst auf ausdrückliche Aktion
„Fertigstellen" baut Claude die finale `.mbz` (inkl. Materialien, Validierung,
Vorschau).

## 2. Entscheidungen (vom User bestätigt)

1. **Voller Struktur-Editor** — nicht nur Textfelder.
2. **Nur im Claude-Workflow** — kein Standalone-Modus; Rückkanal via
   `sendPrompt`, Rebuild durch Claude.
3. **KI-Assist von Anfang an** — pro Baustein kontextuelle KI-Buttons.
4. **(a)** SVG-Diagramme in v1 nur per KI-Neugenerierung oder Roh-Markup
   bearbeitbar — **kein** visueller Zeichen-Editor.
5. **(b)** `.mbz` wird **nur beim Fertigstellen** gebaut, nicht bei jedem
   Zwischenspeichern. Zwischenstände aktualisieren nur `course.json`.
6. **Video-Recap:** Button „🎬 Video-Recap erstellen" im Kurs-Recap-Baustein
   als Hook (`action: "video_recap"`); die eigentliche
   NotebookLM-Automatisierung ist ein **separates Folge-Teilprojekt**
   (siehe §9).

## 3. Architektur (Ansatz A — „Fat Widget")

Das Widget hält den **kompletten editierbaren Kurs** als JS-Objekt im
Browser-State. Lokale Edits (Tippen, Umsortieren, Hinzufügen, Löschen) passieren
ohne Round-Trip. Nur bewusste Aktionen senden via `sendPrompt(...)` einen
**Envelope** mit dem vollständigen aktuellen Kurszustand an Claude. Claude
verarbeitet, schreibt `course.json` auf die Platte (Single Source of Truth
zwischen den Renders) und ruft `show_widget` mit dem neuen Stand erneut auf.

**Warum Voll-Zustand statt Diffs:** Beim Neu-Rendern gehen ungesendete lokale
Edits verloren. Reist immer der ganze Kurs mit, kann nichts driften. Diffs
(Ansatz B) bleiben eine spätere Token-Optimierung.

### Datenfluss

```
course.json ──build_editor_widget.py──▶ Widget-HTML ──show_widget──▶ Browser
     ▲                                                     │
     │            Envelope {action, course, …}             │ sendPrompt
     └────────────── Claude verarbeitet ◀──────────────────┘
          (save → schreiben+rerender | ai_assist → generieren+einsetzen
           | finalize → volle Pipeline | video_recap → Folgeprojekt-Hook)
```

## 4. Envelope-Protokoll (Widget → Claude)

Das Widget sendet **ein JSON-Objekt in einem Markdown-Codeblock**, damit Claude
es robust parsen kann:

```json
{
  "widget": "mbz-course-editor",
  "action": "save | ai_assist | finalize | video_recap",
  "course": { …vollständige Kursdefinition… },
  "target": {"section": 2, "activity": 1, "field": "content"},
  "instruction": "Schreibe das Infoblatt einfacher, A2-Niveau"
}
```

- `course` ist **immer** der komplette aktuelle Stand (inkl. ungesendeter
  Edits). Bilder bleiben **Pfad-Referenzen** — niemals base64 im Envelope.
- `target` + `instruction` nur bei `ai_assist`.
- `action`-Semantik:
  - **save** — Claude schreibt `course.json`, validiert leichtgewichtig
    (JSON-Schema-Check), rendert Widget neu. Kein Build.
  - **ai_assist** — Claude führt die Instruktion auf dem Ziel-Baustein aus
    (Text generieren/ändern, Quizfrage ergänzen, SVG neu erzeugen …), schreibt
    `course.json`, rendert neu.
  - **finalize** — volle Pipeline: `autofit_svg` → `validate_svg` →
    `make_materials` → `build_mbz` → `validate_mbz` → `preview_mbz`.
    Deliverables: `.mbz` + Vorschau-HTML (+ PDFs/PPTX).
  - **video_recap** — Hook für Folgeprojekt; v1-Verhalten: Claude erklärt den
    Stand des Teilprojekts bzw. startet den NotebookLM-Flow, sofern verfügbar.

## 5. Neue Komponente: `scripts/build_editor_widget.py`

Analog zu `preview_mbz.py`: nimmt `course.json`, emittiert **ein
selbstständiges Widget-HTML** (kein DOCTYPE/head/body — `show_widget`-Format).

- **Struktur-UI:** Zwei-Ebenen-Akkordeon wie die Preview (Sektion → Aktivität),
  plus je Ebene: ▲▼ (umsortieren), 🗑 (löschen), ✏️ (umbenennen), ＋ (neue
  Sektion / neue Aktivität mit Typ-Auswahl aus den unterstützten Typen).
- **Feld-Editoren je Typ:** name, intro/content (Textarea mit Roh-HTML),
  Quiz-Fragen/-Antworten/-Feedback, Rubrik/Auftragstext (`assign`),
  Glossar-Einträge, choice-Optionen, feedback-Items, url, Datei-Pfade
  (read-only Anzeige + Pfad editierbar).
- **KI-Assist-Buttons je Typ** (senden `ai_assist`-Envelope):
  - Seite/Infoblatt: neu schreiben · kürzen · vereinfachen · Merke-Box
    ergänzen · Diagramm neu generieren
  - Quiz: Frage ergänzen · Distraktoren verbessern · Feedback schreiben
  - Assign: Auftrag schärfen · Rubrik generieren
  - Glossar: Begriffe ergänzen
  - Freitext-Feld „Eigener KI-Auftrag" auf jedem Baustein
- **Kopf-Aktionen:** „💾 Speichern" (save), „✅ Kurs fertigstellen → .mbz"
  (finalize); im Kurs-Recap-Baustein „🎬 Video-Recap erstellen" (video_recap).
- **Dirty-Indikator:** ungesendete Änderungen sichtbar markieren.
- SVGs werden **angezeigt** (inline gelesen beim Generieren), aber der
  Envelope referenziert sie als Pfad.
- CLI: `python build_editor_widget.py course.json -o editor_widget.html`.

## 6. Skill-Dokumentation (SKILL.md-Erweiterung)

Neuer Abschnitt „Interaktiver Kurs-Editor (Widget)": wann rendern (nach jeder
Kursgenerierung als Standard-Schritt vor dem Build), wie jeder `action`-Typ
abzuarbeiten ist (Handler-Anleitung für Claude), Envelope-Format,
Fehlerverhalten (invalider Envelope → Widget mit Fehlermeldung neu rendern,
Kurs-Stand aus `course.json`).

## 7. Fehlerbehandlung

- **Envelope unparsebar / Schema-Verstoß:** Claude behält die letzte gültige
  `course.json`, rendert das Widget daraus neu und zeigt die Fehlermeldung im
  Widget-Kopf an.
- **`finalize` schlägt fehl** (Validator rot): Claude repariert, wo eindeutig,
  sonst rendert er das Widget mit Fehlerhinweis am betroffenen Baustein.
- **Widget-Größe:** Kurse mit sehr vielen Aktivitäten können das
  `widget_code`-Limit sprengen → Generator misst die Ausgabegröße und schaltet
  ab Schwellwert auf „Lazy-Sektionen" (Inhalte erst beim Aufklappen aus einem
  JSON-Block im selben Dokument gerendert). Bilder nie base64 im Editor.

## 8. Tests

- **Python-Ebene (pytest):** Envelope-Roundtrip — `course.json` →
  `build_editor_widget.py` → im HTML eingebettetes Kurs-JSON ist
  inhaltsgleich; Struktur-Ops-freie Regeneration ist idempotent; alle
  unterstützten Typen bekommen einen Feld-Editor; Größen-Fallback greift.
- **Spike zuerst (manuell, mit User):** Mini-Widget mit einem Feld beweist den
  Loop sendPrompt → Claude → Re-Render, **bevor** der Voll-Editor gebaut wird.
- **End-to-End (manuell):** Beispielkurs → editieren → finalize → `.mbz`
  restauriert in Moodle.

## 9. Folge-Teilprojekt: NotebookLM-Video-Recap (separat spezifizieren)

Nicht Teil dieser Spec, aber hier verankert:

- **`scripts/export_course_dossier.py`** (kann vorgezogen werden, rein lokal):
  konsolidierter Kurs-Export (Markdown, ein Dokument) als NotebookLM-Quelle.
  Filter: Handlungssituation, Lernziele, alle Seiten/Bücher, Auftragstext,
  Glossar **rein**; Quiz-Lösungen+Feedback, verborgene Lehrkraft-Sektion,
  Organisatorisches **raus**.
- **Browser-Automatisierung** (claude-in-chrome): User loggt sich **selbst**
  ein (keine Zugangsdaten an Claude), Claude steuert die Session: Notebook
  anlegen → Dossier hochladen → Video-Overview generieren → MP4 herunterladen
  → als `resource` in den Kurs-Recap einsetzen (ersetzt den Platzhalter).
- **Best-Effort:** UI-Automatisierung ist fragil; Fallback = Platzhalter
  bleibt. Erster Schritt ist ein manuell begleiteter Spike.

## 10. Nicht-Ziele (v1)

Standalone-Editor ohne Claude · WYSIWYG/visueller SVG-Editor ·
Round-Trip pro Tastendruck · `.mbz`-Build bei Zwischenspeichern ·
Book-Kapitel-Inline-Bilder (bestehende Skill-Grenze).
