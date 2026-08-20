# Didaktik-Leitfaden: Moodle-Kurse nach dem 5-Ebenen-Modell (ZDQ)

Diese Datei ist das **didaktische Gehirn** des Skills. Sie liefert das Strukturmodell,
die Pflicht-Sequenz und die Bau-Konventionen, nach denen ein hochwertiger,
vollständig ausgearbeiteter Kurs für die **berufliche Bildung** entsteht – und
übersetzt sie in konkrete Felder der Kurs-JSON. Lies sie, bevor du einen Kurs baust.

> **Vor dem Bauen zuerst fragen (Grill-Me Intake).** Führe das strukturierte
> Grill-Me-Interview in 3 Blöcken (6 Clustern) mit dem Autor durch, *bevor*
> du den Kurs schreibst – als interaktives Auswahlmenü mit konkreten Optionen und
> `(empfohlen)`-Kennzeichnung (die vollständige Systematik steht in `SKILL.md`,
> Schritt 1 „Grill-Me Intake"). Erst mit diesen Antworten und der Freigabe
> des **Vorschlags-Steckbriefs** sitzt die Handlungssituation, das Niveau,
> die 3-stufige Aufgaben-Kaskade (`formular` + `assign`) und die Simulation.

**Leitmodell:** das 5-Ebenen-Strukturmodell für Moodlekurse des ZDQ (vom Autor erweitert)
(Lernelement → Lernbaustein → Lernabschnitt → Lerneinheit/Modul → Lernkurs).

**Zwei verbindliche Goldstandard-Referenzbeispiele:**
1. **Technik & Fertigung:** `assets/fewshot_bohrmaschine.json` (Fertigungstechnik, Maschinenbedienung, 5-Sicherheitsregeln, Arbeitsplan-WPS, Rubriken).
2. **Mathematik, Stochastik & MINT:** `assets/fewshot_mathematik_statistik.json` (Beschreibende Statistik, standardisierte Lernziel-Formulierungen mit Duplikat in Kachel 6, reale Inbox-Aufgabenblätter mit nachgelagerten `assign`-Abgaben, mathematische Formel-Anatomie-Hotspots ohne Textüberdeckung, reaktive Live-Canvas-Simulation nach DIN 55303 und 6-Schritte-Prüfprotokoll).
Nutze sie als Few-Shot-Vorlagen je nach Fachbereich.

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

- **Handlungskontinuität & Der Rote Faden (Continuous Narrative Architecture):** 
  Wenn ein Kurs aus einer authentischen Handlungssituation startet (z. B. Fertigungsauftrag *Kommission Portalrahmen*, Kälteanlagen-Störung, Kfz-Diagnose), müssen **ALLE Kacheln** – auch wenn sie als 90-Minuten-Mikromodule oder Fachthemen vertieft werden – **zwingend aufeinander aufbauen**. Jede Kachel ist eine handlungsorientierte Etappe zur Lösung desselben Gesamtfalls (*Kachel 1 Fallanalyse &rarr; Kachel 2 Arbeitsplatzsicherheit für diesen Fall &rarr; Kachel 3 Brennerinstandsetzung/Rüsten &rarr; Kachel 4 Parameter für diese Werkstoffe &rarr; Kachel 5 WPS für diesen Auftrag &rarr; Kachel 6 Qualitätsprüfung der gefertigten Nähte &rarr; Kachel 7 Kundenabnahme/Reflexion*). Isolierte Theoriekapitel ohne Fallbezug sind unzulässig.
- **Handlungsorientierung:** Jedes Modul ist um eine **Handlungssituation** (ein
  echter beruflicher Auftrag/Fall) herum gebaut und mündet in ein
  **Handlungsprodukt** (etwas, das die Lernenden erstellen).
- **Interaktive Medien-Trias:** Theorie wird nicht nur gelesen, sondern in jedem Fachthema durch die Trias aus **Hotspot-Labor** (Erkundung), **Simulation** (Prozessparameter) und **ausfüllbarem Formular** (normgerechte Dokumentation/WPS) aktiv erfahrbar gemacht.
- **Kompetenzorientierung:** Ziele beschreiben *beobachtbares Können*, nicht „kennen".
- **Aktiv statt konsumierend + formatives Feedback:** jede Phase hat eine
  aktivierende Komponente (Frage, Selbsttest, Auftrag) mit sofortiger Rückmeldung.
- **Chunking:** ein Thema pro Lernabschnitt/Infoblatt; kurze, klare Einheiten.
- **Niedrigschwelligkeit:** einfache Sprache, viel Visualisierung (besonders für
  AV/BFS-Gruppen) – Diagramme tragen den Inhalt mit, nicht nur Text.

Die **vollständige Handlung** (Informieren &rarr; Planen &rarr; Entscheiden &rarr; Ausführen &rarr;
Kontrollieren &rarr; Bewerten) und der **AVIVA-Bogen** sind weiter die *didaktische
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

> **Profil-parametrisch:** Die Abschnitts-Sequenz kommt aus dem im Briefing
> gewählten **didaktischen Profil** (`course.didaktik_profil`, Default `zdq` —
> siehe `scripts/didactic_profiles.py` / `get_profile(key)["section_sequence"]`).
> Die Tabelle unten IST die Sequenz des Default-Profils `zdq` (unverändert).
> Ein anderes Profil bringt seine eigene Sequenz + Pflicht-Abschnitte mit; dann
> gilt dessen `section_sequence` statt dieser Tabelle. Die restlichen Regeln
> dieses Kapitels (Infoblatt-Bauplan, Feedback, Zeitbudget) sind konzept-neutral.

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

### 2-Ebenen-Modell: Übergeordnete Lernphasen & Flexible Kachel-Aufteilung

Das ZDQ-Modell unterscheidet strikt zwischen der **didaktischen Makro-Struktur (Lernphasen)** und der **modularen Kachel-Struktur (Moodle-Sections)**:

1. **Die 5 übergeordneten Lernphasen (Didaktische Leitstruktur):**
   - **Phase 1: Einführung** (Handlungssituation, 4–5 operatorbasierte Lernziele, Vorwissens-Check)
   - **Phase 2: Grundlagen** (Phänomenologischer/physikalischer Einstieg, Baugruppen, formative Tests)
   - **Phase 3: Vertiefung** (Mathematische Dimensionierung, Formeln, Schaltungsaufbau, Simulation, Messprotokoll)
   - **Phase 4: Anwendung** (Praxisauftrag mit 6 Handlungsphasen, Bewertungsrubrik, Werkstattforum)
   - **Phase 5: Kurs-Recap** (Zusammenfassung, Video-Recap, Selbsteinschätzung, Entstehungshinweis)
   - *Begleitende Strukturabschnitte:* **Glossar** (dedizierter Abschnitt) und **Material für Lehrkräfte** (`visible: 0`).

2. **Flexible Kachel-Multiplikatoren (Sub-Kacheln je nach Stofffülle):**
   - Ist ein Thema fachlich sehr umfangreich, werden die Phasen **Grundlagen** oder **Vertiefung** modular auf **mehrere Kacheln** aufgeteilt:
     - *Beispiel Grundlagen:* Kachel 2a: *Physikalisches Wirkprinzip* & Kachel 2b: *Sensoraufbau & Baugruppen*
     - *Beispiel Vertiefung:* Kachel 3a: *Kennwerte & Dimensionierung* & Kachel 3b: *3-Leiter-SPS-Schaltung & Simulation*
   - Der Kurs-Architekt (Grillmaster) analysiert im Briefing (Cluster 6) den Stoffumfang und unterbreitet dem Autor einen begründeten Kachelvorschlag (z. B. 6 bis 8 sichtbare thematische Kacheln).
   - Jede sichtbare Kachel erhält ihr eigenes textfreies Kachelfoto (`cover_<slug>.svg`/`.png`) für das Moodle-Kachelformat (`format_tiles`).

### Pflicht-Attribution (jeder Kurs)

**Jeder generierte Kurs trägt den Entstehungs-Hinweis** – KI-generiert und in
Kooperation mit dem Labor Didaktik der Technik der Hochschule Osnabrück. An
**zwei** Stellen, mit exakt diesem Wortlaut:

1. **Ans Ende von `course.summary`** (dezent, klein):
   ```html
   <p style='font-size:12px;color:#5f6672;'><i>Erstellt mit Hilfe von künstlicher Intelligenz, in Kooperation mit dem Labor Didaktik der Technik der Hochschule Osnabrück.</i></p>
   ```
2. **Als letztes `label` im Kurs-Recap** (sichtbarer Fuß-Hinweis, Name
   „Hinweis zur Entstehung"):
   ```html
   <div style='border-top:1px solid #c9ccd1;margin-top:6px;padding-top:10px;font-size:12px;color:#5f6672;font-family:Arial,sans-serif;'>Dieser Kurs wurde mit Hilfe von <b>künstlicher Intelligenz</b> erstellt und ist in Kooperation mit dem <b>Labor Didaktik der Technik</b> der <b>Hochschule Osnabrück</b> entstanden.</div>
   ```

3. **Automatisch am Ende JEDER Seite** (page-Content und Buch-Kapitel):
   `build_mbz.py` hängt den Satz
   *„Dieser Kurs ist mit Hilfe von Künstlicher Intelligenz und in Kooperation
   mit dem Labor Didaktik der Technik der Hochschule Osnabrück entstanden."*
   als dezenten Seitenfuß an (idempotent — steht der Satz schon im Content,
   passiert nichts). Vorschau (`preview_mbz.py`) und Druck-PDFs
   (`make_materials.py`) zeigen denselben Fuß. Override pro Kurs:
   `course.attribution` (eigener Satz) bzw. `"attribution": ""` schaltet den
   Seitenfuß ab — die beiden Stellen oben bleiben davon unberührt.

Optional zusätzlich eine `Entstehung:`-Zeile im Lehrkräfte-Leitfaden. Der
Wortlaut ist verbindlich; nur Namen/Institution nach Bedarf anpassen, wenn der
Nutzer eine andere Kooperation nennt.

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
| Ausfüllbares Protokoll/Arbeitsblatt | `formular` | echte Eingabefelder + Autosave + Datei-Download; NIE `__`-Lücken in einer `page` |
| Reflexion / Evaluation | `feedback` / `page` | unbenotet |

**Ergebnisfelder-Regel:** Wo Lernende etwas eintragen sollen (Rechenweg,
Messwert, Begründung), IMMER den `formular`-Baustein verwenden — volle
Feldbreite (lang genug für den Rechenweg), Autosave im Browser, Abgabe als
Textdatei/PDF über den Praxisauftrag. `__________`-Lücken in einer statischen
Seite kann niemand ausfüllen.

**Glossar-Restore-Hinweis:** Glossareinträge sind im Backup Nutzerdaten — beim
Wiederherstellen „Nutzerdaten einschließen" aktiviert lassen. Für den Fall
eines Restores ohne Nutzerdaten legt `make_materials.py` automatisch eine
Glossar-Importdatei in die Lehrkräfte-Sektion (Glossar → Einträge importieren).

**Verb-Konsistenz:** Ein Ziel mit „aufbauen/durchführen" wird per **Aufgabe**
geprüft, nicht per Multiple-Choice. Wissen/Verstehen per **Quiz**.

### Die Interaktive Medien-Trias je Fachthema (Gold-Standard)

Um Fachinhalte handlungsorientiert und nachhaltig zu verankern, erhält jedes vertiefte Fachthema/Modul die **Interaktive Medien-Trias**:

1. **Hotspot-Labor (`type: "hotspot"`):** 
   - *Zweck:* Visuelle Bauteil-, Werkzeug-, Schaltschrank- oder Fehlererkundung im H5P-Stil.
   - *Features:* Pulsierende interaktive Pins, Highlight-Glow, aufklappbare Detail-Karten mit technischen Daten, Normbezügen und Prüfschritten.
2. **Simulation (`type: "simulation"` via `sim_engine.py`):**
   - *Zweck:* Erforschung dynamischer Prozessparameter, physikalischer/chemischer Kausalitäten und Kennlinien.
   - *Features:* Schieberegler (`range`), Umschalter (`toggle`/`select`), dynamisch reagierende Vektorgrafiken (z. B. Einbrandtiefe, Stromfluss, Zeiger, Kurvenverlauf) und integrierte Challenge-Aufgaben mit sofortiger Erfolgsprüfung.
3. **Ausfüllbares Formular (`type: "formular"` via `form_engine.py`):**
   - *Zweck:* Normgerechte Dokumentation, Schweißanweisungen (WPS nach DIN EN ISO 15609-1), Prüfprotokolle, Fehlersuchpläne oder Gefährdungsbeurteilungen.
   - *Features:* Volle Eingabebreite für Rechenwege, browserseitiges Autosave (übersteht Reloads), Textdatei-Export (`.txt`/`.json`) für die Abgabe im Praxisauftrag (`assign`) und Druckansicht. Keine statischen Lücken in Textseiten!

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
6. **Merke-Box** – ein hervorgehobener Sicherheits-/Kernhinweis in
   **vollständigen Sätzen** (kein Stichwort-Telegramm à „Schneiden scharf? Schaft
   sauber?"). `validate_mbz.py` warnt beratend (`MERKE:`) bei Fragment-Ketten.

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

### Kachel-Cover Bildarchitektur für Moodle Tiles (`format_tiles`)

Für das Moodle-Kachelformat (`format_tiles`) erzeugte Kachel-Cover (`cover_<slug>.svg` &rarr; rasterisiert zu `.png`) müssen zwingend dieser Bildarchitektur folgen:

1. **Striktes Textverbot im Cover:**
   - Cover-SVGs für Kacheln dürfen **KEINEN Text** enthalten.
   - *Begründung:* Moodle Tiles rendert den Kacheltitel nativ als halbtransparentes Overlay über das Bild. Text im Bild führt zu unleserlicher Doppelbeschriftung und Darstellungsfehlern auf mobilen Geräten.
2. **Safe-Zone & Icon-Positionierung ($y = 45\%$ bis $85\%$):**
   - **Unterer Bereich ($y = 45\dots85\%$):** Das symbolstarke, kontrastreiche Hauptmotiv bzw. Icon (z. B. Schweißbrenner, Sensor, Getriebe, Schaltschrank, Messgerät) wird zwingend in den **unteren Bereich / unteren Rand** platziert.
   - **Oberer Bereich ($y < 45\%$):** Dient als ruhiger technischer Hintergrund (z. B. feine Blueprint-Gitter, Schaltungs-HUDs oder dezente Radial-Glows).
3. **Farbwelt & Format:**
   - 16:9-Format (z. B. 1200×675 px oder 800×450 px).
   - Ruhiger, dezenter Hintergrund mit technischer Tiefe; Hauptmotiv klar freigestellt und mit prägnanten Akzentfarben akzentuiert.

### Koordinaten-Diagramme (Charts) — Achsen, Skala, geschlossene Figuren

- **Chart markieren:** Ein Diagramm mit Koordinatenachsen (Kennlinie,
  Messkurve, Balken über einer Werteachse) bekommt am Wurzel-`<svg>` das
  Attribut `data-diagram-type="chart"`. Nur so prüft `validate_svg.py` die
  Achsen — Schaltpläne, Anatomiebilder und Piktogramme bleiben unberührt.
- **Achsentitel (Pflicht bei Charts):** jede Achse braucht einen beschrifteten
  Titel mit Größe/Einheit (z. B. „t in s", „U / V", „Kraft F") — nicht nur
  Zahlen. Fehlt er → Warnung `ACHSE`.
- **Skalierung (Pflicht bei Charts):** jede Achse braucht mindestens zwei
  numerische Skalenwerte entlang der Achse (Teilstriche zusätzlich empfohlen).
  Weniger als zwei → Warnung `SKALA`.
- **Figuren schließen (alle Diagramme):** geschlossene Formen als `polygon`
  oder als `path` mit abschließendem `Z` zeichnen, nicht als offene Linienkette
  mit einer kleinen Lücke. Eine Restlücke von 2–12 px → Warnung `FIGUR`.
- **Technische Zeichnungen — Bemaßung (Pflicht):** eine Fertigungs-/Bauteil-
  zeichnung bekommt am Wurzel-`<svg>` das Attribut `data-diagram-type="zeichnung"`
  und muss **Lage UND Größe** bemaßen — echte Maßlinien mit Begrenzungspfeilen und
  **Maßzahlen** (z. B. „20", „55", „100"; nicht nur „Ø 5 mm"). Die Lage jeder
  Bohrung ab einer Bezugskante bemaßen (parallele/gestaffelte Maße, Hilfslinien pro
  Maß). `validate_svg.py` warnt (`BEMASSUNG:`), wenn eine so markierte Zeichnung
  weniger als 3 reine Maßzahlen trägt.

Alle diese Checks sind warn-Level und blocken damit das
`validate_svg.py --strict`-Gate.

### Typografie-Konventionen in SVG-Text (Pflicht — der Validator prüft sie)

Diese Konventionen gelten für JEDE Beschriftung in selbst gezeichneten SVGs
(Diagramme UND Kachel-Banner). Alle genannten Zeichen sind WinAnsi-sicher und
rendern in Kurs, PDF und PPTX einwandfrei:

- **Echte Umlaute:** ä ö ü ß Ä Ö Ü — **niemals** ae/oe/ue-Transliteration
  („Flaeche", „gross", „Oel" sind Fehler; „Fläche", „groß", „Öl" ist richtig).
- **Einheiten hochgestellt:** cm² mm² m² m³ (echtes ²/³, U+00B2/U+00B3) —
  nie „cm2" oder „cm^2". Ausnahme „pro"-Einheiten: **„1/min" statt „min⁻¹"**
  (das hochgestellte Minus U+207B ist NICHT WinAnsi-sicher und wird zum Kästchen).
- **Malpunkt:** `·` (U+00B7) als Mal-Operator — nie „x" oder „×"
  (`F = p · A`).
- **Formelzeichen-Indizes TIEFGESTELLT:** A₁, d₂, F₁ — nie „A1"/„d2" in
  Normalgröße. Im **HTML** (Seiten, Quiz, Formular-Labels, Aufträge) als
  `A<sub>1</sub>`; in **Simulationen** (nur Browser) als Unicode ₁ ₂; in
  **SVG-Diagrammen** als separates kleineres `<text>`-Element mit y-Versatz
  (~0,72 der Grundgröße, +0,28·size), Breiten mit `stringWidth` berechnen —
  Unicode-₁₂ ist NICHT WinAnsi-sicher und in SVGs tabu. Leerzeichen in
  segmentierten Formelzeilen nie mitrendern (SVG trimmt sie), nur als
  x-Vorschub einrechnen. Die PDFs übernehmen `<sub>`/`<sup>` automatisch
  (ReportLab). Prüfung: INDEX-Check in `validate_svg.py` (SVG-Text) und
  `validate_mbz.py` (Kurs-HTML).
- **Dezimalkomma:** deutsche Schreibweise `3,14` — nie `3.14`.
- **Mindest-Schriftgröße 10** — kleiner ist gedruckt unlesbar.
- **Bündigkeit:** mittig verankerte Titel/Fußzeilen exakt auf die
  viewBox-Mitte setzen; gestapelte gleich verankerte Texte exakt auf
  dieselbe x-Koordinate (der Validator meldet 1–4-px-Versätze als
  „fast bündig/fast zentriert").
- **Kontrast:** Text muss sich von seinem Kasten/Kreis abheben
  (Leuchtdichte-Kontrast ≥ 2,5:1); heller Text auf mittelblauer Füllung
  ist ein typischer Verstoß.
- **Typografie- & Rendering-Garantie (Kein LaTeX-MathJax-Bruch):**
  Pfeile in Fließtexten, Tabellen, HTML-Attributen und Beschriftungen IMMER als sauberes HTML `&rarr;` oder Unicode `→` setzen (niemals fragile LaTeX-Befehle wie `\to`, `\rightarrow` oder `$\rightarrow$`, die MathJax zerstören oder ungerendert als Quelltext stehen bleiben).

`validate_svg.py` meldet Verstöße als Warnungen (unter `--strict` schlagen sie
den Build fehl); die Prüfung läuft automatisch in `make_materials.py` und
`build_mbz.py` mit.

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

**Die 3-stufige Aufgaben-Kaskade (Aktivierung über den gesamten Kurs):**
1. **Kachel 2 (Grundlagen) — Formativer Erkundungsauftrag:**
   Kurze Beobachtungs-, Mess- oder Zuordnungsaufgabe direkt im Anschluss an die
   Einführung (z. B. Bauteile am Schaltplan identifizieren, Klemmenbezeichnungen
   zuordnen, Messwerte an einer statischen Skala ablesen).
2. **Kachel 3 (Vertiefung) — Ausfüllbares Formular-Protokoll (`type: "formular"`):**
   Interaktives Formular mit Textfeldern, Rechenschritten, Formel-Eingaben und
   Begründungsfeldern. Verfügt über lokales **Autosave** im Browser und einen
   **Textdatei-Export** (.txt / .json), damit die Lernenden ihre Arbeit sichern
   und weiterverarbeiten können.
3. **Kachel 4 (Anwendung) — Vollständiger Praxisauftrag (`type: "assign"`):**
   Der summative Hauptauftrag, strukturiert nach den **6 Phasen der vollständigen
   Handlung**: *1. Informieren → 2. Planen → 3. Entscheiden → 4. Ausführen →
   5. Kontrollieren → 6. Bewerten*. Die Lernenden laden ihre Ergebnisse
   (z. B. den Text-Export aus dem Formular + Messprotokoll + Schaltplan) hoch.
   Transparente **Bewertungskriterien als HTML-Rubrik** (3–4 Kriterien × 3–4 Notenstufen).

**Quizfragen mit formativem Feedback:** Jede Frage braucht `generalfeedback` (Regel für alle)
**und** Feedback je Antwort; Distraktoren bilden **typische Fehlvorstellungen** ab.
Quiz braucht `overallfeedback` (Prozentbänder mit Feed-Forward). Nie nur „richtig/falsch".

**Reflexion & Transfer** (Recap): Rückblick aufs eigene Lernen + Transferauftrag,
an eine konkrete eigene Handlung im Betrieb gebunden.

### Rechenbeispiele & Aufgaben (Pflicht — geg/ges, Einheiten, echte Situation)

**Rechenbeispiel-Bauplan (kopierbares Muster).** Jede vorgerechnete Aufgabe folgt
Schritt für Schritt diesem Muster — nur ReportLab-sicheres HTML (`<b>`, `<sub>`,
`<sup>`), damit es in Moodle-Seite, Vorschau UND PDF ankommt:

```html
<div class="rechenbeispiel">
  <h4>Rechenbeispiel (Musterlösung): <Titel></h4>
  <p><b>Situation:</b> <realer betrieblicher Kontext + konkrete Frage></p>
  <p><b>Gegeben:</b> <Größe = Wert Einheit; …></p>
  <p><b>Gesucht:</b> <Größe in Einheit></p>
  <p><b>Formel:</b> <symbolisch; Bruch als \(\frac{}{}\)></p>
  <p><b>Schritt 1 – Einheiten angleichen:</b> <z.B. mm→m, mit Begründung></p>
  <p><b>Schritt 2 – Zwischenwert:</b> <Teilterm/Nenner ausrechnen, MIT Einheit></p>
  <p><b>Schritt 3 – Einsetzen und rechnen:</b> <Division/Mult., Zwischenergebnis></p>
  <p><b>Schritt 4 – Einheiten prüfen:</b> <Kürzung als Bruch sichtbar machen></p>
  <p><b>Ergebnis:</b> <Wert Einheit, sinnvoll gerundet></p>
  <p><b>Schritt 5 – In die Praxis:</b> <nächste Norm-/Maschinenstufe wählen></p>
  <p><b>Plausibilität:</b> <Gegencheck, z.B. an einer Kennlinie></p>
</div>
```

- **V5 — Musterlösung, nicht Kurzform:** Gegeben/Gesucht → Formel → **mindestens
  eine Zwischenrechen-Zeile** → Ergebnis. NIE direkt von „Einsetzen" zu „Ergebnis"
  springen — Einheiten-Umrechnung, Teilterme (z. B. Nenner) und das Runden auf die
  praktische Stufe werden ausgeschrieben. Die Schrittzahl skaliert mit der
  Komplexität (ein simples Verhältnis braucht weniger). `validate_mbz.py` warnt
  beratend (`RECHENBEISPIEL:`), wenn „Einsetzen" ohne Zwischenschritt aufs
  „Ergebnis" springt.
- **V7 — Einheiten in JEDER Zeile:** jede physikalische Größe trägt ihre Einheit
  (gegeben, eingesetzt, Zwischenwert, Ergebnis). Keine nackten Zahlen. Konventionen
  wie bei SVG-Text (echte ²/³, Malpunkt ·, `1/min`).
- **V6 — echte Aufgaben aus der Handlungssituation:** jede Aufgabe/Rechnung ist
  in den realen betrieblichen Kontext des Kurses eingebettet (Bedarf, Zweck:
  „In der Steuerung …, damit …") — NIE ein nacktes „Berechne R".
- **Brüche in Rechnungen — echt setzen:** Brüche als MathJax schreiben:
  `\(\frac{Zähler}{Nenner}\)` — Moodle rendert daraus einen echten Bruch
  (`\(\frac{3}{4}\)` erscheint als echtes ¾), die Vorschau zeigt ihn gestapelt,
  das PDF fällt auf `Zähler/Nenner` zurück. Nur der Bruch selbst ist MathJax; die
  umgebende Gleichung (`R = \(\frac{U}{I}\) = 6 Ω`) bleibt normaler Text.
- **Einheiten NICHT als Bruch (Regel):** m/s, km/h und besonders lange/
  zusammengesetzte Einheiten (z. B. die der Gravitationskonstante) bleiben im
  Fließtext normaler Text/Slash — nie in `\frac` zwingen.
- **Ausnahme — Einheiten-Kürzung sichtbar machen:** Zeigt ein Rechenschritt, WIE
  sich Einheiten kürzen, darf genau dieser Schritt als Bruch stehen — das macht das
  Wegkürzen augenfällig. Muster (Drehzahl):
  `\(\frac{m/min}{m}\) = \(\frac{m}{min · m}\) = \(\frac{1}{min}\)` → das „m" steht
  oben und unten und kürzt sich weg, übrig bleibt 1/min. Nur für den
  Kürzungs-Schritt, nicht als generelle Schreibweise der Einheit.
  Voraussetzung fürs echte Bruch-Rendering: der **MathJax-Filter** ist im
  Ziel-Moodle aktiv (4.x-Standard); sonst zeigt Moodle den LaTeX-Quelltext.
  Wichtig: **keine verschachtelten** `\frac` (Zähler/Nenner ohne `{}` darin) — der
  Renderer wandelt nur nicht-verschachtelte Brüche um.

`validate_mbz.py` meldet beratend (nicht-fatal) eine Ergebniszeile ohne Einheit
im Rechenkontext (`EINHEIT:`).

---

## 8. Downloadbare Materialien + Bau-Pipeline

Infoblätter mit `"material": true` werden **automatisch** zu Download-Dateien:
`make_materials.py` erzeugt pro Infoblatt ein **PDF** (Druck – es bildet das
**vollständige Infoblatt** ab: Kopfleiste, Fließtext, Diagramm, Tabellen/Listen,
Merke-Box) und eine **PPTX** (editierbar) und sammelt alle PDFs + PPTX in der
verborgenen Lehrkräfte-Sektion. Das PDF wird **nicht** hinter die Seite gehängt –
im Kurs steht an der Stelle nur das Infoblatt selbst.

**Pipeline (Standard für jeden Kurs — Video zuerst starten, Rest parallel):**

Die NotebookLM-Video-Generierung dauert 5–10 Minuten und braucht als Input NUR
das Dossier (aus `course.json`). Deshalb: **Video-Flow zuerst anstoßen und die
gesamte Build+Validierungs-Pipeline WÄHREND der Wartezeit laufen lassen** —
so verlängern die Validatoren die Kursherstellung um keine Sekunde:

```
# (1) VIDEO STARTEN (sofort, sobald course.json steht)
export_course_dossier.py course.json -o dossier.md           # Quelle fürs Video
# NotebookLM-Flow starten (references/notebooklm-video-recap.md) -> generiert im Hintergrund

# (2) PARALLEL, während NotebookLM rechnet (~5-10 min):
autofit_svg.py        assets/                                # viewBox passgenau -> kein Clipping
validate_svg.py       course.json --strict                   # Diagramm-QA + Typografie
build_simulation.py   course.json -o course.sim.json         # Sims/Formulare -> Datei-Ressourcen
make_materials.py     course.sim.json -o course.materialized.json  # PDF/PPTX + Einhängen
build_mbz.py          course.materialized.json -o course.mbz --wwwroot ...
validate_mbz.py       course.mbz                             # Struktur + TIEFEN-CHECKS
preview_mbz.py        course.materialized.json -o course_vorschau.html
# Browser-Checks (Sim ohne Scrollen, Formularfelder leer+Autosave) ebenfalls jetzt

# (3) SOBALD DAS VIDEO FERTIG IST:
set_recap_video.py    course.json --file recap.mp4           # Platzhalter ersetzen
# Kurz-Rebuild: build_simulation -> make_materials -> build_mbz -> validate_mbz
```

`validate_mbz.py` prüft neben der Struktur automatisch die **inhaltlichen
Ketten** (Glossar-Nutzerdaten-Kette inkl. mnethosturl, tiles-Kachelfoto-
Verdrahtung, Attributions-Fuß je Seite, leere Formularfelder, Sim-Kompakt-
layout) — alle Checks zusammen < 1 s. Findet der finale Kurz-Rebuild in (3)
noch einen Fehler, korrigieren und (3) wiederholen; das Video bleibt gültig.
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
2. **Handlungskontinuität & Der Rote Faden (Continuous Narrative Architecture):** Alle Kacheln bauen zwingend aufeinander auf und lösen denselben Gesamtauftrag als handlungsorientierte Etappen.
3. Sequenz Einführung &rarr; Grundlagen &rarr; Vertiefung &rarr; Anwendung &rarr; Recap erkennbar.
4. Jedes Infoblatt nach Bauplan: Einleitung + **Erklär-Fließtext (≥120–200 Wörter, Was/Wie/Warum)** + Diagramm + Stichpunkte + Merke. Kein „Bild + ein Satz".
5. Diagramme als eingebettete Bilddateien (kein inline-SVG); Stil passend zum Inhalt. **`autofit_svg.py` + `validate_svg.py --strict` grün** (kein Clipping, keine Überlappung, kein Styling-tspan).
6. Praxisauftrag mit 6 Handlungsphasen **und** transparenter Bewertungsrubrik.
7. Formative Tests in JEDER Kachel: mehrere Versuche, Antwort-Feedback zu jeder Option + allgemeines Feedback + Gesamtfeedback.
8. Glossar mit echten Begriffen; Forum mit klarer handlungsorientierter Aufgabe.
9. `material:true` auf allen Infoblättern &rarr; PDF/PPTX automatisch; Lehrkräfte-Sektion verborgen.
10. Mengen tragen die Zeit (Abschnitt 9).
11. Pipeline durchlaufen: make_materials &rarr; build &rarr; **validate (grün)** &rarr; preview.
12. **Kachel-Cover Bildarchitektur für `format_tiles`:** Jede sichtbare Kachel erhält ein **textfreies** Cover-PNG (`cover_<slug>.png`, gerastert aus SVG). **Safe-Zone eingehalten ($y = 45\dots85\%$ für Hauptmotiv/Icon am unteren Rand)**, oberer Bereich ($y < 45\%$) ruhig gehalten für technische Hintergrundstrukturen. Keine Schriftzüge im Bild.
13. **Pflicht-Attribution** in `course.summary` **und** als „Hinweis zur Entstehung"-`label` im Kurs-Recap (KI + Labor Didaktik der Technik, HS Osnabrück – siehe Abschnitt 3).
14. **Interaktive Medien-Trias je Fachthema:** Hotspot-Labor (`hotspot`) für Erkundung + Simulation (`simulation`) für Prozessparameter + ausfüllbares Formular (`formular`) für Protokolle/WPS.
15. **Typografie- & Rendering-Garantie:** Keine LaTeX-Pfeilbrüche (immer `&rarr;` oder `→`), echte Umlaute, ²/³, Malpunkt ·, Dezimalkomma, Bündigkeit, Kontrast warnungsfrei.
16. **Ergebnisfelder als `formular`** (ausfüllbar + autosave + exportierbar), keine `__`-Lücken in Seiten.
17. **Simulation passt ohne Scrollen auf einen Bildschirm** (kompaktes Engine-Layout; flaches `visual`-viewBox). **Animation/Manipulation sind Standard**, wo das Thema etwas Bewegtes hergibt — Spec-Felder `animate` (Zeit-Loop mit Play/Pause/Speed) und `inputs[].type: select/toggle` (Schalter/Szenario statt nur Regler). Tempo-Regler reicht bis 0,1× (Zeitlupe).
18. **Rechenbeispiele als Musterlösung** (Abschnitt 7): geg/ges &rarr; Formel &rarr; **mindestens ein Zwischenschritt** &rarr; Ergebnis &rarr; Praxisstufe; Einheiten in jeder Zeile; Einheiten-Kürzung als Bruch sichtbar. `validate_mbz` warnt (`RECHENBEISPIEL:`) bei direktem Sprung Einsetzen&rarr;Ergebnis.
19. **Merke-Boxen in vollständigen Sätzen** (kein Stichwort-Telegramm); `validate_mbz` warnt (`MERKE:`).
20. **Technische Zeichnungen bemaßt** (`data-diagram-type="zeichnung"`, Lage UND Größe mit Maßzahlen); `validate_svg` warnt (`BEMASSUNG:`).
