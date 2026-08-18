# Methodenvielfalt & E-Learning-Formate für berufliche Moodle-Kurse

Dieses Referenzdokument definiert die didaktische Methodenvielfalt, die E-Learning-Szenarien und die Entscheidungslogik für das Grill-Me-Interview im Skill `moodle-kurs-grill-me`.

---

## 1. E-Learning-Formate & Lernszenarien

| Format-Key | Bezeichnung | Didaktische Kernidee | Ideale Zielgruppe / Schulform | Moodle-Architektur |
|---|---|---|---|---|
| `blended_learning` | **Integriertes Blended Learning** | Enge Verzahnung von digitalem Moodle-Kurs (Theorie, Vorbereitung, Dokumentation) und realem Werkstatt-/Präsenzunterricht. | Duale Berufsschule, BFS, Meisterkurse | Kacheln im Theorie-Praxis-Tandem; Moodle liefert Vorbereitung, Arbeitsblätter und Prüfprotokoll für die Werkstatt. |
| `flipped_classroom` | **Flipped / Inverted Classroom** | Wissenserwerb erfolgt asynchron digital im Moodle-Kurs vorab (Infoblätter, Hotspots, Videos, Selbsttest). Die Präsenzzeit wird zu 100 % für Diskussion, Schaltungsaufbau und komplexe Probleme genutzt. | Fachoberschule (FOS), Berufliches Gymnasium (BGY), Technikerschule | Kacheln 1–3 als digitale Pflicht-Vorbereitung (mit Eingangs-Quiz als Ticket-to-Class); Kachel 4 als Präsenz-Projekt. |
| `microlearning` | **Microlearning (Learning Nuggets)** | Aufteilung in kompakte 5- bis 10-Minuten-Lerneinheiten mit direktem interaktiven Wissens-Check. Fokus auf hohe Anschaulichkeit und mobile Nutzbarkeit. | Ausbildungsvorbereitung (AV), Prüfungsvorbereitung (GAP 1/2), Azubis unterwegs | Kurze Kacheln mit jeweils 1 Hotspot/Simulation + 1 ausfüllbares Mini-Formular + 1 Dreifragen-Quiz. |
| `scenario_based_pbl` | **Szenariobasiertes Lernen (PBL)** | Der gesamte Kurs ist als zusammenhängender Kriminalfall, Kundenauftrag oder Störungsfall aufgebaut. Die Lernenden schlüpfen in die Rolle des Technikers/Fachberaters. | 2./3. Ausbildungsjahr, Techniker, Höhere Berufsfachschule | Kachel 1: Notruf/Auftrag; Kacheln 2–3: Ursachenforschung & Messdaten; Kachel 4: Behebung & Abnahmebericht. |
| `leittext_digital` | **Digitale Leittextmethode** | Strukturierte Selbstorganisation über Leittexte und Leitfragen entlang der 6 Phasen der vollständigen Handlung. Höchste Selbstständigkeit. | Duale Berufsausbildung (ab 2. Lehrjahr), Fachpraxis | Ausfüllbare Leittext-Formulare (`formular`) in jeder Kachel; abschließende Bewertungsrubrik (`assign`). |
| `lerntheke_stationen` | **Digitale Lerntheke / Stationenlernen** | Binnendifferenziertes Lernen: Kacheln fungieren als Stationen mit Pflichtaufgaben (Basiskompetenz) und Wahl-/Expertenstationen (Vertiefung). | Heterogene Klassen, BFS, Sekundarstufe 1/2, DaZ-Förderung | Pflichtkacheln + gekennzeichnete Vertiefungskacheln („Expertenstation“ / „Zusatz-Challenge“). |
| `mastery_learning` | **Beherrschungslernen (Gating)** | Stufenweises Freischalten: Ein Lernabschnitt wird erst zugänglich, wenn das formative Quiz des vorherigen Abschnitts mit mindestens 80 % bestanden wurde. | Sicherheitsrelevante Themen (5 Sicherheitsregeln, DGUV V3, Hygiene, Gefahrstoffe) | Moodle-Voraussetzungen (`conditions`) auf Quiz-Abschluss konfiguriert. |

---

## 2. Didaktische Methoden & Handlungsformen

Im Kursbau kombiniert der Kursentwickler gezielt 2–4 didaktische Methoden, um Monotonie zu verhindern:

### A. Leittextmethode (Selbstgesteuertes Handeln)
* **Ablauf:** Leitfragen zur Informationsbeschaffung $\rightarrow$ Erstellung eines Arbeits-/Prüfplans $\rightarrow$ Entscheidung über Vorgehen $\rightarrow$ Fachgerechte Ausführung $\rightarrow$ Kontrollbogen $\rightarrow$ Fachgespräch/Bewertung.
* **Moodle-Elemente:** `type: "formular"` (Leitfragenbogen), `type: "page"` (Infoblatt), `type: "assign"` (Handlungsprodukt).

### B. Fehlersuche & Störungsdiagnose (Bug-Hunt)
* **Ablauf:** Analyse eines Störungsbilds (z. B. *"Motor brummt, läuft aber nicht an"*) $\rightarrow$ Hypothesenbildung $\rightarrow$ Messungen im virtuellen/realen Stromkreis $\rightarrow$ Eingrenzung fehlerhafter Bauteile $\rightarrow$ Dokumentation im Fehlerprotokoll.
* **Moodle-Elemente:** `type: "hotspot"` (Messpunkte anklicken), `type: "simulation"` (Schaltzustände testen), `type: "formular"` (Fehleranalyse-Matrix).

### C. Fallstudie & Kundengespräch (Situatives Problem-Solving)
* **Ablauf:** Realistisches Kundenbriefing mit Zielkonflikten (z. B. Kosten vs. Ausfallsicherheit) $\rightarrow$ Normen- und Wirtschaftlichkeitsprüfung $\rightarrow$ Erstellung eines Angebots / Montageplans.
* **Moodle-Elemente:** `type: "page"` (Kundenakte), `type: "forum"` (Diskussion von Alternativen), `type: "assign"` (Angebotsabgabe).

### D. Think-Pair-Share digital (Kooperatives Lernen)
* **Ablauf:** 1. **Think:** Individuelle Bearbeitung des Protokolls im Moodle-Formular. 2. **Pair:** Abgleich der Ergebnisse im Partner-Tandem (Forum/Chat). 3. **Share:** Veröffentlichung der Best-Practice-Lösung im Kursforum.
* **Moodle-Elemente:** `type: "formular"` + `type: "forum"`.

### E. Expertenpuzzle (Jigsaw digital)
* **Ablauf:** Aufteilung der Klasse in Expertengruppen (z. B. Gruppe A: Motorschutzschalter, Gruppe B: Schütztechnik, Gruppe C: Bimetallrelais). Jede Gruppe erarbeitet ihr Spezialgebiet und unterrichtet anschließend die Stammgruppe.
* **Moodle-Elemente:** Kachelweise Zuteilung oder Gruppen-Foren im Moodle.

### F. Kriteriengeleitetes Peer-Feedback
* **Ablauf:** Lernende reichen ihren Schaltplan oder Rechenweg ein und bewerten die Einreichung eines Mitschülers anhand einer standardisierten Moodle-Rubrik mit festen Kriterien.
* **Moodle-Elemente:** `type: "assign"` mit Rubriken-Feedback oder Moodle-Gegenseitige Beurteilung (`workshop`).

### G. Gestufte Lernhilfen (Scaffolding)
* **Ablauf:** Aufgabenstellung mit mehrstufigen, einklappbaren Hinweisen (Stufe 1: Fachbegriff-Erklärung, Stufe 2: Formelansatz, Stufe 3: Teillösung).
* **Moodle-Elemente:** HTML-Details-Tags (`<details><summary>Tipp anzeigen</summary>...</details>`) in Formularen und Infoblättern.

---

## 3. Entscheidungsmatrix & Vorschlagslogik im Grill-Me

Im Gespräch analysiert der Agent das Thema und generiert eine maßgeschneiderte **Vorschlags-Triade** mit begründeter Empfehlung:

### Beispiel 1: Technische Ausbildung (z. B. Wendeschützschaltung)
> **E-Learning-Format Vorschlag:**
> 1. **(Empfohlen) Integriertes Blended Learning:** Digitale Schaltungsanalyse & Formular-Dimensionierung im Moodle, gefolgt von realer Verdrahtung in der Ausbildungswerkstatt.
> 2. **Flipped Classroom:** Vollständige Vorab-Theorie mit Schaltschrank-Hotspot und Eingangs-Selbsttest; Präsenzzeit wird komplett für Fehlersuche genutzt.
> 3. **Szenariobasiertes PBL:** Durchgehender Störungsfall bei Kunde Meyer (Förderband blockiert).
>
> **Didaktische Methoden Vorschlag:**
> 1. **(Empfohlen) Leittextmethode kombiniert mit Störungsanalyse:** 6 Handlungsphasen mit ausfüllbarem Prüfprotokoll und interaktiver Hotspot-Fehlersuche.
> 2. **Fallstudie & Werkstattauftrag:** Klassische Kundenauftragsabwicklung mit Materialliste und Sicherheitsprüfung.
> 3. **Think-Pair-Share:** Einzelberechnung von Bemessungsströmen mit anschließendem Tandem-Schaltplan-Review.

### Beispiel 2: Kaufmännische Ausbildung (z. B. Mahnwesen & Zahlungsverzug)
> **E-Learning-Format Vorschlag:**
> 1. **(Empfohlen) Szenariobasiertes Lernen (PBL):** Fallakte eines säumigen Großkunden; Azubis durchlaufen kaufmännische Mahnstufen bis zum gerichtlichen Mahnbescheid.
> 2. **Blended Learning:** Digitales Erstellen von Mahnschreiben im Moodle-Formular, Rollenspiel (Mahntelefonat) im Präsenzunterricht.
> 3. **Microlearning:** Kurze Module zu Verzugszinsen, Fristenberechnung nach BGB und Mahnformulierungen.
