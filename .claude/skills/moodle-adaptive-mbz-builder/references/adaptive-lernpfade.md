# Adaptive Lernpfade in Moodle-MBZ — Skill-Referenz

Diese Datei beschreibt, wie der bestehende Skill (der aktuell **lineare** Moodle-Kurse
als MBZ erzeugt) so erweitert wird, dass er **adaptive, verzweigende Kurse mit
durchlässiger Ein-/Abstufung und dokumentierender, niveaugewichteter Bewertung**
ausgeben kann — vollständig plugin-frei und MBZ-portabel.

> **Zentrales Konstruktionsprinzip (unbedingt beachten):** Einstufung und Bewertung
> sind **entkoppelt**. Die Auf-/Abstiegsentscheidung hängt an der **aktuellen Leistung
> relativ zum aktuellen Niveau**, NICHT am kumulativen Gesamtscore. Der gewichtete
> kumulative Score dient nur der **Dokumentation/Benotung**, nicht der Steuerung.
> Grund: Ein gewichteter kumulativer Score, der die Einstufung steuert, wirkt wie eine
> **Ratsche** — hohe Lernende bleiben oben, niedrige unten. Das zerstört die
> Durchlässigkeit. Details und Herleitung in §4.

> Zweck: Referenzdokument für Claude Code. Beschreibt Zielstruktur, MBZ-Serialisierung,
> Berechnungslogik und den konkreten Bauablauf. Kein Ersatz für den fachlichen Content —
> die didaktische Validierung und die Testfragen bleiben Aufgabe des Autors.

---

## 1. Was der erweiterte Skill können muss

Aus einem **linearen 5-Modul-Kurs** (Modul 1→2→3→4→5, je mit Abschlusstest)
soll ein **adaptiver Kurs** werden mit:

1. **Drei Niveaupfaden** pro Stufe: Anfänger / Mittel / Fortgeschritten.
2. **Konvergenz an den Testpunkten**: Alle drei Niveaupfade einer Stufe münden
   wieder in *einen* gemeinsamen Test, bevor die nächste Verzweigung kommt.
3. **Durchlässigkeit**: Die Einstufung in die nächste Stufe hängt **nur von der
   aktuellen Leistung relativ zum aktuellen Niveau** ab, nicht vom kumulativen Score
   und nicht davon, wo der Lernende zwei Stufen vorher war. Aufstieg und Abstieg sind
   **symmetrisch** (gleich „schwer") und jederzeit möglich.
4. **Niveaugewichtete, kumulative Bewertung — nur als Dokumentation**: Ein
   Fortgeschrittenen-Test zählt fürs Zeugnis mehr als ein Anfänger-Test. Über alle
   Module summiert sich daraus ein individueller Gesamtscore, der den Lernweg abbildet.
   Dieser Score **steuert die Einstufung NICHT** (sonst Ratschen-Effekt, §4).

---

## 2. Zielstruktur (pro Stufe)

Jede der 5 Stufen besteht aus:

| Element | Anzahl pro Stufe | Zweck |
|---|---|---|
| Lernmodul-Kacheln | 3 (Anfänger/Mittel/Fortgeschritten) | Niveaudifferenzierter Inhalt |
| Test | 3 niveaugebundene Test-Items (siehe §4) | Je 20 Fragen, unterschiedlich gewichtet |
| Wiederholschleife | 1 (Rücksprung) | Bei < Mindestschwelle |

Konvergenz-Prinzip: **Aufspalten → Zusammenführen → Aufspalten.** Der Baum wächst
dadurch **linear** (≈ 5 Kacheln/Stufe), nicht exponentiell.

Modulzahl gesamt (5 Stufen): ca. **25 Aktivitäten** + 3 Grade-Items/Stufe + 1 kumulatives
Calculated-Grade-Item. Zum Vergleich linear: ca. 10 Aktivitäten.

---

## 3. Das Ratschen-Problem (warum das naive Modell versagt)

Ein früherer Entwurf ließ die Einstufung vom **kumulativen, gewichteten Gesamtscore**
abhängen. Das ist ein Konstruktionsfehler. Zwei Effekte verstärken sich gegenseitig:

1. **Kumulation** macht das System träge — alte Ergebnisse hängen ewig nach; ein
   starker Start dominiert dauerhaft.
2. **Niveaugewichtung** verzerrt zusätzlich zugunsten derer, die schon oben sind.

Rechenbeispiel (Gewichte 1,0 / 1,5 / 2,0):
- Fortgeschrittener mit schwachem Test: 40 % × 2,0 = **80 Beitragspunkte**
- Anfänger mit exzellentem Test: 95 % × 1,0 = **95 Beitragspunkte**

Der Anfänger liegt in dieser *einen* Stufe knapp vorn — aber der Fortgeschrittene hat
sich über alle vorherigen Stufen mit dem 2,0-Faktor ein dickes Punktepolster aufgebaut.
Der kumulative Score friert die Niveaus ein: **schwer aufzusteigen, schwer abzusteigen.**
Das ist das Gegenteil eines durchlässigen adaptiven Systems.

**Lösung: Einstufung und Bewertung entkoppeln.** Die nächste Verzweigung richtet sich
nach der **aktuellen Leistung relativ zum aktuellen Niveau**, nicht nach dem Gesamtscore.
Der gewichtete kumulative Score bleibt erhalten, wechselt aber die Rolle: von der
**Steuergröße** zur reinen **Dokumentations-/Benotungsgröße** (§6).

---

## 4. Freischaltungslogik (`availability`) — leistungsbasiert & niveau-relativ

Steuerung der Sichtbarkeit über **Restrict access / Voraussetzungen** — Moodle-Bordmittel,
serialisiert als JSON im Feld `availability` innerhalb jeder `activities/[modul]_[id]/module.xml`.

Die Bedingung jeder Stufe-N-Kachel bezieht sich auf **die Prozentnote des letzten Tests**
(bzw. auf ein kleines gleitendes Mittel der letzten 1–2 Tests, §4.3), **NICHT** auf den
kumulativen Score. Entscheidend: Die Schwellen sind **relativ zum aktuellen Niveau**
definiert, damit Auf- und Abstieg symmetrisch werden.

### 4.1 Niveau-relative Schwellen

Der Skill trägt je Niveaukachel den passenden Schwellensatz ein:

| Aktuelles Niveau | Aufstieg (≥) | Bleibt | Abstieg (<) |
|---|---|---|---|
| **Anfänger** | 80 % → Mittel | 40–79 % | < 40 % → Wiederholung |
| **Mittel** | 80 % → Fortgeschritten | 40–79 % | < 40 % → Anfänger |
| **Fortgeschritten** | — (Deckel) | ≥ 50 % | < 50 % → Mittel |

Der Fortgeschrittene mit 40 % **steigt jetzt ab** — genau die Bewegung, die die
Gewichtung vorher verhindert hat. Aufstieg (immer ≥ 80 %) und Abstieg sind gleich „schwer".

### 4.2 JSON-Muster

Beispiel: Freischaltung „Mittel-Kachel Stufe 2", wenn der **letzte Test** (Stufe-1-Test)
zwischen 80–100 % lag. `id` verweist auf das Grade-Item des **letzten Tests** (nicht auf
das kumulative Item):

```json
{
  "op": "&",
  "c": [
    { "type": "grade", "id": <GRADEITEM_ID_LETZTER_TEST>, "min": 80, "max": 100 }
  ],
  "showc": [ false ]
}
```

- `min`/`max` = das Niveaufenster gemäß Tabelle §4.1.
- `showc: false` = nicht erfüllte Kacheln bleiben unsichtbar.
- Wiederholschleife: eigene Bedingung mit `max` unter der Mindestschwelle, Rücksprung
  auf dieselbe Stufe — **mit Deckel** (§4.4).

> `availability` steuert nur Sichtbarkeit; es schreibt keine Werte zurück. Verrechnung
> passiert im Gradebook (§5/§6).

### 4.3 Hysterese gegen Zappeln (optional, empfohlen)

Rein leistungsbasiert kann das System *zu* zappelig werden (Pendeln bei Tagesform).
Etwas Trägheit ist erwünscht — aber **kontrolliert eingebaut**, nicht über Kumulation:

- **Asymmetrische Schwellen**: Aufstieg ab 80 %, Abstieg aber erst unter **35 %** statt
  40 %. Kleiner Puffer gegen zufälliges Abrutschen, ohne echte Schwäche zu ignorieren.
- **Gleitendes Mittel der letzten 2 Tests** als Einstufungsgröße statt Einzeltest.
  Umsetzung: ein eigenes, **kleines** Calculated-Item, das nur die letzten 1–2
  Test-Items mittelt (nicht die ganze Historie). Die `availability` verweist dann auf
  dieses Mittel-Item statt auf den Einzeltest.

### 4.4 Wiederhol-Deckel

Die Wiederholschleife braucht einen Zähler/Deckel, sonst kann sich ein Lernender
festfahren. Umsetzung plugin-frei: nach 2 Fehlversuchen greift eine alternative
Bedingung, die statt der reinen Wiederholung eine **Fördervariante mit anderem Zugang**
freischaltet (z. B. zusätzliches Erklärmodul), von der aus der Test erneut erreichbar ist.

---

## 5. Niveaugewichtung ohne Laufzeitlogik — der Null-Item-Trick

> Dieser Abschnitt betrifft **nur die Bewertung/Dokumentation** (§6), nicht die
> Einstufung. Die Einstufung läuft ausschließlich über §4.

Kernproblem: Moodles Calculated-Grade-Formel ist **statisch** — sie kann nicht zur
Laufzeit „erkennen", welchen Pfad jemand gegangen ist, und die Gewichte umschalten.

Lösung: Pro Modul existieren **drei separate Test-Items** (Anfänger/Mittel/Fortgeschritten).
Ein Lernender füllt immer nur **eines** davon aus — die anderen beiden bleiben leer (null/0).
Jedem Item wird **fest** sein Niveau-Gewicht in der Gesamtformel zugewiesen. Da pro Modul
nur ein Item befüllt ist, „wählt" die Formel automatisch das richtige Gewicht, **ohne den
Pfad kennen zu müssen**.

Beispiel-Gewichte (frei kalibrierbar):

| Niveau-Test-Item | Gewicht |
|---|---|
| Anfänger-Test Modul N | 1,0 |
| Mittel-Test Modul N | 1,5 |
| Fortgeschritten-Test Modul N | 2,0 |

Damit werden 85 % im Fortgeschrittenen-Test fürs Zeugnis „schwerer" als 85 % im
Anfänger-Test — ohne dass diese Gewichtung die Einstufung verzerrt.

---

## 6. Kumulativer Gesamtscore (`gradebook.xml`) — Dokumentationsgröße

Der rote Faden ist ein **Calculated grade item**, das in `gradebook.xml` mitexportiert wird.
Es summiert alle niveaugewichteten Test-Items über alle Module.

Formel-Semantik (Moodle-Calculated-Grade nutzt Item-IDs in `[[...]]`):

```
Kumulativ =
    [[AnfTest_M1]]*1.0 + [[MitTest_M1]]*1.5 + [[FortTest_M1]]*2.0
  + [[AnfTest_M2]]*1.0 + [[MitTest_M2]]*1.5 + [[FortTest_M2]]*2.0
  + ... (über alle 5 Module)
```

Da pro Modul nur ein Item befüllt ist, trägt jedes Modul genau seinen gewählten
Niveau-Beitrag bei. Das Ergebnis ist ein **individueller Gesamtscore**, der den
kompletten adaptiven Weg abbildet — die Abschluss-/Zeugnisnote.

> **Wichtig:** Auf dieses kumulative Item verweist **keine** `availability`-Bedingung.
> Es ist reine Dokumentations-/Benotungsgröße. Die Einstufung läuft über die
> Einzeltest- bzw. Mittel-Items aus §4. Das ist die zentrale Korrektur gegen den
> Ratschen-Effekt (§3).

Aufbau in `gradebook.xml`, den der Skill erzeugen muss:
- Pro Modul: 3 `grade_item`-Einträge (Anfänger/Mittel/Fortgeschritten), jeweils mit
  eigenem Gewicht (fürs kumulative Item) — und als **rohe Prozentnote** referenzierbar
  (für die Einstufung in §4).
- 1 `grade_item` vom Typ **Calculated** (kumulativ, gewichtet) für die Dokumentation.
- Optional (bei Hysterese §4.3): 1 kleines Calculated-Item pro Stufe, das nur die
  letzten 1–2 Tests mittelt und als Einstufungsgröße dient.
- Konsistente, **stabile IDs**: Formeln und `availability`-JSONs referenzieren dieselben
  IDs. Der Skill muss eine ID-Map führen und cross-referenzieren (analog zu den bereits
  vorhandenen kaskadierenden JSON-Handoffs). **Achtung:** Einstufungs-JSONs zeigen auf
  Einzeltest-/Mittel-Items, NICHT auf das kumulative Item.

---

## 7. Bauablauf für den Skill (Schritt für Schritt)

1. **Eingaben einsammeln**
   - Anzahl Stufen (Default 5), Anzahl Fragen/Test (Default 20).
   - Niveau-Gewichte **fürs kumulative Item** (Default 1,0 / 1,5 / 2,0) — nur Doku.
   - **Niveau-relative Ein-/Abstiegsschwellen** (Default siehe §4.1: Auf ≥ 80 %,
     Abstieg < 40 %, Fortgeschritten-Deckel bei < 50 %).
   - Hysterese ein/aus (§4.3): asymmetrische Abstiegsschwelle (Default 35 %) und/oder
     gleitendes Mittel der letzten 2 Tests.
   - Wiederhol-Deckel (Default: nach 2 Fehlversuchen Fördervariante, §4.4).

2. **Basiscontent generieren**
   - Pro Stufe ein Basismodul, daraus 3 Niveauvarianten ableiten
     (Förder-/Standard-/Vertiefungsversion). Größter realer Aufwandstreiber →
     hier Content wirklich differenzieren, nicht nur umbenennen.

3. **Tests generieren**
   - Pro Stufe 3 niveaugebundene Tests à 20 Fragen. Fachliche Validierung durch den
     Autor kennzeichnen (HITL-Checkpoint) — **nicht** automatisch als final markieren.

4. **ID-Map aufbauen**
   - Stabile IDs vergeben für: alle Einzeltest-Items, (optional) die Mittel-Items je
     Stufe, das kumulative Calculated-Item. In Handoff-JSON ablegen, bevor XML entsteht.
   - Klar markieren, **welche** IDs Einstufungsgrößen sind (Einzeltest/Mittel) und
     welche reine Doku (kumulativ).

5. **`gradebook.xml` schreiben**
   - 3 Test-`grade_item` pro Modul (roh, in Prozent referenzierbar).
   - 1 kumulatives Calculated-Item mit gewichteter Summenformel (§6) — **Doku**.
   - (Optional) je Stufe 1 Mittel-Calculated-Item über die letzten 1–2 Tests (§4.3).

6. **`availability`-JSON pro Kachel schreiben**
   - Jede Niveaukachel: niveau-relative Bedingung auf das **letzte Test-Item** bzw.
     **Mittel-Item** (§4.1/§4.2) — **niemals** auf das kumulative Item.
   - Wiederholschleife mit Deckel (§4.4). `showc` je nach Verhalten (unsichtbar/ausgegraut).

7. **`course.xml` / `module.xml` finalisieren**
   - `enablecompletion=1`; pro Aktivität `completion`-Felder inkl. `completionpassgrade`
     wo sinnvoll.

8. **MBZ packen & Restore-Test**
   - MBZ serialisieren. **Pflicht-QA**: Auf einer Moodle-Instanz wiederherstellen und
     jeden Pfad als Testuser durchklicken. Gezielt prüfen: **steigt ein starker Anfänger
     wirklich auf und ein schwacher Fortgeschrittener wirklich ab?** (Der Ratschen-Test.)
     Außerdem Konvergenz und Wiederhol-Deckel verifizieren.

---

## 8. Grenzen (bewusst außerhalb der MBZ lassen)

- **Echtes adaptives Testing** (IRT / dynamische Schwierigkeitsanpassung pro Frage)
  braucht ein Plugin (z. B. `mod_adaptivequiz`) und ist **nicht MBZ-portabel**. Für ein
  plugin-freies, transportierbares Artefakt beim gewichteten Null-Item-Ansatz (§4) bleiben.
- **Dynamische Formel-Umschaltung zur Laufzeit** gibt es nicht — der Null-Item-Trick
  ist der saubere Ersatz.
- Bei Restore auf eine Instanz **ohne** benötigte Plugins brechen plugin-abhängige
  Bedingungen weg. Bordmittel (Restrict access + Calculated grade) sind der sichere Weg.

---

## 9. Kalibrier-Hinweise (didaktisch, vom Autor zu prüfen)

- **Einstufung von Bewertung trennen** — das ist der wichtigste Punkt. Einstufung über
  aktuelle Leistung (§4), Gewichtung nur fürs Zeugnis (§5/§6).
- Auf-/Abstiegsschwellen **symmetrisch** denken: Wenn Aufstieg ≥ 80 % verlangt, sollte
  Abstieg nicht schon bei 60 % greifen — sonst wird das System instabil oder unfair.
- **Hysterese bewusst dosieren** (§4.3): genug, um Tagesform-Zappeln zu dämpfen; nicht so
  viel, dass echte Niveauänderungen unterdrückt werden. Asymmetrischer Puffer von ~5 %
  ist ein guter Startwert.
- Prozentfenster **überschneidungsfrei** halten (harte Kanten).
- Wiederholschleife immer mit Deckel (§4.4) — Endlosschleife vermeiden.
- **Ratschen-Test** vor Pilotierung: Simuliere einen starken Anfänger und einen
  schwachen Fortgeschrittenen. Bewegen sie sich? Wenn nein, ist die Entkopplung nicht
  sauber umgesetzt.
- Der kumulative Score eignet sich als **abhängige Variable** für eine Pilotierung /
  Design-Science-Evaluation — er ist portabel und instanzunabhängig dokumentierbar.
  Die tatsächliche **Niveaubewegung** (Auf-/Abstiegshäufigkeit) ist eine zweite,
  aussagekräftige Kennzahl für die Durchlässigkeit des Systems.
