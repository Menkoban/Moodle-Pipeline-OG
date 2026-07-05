# Didaktik-Leitfaden: Moodle-Kurse nach dem 5-Ebenen-Modell (Rode)

Diese Datei ist das **didaktische Gehirn** des Skills. Sie liefert das Strukturmodell,
die Pflicht-Sequenz und die Bau-Konventionen, nach denen ein hochwertiger,
vollständig ausgearbeiteter Kurs für die **berufliche Bildung** entsteht – und
übersetzt sie in konkrete Felder der Kurs-JSON. Lies sie, bevor du einen Kurs baust.

> **Vor dem Bauen zuerst fragen (Kurs-Steckbrief).** Kläre die relevanten
> Steckbrief-Punkte mit dem Nutzer, *bevor* du den Kurs schreibst – gebündelt,
> nur wo sinnvoll, mit Default-Vorschlag zum Bestätigen (die vollständige Frageliste
> steht in `SKILL.md`, Schritt 1 „Intake first"). Erst mit diesen Antworten sitzt
> die Handlungssituation, das Niveau und der Schwerpunkt wirklich passgenau.

**Leitmodell:** das 5-Ebenen-Strukturmodell für Moodlekurse nach Henning Rode
(Lernelement → Lernbaustein → Lernabschnitt → Lerneinheit/Modul → Lernkurs).
Gold-Standard-Beispiel, das jeden Punkt unten umsetzt: `assets/fewshot_bohrmaschine.json`
(mit eingebetteten SVG-Diagrammen und `material`-Flags). Nutze es als Few-Shot-Vorlage.

## Inhalt
1. Leitprinzipien
2. Das 5-Ebenen-Strukturmodell (Wording)
3. Pflicht-Sequenz der Lernabschnitte (mit Zeitbudgets)
4. Lernbaustein → Aktivität (Mapping)
5. Der Infoblatt-Bauplan
6. Diagramme selbst erzeugen und einbetten
7. Lernziele, Handlungssituation, Praxisauftrag, Feedback (Schreibmuster)
8. Downloadbare Materialien + Bau-Pipeline
9. Mengen-Kalibrierung (Inhalt ↔ Zeit)
10. Qualitäts-Checkliste

---

## 1. Leitprinzipien

- **Handlungsorientierung:** Jedes Modul ist um eine **Handlungssituation** (ein
  echter beruflicher Auftrag/Fall) herum gebaut und mündet in ein
  **Handlungsprodukt** (etwas, das die Lernenden erstellen).
- **Kompetenzorientierung:** Ziele beschreiben *beobachtbares Können*, nicht „kennen".
- **Aktiv statt konsumierend + formatives Feedback:** jede Phase hat eine
  aktivierende Komponente (Frage, Selbsttest, Auftrag) mit sofortiger Rückmeldung.
- **Chunking:** ein Thema pro Lernabschnitt/Infoblatt; kurze, klare Einheiten.
- **Niedrigschwelligkeit:** einfache Sprache, viel Visualisierung (besonders für
  AV/BFS-Gruppen) – Diagramme tragen den Inhalt mit, nicht nur Text.

Die **vollständige Handlung** (Informieren → Planen → Entscheiden → Ausführen →
Kontrollieren → Bewerten) und der **AVIVA-Bogen** sind weiter die *didaktische
Begründung* – sie spielen sich vor allem im Lernabschnitt **Anwendung** ab
(Abschnitt 3). Plane rückwärts (Constructive Alignment): erst Ziele, dann Prüfung
(Praxisauftrag/Test), dann Input.

---

## 2. Das 5-Ebenen-Strukturmodell (Wording)

Verbindliches Vokabular. Es bildet sich **eins zu eins** auf die Skill-Architektur ab:

| Ebene | Begriff | Beispiele | Skill / Moodle |
|---|---|---|---|
| 1 | **Lernelement** | Überschrift, Text, Bild, Hinweis, Frage, Antwort, Video, Dokument, Quellenangabe | HTML-Inhalt *innerhalb* einer Aktivität |
| 2 | **Lernbaustein** | Handlungssituation, Informationsblatt, Arbeitsblatt/Test, Dateiablage, Videozusammenfassung, Glossar | eine `activity` (Aktivität/Material) |
| 3 | **Lernabschnitt** | Einführung, Grundlagen, Vertiefung, Kurs-Recap, Glossar, Material für Lehrkräfte | eine `section` (= Moodle-Kachel) |
| 4 | **Lerneinheit / Modul** | „Modul Lenksysteme" (~2 Unterrichtsstd.) | ein Kurs = **eine `.mbz`** |
| 5 | **Lernkurs** | „Kurs digitale Landtechnik" (mehrere Module) | Moodle-Kursbereich (über einer .mbz) |

**Konventionen / aufgelöste Mehrdeutigkeiten:**
- Eine **Überschrift bleibt ein Lernelement** (sie trägt den Lernpfad).
- **Glossar** ist auf Ebene 2 ein Lernbaustein (die Glossar-Aktivität); ein
  Lernabschnitt darf nach seinem dominanten Baustein benannt werden (Abschnitt
  „Glossar" enthält den Baustein „Glossar"). Das ist kein Widerspruch, sondern
  Namenskonvention.
- Standard-Modulumfang ≈ **2 Unterrichtsstunden** (Selbstlernen + betreute Praxis).
  Mehrere Module bündelt man über den Kursbereich zum Lernkurs.

---

## 3. Pflicht-Sequenz der Lernabschnitte (mit Zeitbudgets)

Die Sektionen eines Moduls folgen dieser Reihenfolge. Index 0 ist ein kurzer
„Über dieses Modul"-Abschnitt (Begrüßung + Ablauf), danach die nummerierten
Lernabschnitte:

| # | Lernabschnitt | Zeit | Inhalt |
|---|---|---|---|
| 1 | **Einführung** | ~5 min | Handlungssituation + 4–5 Lernziele + niedrigschwellige Vorwissens-Abstimmung |
| 2 | **Grundlagen** | ~25 min | einordnendes Infoblatt + Aufbau/Begriffe (mit Diagramm) + formativer Vorwissens-Check |
| 3 | **Vertiefung** | ~50 min | mehrere Infoblätter (je mit Diagramm) + 2 Arbeitsblatt-Tests |
| 4 | **Anwendung / Handlungsprodukt** | — | Arbeitsplan-Vorlage + **Praxisauftrag (`assign`) mit Rubrik** + Begleit-Forum; (Sicherheits-Kurzcheck als Gate, wo sinnvoll) |
| 5 | **Kurs-Recap** | ~10 min | „Das Wichtigste in Kürze" + Videozusammenfassung (Platzhalter) + Selbsteinschätzungstest |
| 6 | **Glossar** | — | Glossar-Baustein mit echten Fachbegriffen |
| 7 | **Material für Lehrkräfte** | — | **verborgen** (`"visible": 0`): didaktischer Leitfaden + Druck-/Editiermaterial (auto-generiert) |

Die Sequenz *Einstieg → Vorwissen → Input → Handlung → Üben/Feedback → Reflexion*
muss erkennbar bleiben. Nicht jedes Modul braucht alle Abschnitte in voller Länge,
aber Einführung, Vertiefung, Anwendung und Recap sind Pflicht.

---

## 4. Lernbaustein → Aktivität (Mapping)

| Lernbaustein | Skill `type` | Hinweis |
|---|---|---|
| Handlungssituation | `page` (oder `label`) | Überschrift + ½-Seite Falltext + Bild + Leitfrage |
| Lernzielformulierung | `page` | Teil der Einführung, 4–5 operatorbasierte Ziele |
| Informationsblatt | `page` mit `material:true` | Infoblatt-Bauplan (Abschnitt 5), Diagramm eingebettet |
| Arbeitsblatt / Test | `quiz` (geschlossene Fragen) | an Lernzielen ausgerichtet, formatives Feedback |
| Dateiablage | `resource` / `folder` | echte Datei; PDF/PPTX werden auto-generiert (Abschnitt 8) |
| Videozusammenfassung | `label` (Hinweis) + Platzhalter | Video extern via NotebookLM, **nicht** vom Skill erzeugt |
| Glossar | `glossary` (mit `entries`) | Fachbegriffe, alphabetisch |
| Praxisauftrag (Handlungsprodukt) | `assign` | Vorgehen + transparente Rubrik im Auftragstext |
| Reflexion / Evaluation | `feedback` / `page` | unbenotet |

**Verb-Konsistenz:** Ein Ziel mit „aufbauen/durchführen" wird per **Aufgabe**
geprüft, nicht per Multiple-Choice. Wissen/Verstehen per **Quiz**.

---

## 5. Der Infoblatt-Bauplan

Ein Infoblatt ist eine `page` mit `"material": true`. Jedes Infoblatt folgt
diesem Aufbau (siehe Few-Shot):

1. **Kopfleiste** – farbiger Balken mit „Infoblatt · &lt;Titel&gt;".
2. **Kurze Einleitung** – ein, zwei Sätze, worum es geht.
3. **Erklär-Fließtext (Pflicht, Mindestumfang)** – der eigentliche Lehrtext.
   **Mindestens 2–3 kurze Absätze, zusammen ~120–200 Wörter** in einfacher
   Sprache. Er folgt dem Dreischritt **Was → Wie → Warum/Praxisbezug**:
   (a) *Was* ist es / Definition, (b) *Wie* funktioniert es / wie geht man vor,
   (c) *Warum* ist es wichtig bzw. wo begegnet es im Berufsalltag.
   **Ein einzelner Satz oder nur Stichpunkte sind zu wenig** – Stichpunkte/Tabelle
   kommen zusätzlich (Punkt 5), nicht statt des Fließtexts. Das Diagramm ersetzt
   den Text nicht; es ergänzt ihn.
4. **Eingebettetes Diagramm** – `<img src='@@PLUGINFILE@@/…svg'>` (Abschnitt 6).
5. **Stichpunkte oder Tabelle** – die Kernfakten kompakt.
6. **Merke-Box** – ein hervorgehobener Sicherheits-/Kernhinweis.

HTML-Muster (Attribute mit **einfachen** Anführungszeichen, damit die JSON-Strings
ohne Escaping bleiben):

```html
<div style='border:1px solid #c9ccd1;border-radius:6px;overflow:hidden;font-family:Arial,sans-serif;'>
  <div style='background:#1d6e56;color:#fff;padding:10px 14px;font-size:18px;font-weight:bold;'>Infoblatt · Titel</div>
  <div style='padding:14px 16px;'>
    <p style='margin-top:0;'>Kurze Einleitung …</p>
    <p style='background:#f7f7f4;border-left:3px solid #1d9e75;padding:8px 12px;'>Erklär-Fließtext …</p>
    <div style='text-align:center;margin:10px 0;'><img src='@@PLUGINFILE@@/diagramm.svg' style='max-width:100%;height:auto;'></div>
    <table border='1' cellpadding='6' style='border-collapse:collapse;width:100%;'>…</table>
    <div style='background:#fbeec9;border-left:4px solid #ba7517;padding:8px 12px;'>⚠ <b>Merke:</b> …</div>
  </div>
</div>
```

Zusätzlich `"material_bullets": ["…","…"]` setzen (Kernpunkte für die
auto-generierten PDF/PPTX; ohne werden sie aus dem Content extrahiert).

---

## 6. Diagramme selbst erzeugen und einbetten

- **Selbst zeichnen als SVG** (du kannst SVG direkt schreiben – kein Rasterizer
  nötig). Beschriftete Fachdiagramme: Aufbau/Anatomie eines Bauteils,
  Schritt-für-Schritt-Ablauf, Richtig/Falsch-Vergleich, Fehlerbilder,
  Sicherheits-Piktogramme.
- **Stil nach Inhalt:** sachlich-technisch (Grau + Akzente) für Aufbau/Anatomie;
  farbig-piktografisch (Grün=Gebot, Rot=Verbot) für Sicherheit/Ablauf.
- **Einbetten als Bilddatei**, nie als Inline-`<svg>` (Moodles HTMLPurifier
  entfernt inline-SVG): Datei in `images` der Seite, im Content via
  `@@PLUGINFILE@@/<dateiname>` referenzieren (Details: SKILL.md → „Embedding
  images inline in a page").
- **Keine Fotos generieren** – wenn echte Fotos nötig sind, Platzhalter mit
  Bildprompt setzen; der Autor/die Lehrkraft ersetzt sie später.

### SVG-Autorenregeln (gegen abgeschnittene Ränder & Überlappungen)

Hand-gezeichnetes SVG hat zwei typische Defekte, weil man Textbreiten beim
Schreiben nur schätzt: Inhalt wird am `viewBox`-Rand **abgeschnitten** oder
Beschriftungen **überlappen** und verdecken sich. Halte diese Regeln ein – und
prüfe sie danach automatisch (nicht nur per Augenschein):

- **Kein Styling-`<tspan>` innerhalb eines `<text>`** (z. B. `<tspan
  font-weight="bold">…</tspan>` ohne eigenes `x`). svglib rückt den x-Cursor
  über `<tspan>` **nicht** weiter → der fette Teil landet auf dem folgenden Text
  („eibfaidhe genau EIN Weg"). Nutze **getrennte `<text>`-Elemente** oder mach
  das ganze `<text>` fett.
- **Lange Beschriftungen in eine Legenden-Box**, nicht als frei schwebende
  Leader-Line-Labels am Rand – Legenden lassen sich bündig setzen und laufen
  nicht aus dem Rahmen. Kurze **Tags** (B1, S2, …) direkt ans Objekt.
- **Innenrand einhalten:** mind. ~10 px Abstand von Text zum `viewBox`-Rand.
- **Text muss in seine Box passen** (Merke-/Legenden-Kästen): einzeiliger SVG-Text
  bricht nicht um; ist er breiter als das Rechteck, läuft er rechts heraus (der
  Kasten wächst NICHT mit, `autofit` vergrößert nur die viewBox). Box breit genug
  zeichnen, Text kürzen **oder** auf zwei `<text>`-Zeilen umbrechen und die Box
  höher machen. `validate_svg.py` meldet Text, der aus seiner umschließenden Box läuft.
- **Dekorative Linien und Pfeile nicht durch Beschriftungen legen** (z. B. ein
  Rotations- oder Leserichtungs-Pfeil quer durch ein Label). Beschriftungslinien
  dürfen *am* Text enden, aber nicht hindurchlaufen. `validate_svg.py` meldet
  Linien **und gekrümmte Pfade** (Q/C-Kurven, Bögen — typisch: Rotationspfeile),
  die einen Text kreuzen (Leader, die am Text enden, sind ausgenommen), sowie
  **gefüllte Polygone** (Pfeilspitzen), die ein Label überdecken (SHAPE-Check).
- **Renderpfad:** svglib → `renderPDF` (so rendert der Skill); das `rlPyCairo`-
  Backend von `renderPM` ist nicht installiert – nicht darauf verlassen.
- **Keine Sonderzeichen-Glyphen in SVG-`<text>`**, die die Helvetica-Basisschrift
  nicht hat (⚠ ✅ ⛔ Emoji) oder kombinierende Diakritika (Überstrich für
  Negation) – sie werden im gerasterten PDF/PPTX zu leeren Kästchen. **Zeichne**
  sie stattdessen (z. B. Negationsstrich als `<line>` über dem Signal), oder lass
  das Symbol weg. Pfeile (→ ↑) und der Malpunkt · rendern dagegen. `validate_svg.py`
  warnt vor riskanten Glyphen.

**Pflicht-Prüfung (deterministisch, misst echte Textbreiten):**

```bash
python <skill-dir>/scripts/autofit_svg.py   assets/          # wächst viewBox passgenau -> nie mehr abgeschnitten
python <skill-dir>/scripts/validate_svg.py  assets/ --strict # findet Überlappungen + Styling-tspan
```

`autofit_svg.py` löst das Abschneiden **strukturell** (viewBox umschließt den
gemessenen Inhalt inkl. Text + Rand; Hintergrund-Rechteck wächst mit).
`validate_svg.py` meldet verbleibende Überlappungen und tspan-Fallen. Beide
akzeptieren einzelne `.svg`, einen Ordner **oder** eine `course.json` (prüft
alle referenzierten Diagramme). Führe sie aus, **bevor** du `make_materials.py`
startest – dann sind die Diagramme in Kurs, PDF und PPTX gleichermaßen korrekt.

---

## 7. Lernziele, Handlungssituation, Praxisauftrag, Feedback (Schreibmuster)

**Lernziele** – Bauformel: „Die Lernenden können **[Operator] [Inhalt]
[Kontext/Kriterium]**." Verboten: *kennen, verstehen, wissen*. 4–5 Ziele pro Modul.

| Stufe | Operatoren |
|---|---|
| Erinnern | nennen, benennen, aufzählen, beschriften |
| Verstehen | beschreiben, erklären, zuordnen, einordnen |
| Anwenden | anwenden, durchführen, berechnen, montieren, einstellen, dokumentieren |
| Analysieren | analysieren, vergleichen, untersuchen, unterscheiden |
| Bewerten | begründen, beurteilen, auswählen und begründen |
| Erschaffen | planen, entwickeln, entwerfen, konzipieren |

**Handlungssituation** = Rolle + Betriebs-/Kundenkontext + konkretes Problem +
offene Leitfrage, mit Namen/Zahlen. *„Erste Woche im Praktikum bei Betrieb X.
Ihr Anleiter legt … Leitfrage: Wie gehen Sie vor?"*

**Praxisauftrag (`assign.intro`):** Ausgangssituation → Auftrag/Handlungsprodukt →
Vorgehen (nummeriert) → Rahmen (Zeit/Material) → Abgabe → **Bewertungskriterien als
HTML-Rubrik** (3–4 Kriterien × 3 Niveaus, abgeleitet aus den Ziel-Verben).

**Quizfragen mit Feedback:** Jede Frage braucht `generalfeedback` (Regel für alle)
**und** Feedback je Antwort; Distraktoren bilden **typische Fehlvorstellungen** ab.
Quiz braucht `overallfeedback` (Prozentbänder mit Feed-Forward). Nie nur „richtig/falsch".

**Reflexion & Transfer** (Recap): Rückblick aufs eigene Lernen + Transferauftrag,
an eine konkrete eigene Handlung im Betrieb gebunden.

---

## 8. Downloadbare Materialien + Bau-Pipeline

Infoblätter mit `"material": true` werden **automatisch** zu Download-Dateien:
`make_materials.py` erzeugt pro Infoblatt ein **PDF** (Druck – es bildet das
**vollständige Infoblatt** ab: Kopfleiste, Fließtext, Diagramm, Tabellen/Listen,
Merke-Box) und eine **PPTX** (editierbar) und sammelt alle PDFs + PPTX in der
verborgenen Lehrkräfte-Sektion. Das PDF wird **nicht** hinter die Seite gehängt –
im Kurs steht an der Stelle nur das Infoblatt selbst.

**Pipeline (Standard für jeden Kurs):**
```
autofit_svg.py        assets/                                # viewBox passgenau -> kein Clipping
validate_svg.py       course.json --strict                   # Überlappungen/tspan finden (vor make_materials!)
build_simulation.py   course.json -o course.sim.json         # nur falls Simulationen -> Datei-Ressourcen
make_materials.py     course.sim.json -o course.materialized.json  # PDF/PPTX + Einhängen
build_mbz.py          course.materialized.json -o course.mbz --wwwroot ...
validate_mbz.py       course.mbz
preview_mbz.py        course.materialized.json -o course_vorschau.html
--- danach IMMER: Video-Recap (NotebookLM) ---
export_course_dossier.py course.json -o dossier.md           # Quelle fürs Video
# NotebookLM-Flow (references/notebooklm-video-recap.md): Video erzeugen + herunterladen
set_recap_video.py    course.json --file recap.mp4           # Platzhalter ersetzen
# dann make_materials -> build_mbz -> validate -> preview ERNEUT (jetzt mit Video)
```
Die beiden SVG-Schritte laufen **zuerst**, damit die (korrigierten) Diagramme in
Kurs, PDF und PPTX identisch stimmen. `autofit_svg.py` musst du selbst ausführen
(es *ändert* die SVGs); die **Prüfung** läuft zusätzlich **automatisch** in
`make_materials.py` (vor dem Rastern) und `build_mbz.py` (jeder Build, nur Warnung;
`--strict-svg` bricht ab, `--no-svg-check` überspringt) – ein defektes Diagramm
rutscht also auch dann nicht durch, wenn man den Schritt vergisst.

**Der Video-Recap gehört zu jedem fertigen Kurs (Pflicht-Schritt).** Die
Videozusammenfassung im Kurs-Recap wird nicht lokal generiert, sondern über den
NotebookLM-Flow (`references/notebooklm-video-recap.md`) erzeugt und mit
`set_recap_video.py` eingebaut; danach wird der Kurs **neu gebaut**. Nur wenn in
der Session kein Browser/kein NotebookLM-Login verfügbar ist, bleibt der
Platzhalter stehen – dann den Nutzer informieren und das Video nachziehen.
Liefere immer `.mbz` **und** die HTML-Vorschau aus.

---

## 9. Mengen-Kalibrierung (Inhalt ↔ Zeit)

Faustzahl **~25 Wörter Lerninhalt pro Lernminute** (Diagramme und Quizfragen
tragen zusätzlich Zeit, die nicht in Wörtern steckt). Richtwerte:

| Lernabschnitt | Soll-Zeit | ~Text-Wörter |
|---|---|---|
| Einführung | 5 min | ~120 |
| Grundlagen | 25 min | ~600 |
| Vertiefung | 50 min | ~1000–1250 (mit Diagrammen/Tests) |
| Kurs-Recap | 10 min | ~250 |

Erzeuge **echten Inhalt** (Erklär-Fließtext + Diagramm + Stichpunkte je Infoblatt),
keine dünnen Hüllen. Prüfe die Mengen, bevor du auslieferst.

**Pro Infoblatt-Seite mindestens ~120–200 Wörter Erklär-Fließtext** (Abschnitt 5,
Punkt 3). Ein „schönes Bild + ein Satz" gilt als zu dünn. Eine Vertiefung mit 4–5
Infoblättern erreicht so von allein ihr Wort-Soll.

---

## 10. Qualitäts-Checkliste (vor Auslieferung)

1. 4–5 kompetenzorientierte Lernziele (Operator + Kriterium), sichtbar in der Einführung.
2. Authentische Handlungssituation + klares Handlungsprodukt.
3. Sequenz Einführung → Grundlagen → Vertiefung → Anwendung → Recap erkennbar.
4. Jedes Infoblatt nach Bauplan: Einleitung + **Erklär-Fließtext (≥120–200 Wörter, Was/Wie/Warum)** + Diagramm + Stichpunkte + Merke. Kein „Bild + ein Satz".
5. Diagramme als eingebettete Bilddateien (kein inline-SVG); Stil passend zum Inhalt. **`autofit_svg.py` + `validate_svg.py --strict` grün** (kein Clipping, keine Überlappung, kein Styling-tspan).
6. Praxisauftrag mit Vorgehen **und** transparenter Rubrik.
7. Formative Tests: mehrere Versuche, Antwort-Feedback + allgemeines Feedback + Gesamtfeedback.
8. Glossar mit echten Begriffen; Forum mit klarer Aufgabe.
9. `material:true` auf allen Infoblättern → PDF/PPTX automatisch; Lehrkräfte-Sektion verborgen.
10. Mengen tragen die Zeit (Abschnitt 9).
11. Pipeline durchlaufen: make_materials → build → **validate (grün)** → preview.
12. `course.format` = `topics` (für Kachel-Optik nach dem Restore in der UI auf „tiles" umstellen).
