# Video-Recap via NotebookLM (Pflicht-Schritt jedes Kurses)

Füllt den Platzhalter „Videozusammenfassung" im Kurs-Recap. **Dieser Schritt
gehört zu jedem fertigen Kurs** (siehe SKILL.md „Quick start" Schritt 6 und
course-design.md Pipeline) – nicht optional. Status: **erprobt** — kompletter
Durchlauf am 2026-07-05 (Kurs „Drehen und Fräsen") und am 2026-07-05 erneut für
den Kurs „Künstliche neuronale Netze". Auslöser: automatisch am Ende jedes
Builds, die `video_recap`-Action aus dem Editor-Widget oder direkte User-Bitte.

## Grundsätze

- **Immer ausführen, außer es geht technisch nicht.** Der Video-Recap ist der
  letzte Standard-Schritt jedes Kurses. Nur wenn kein Browser verbunden ist
  (`list_connected_browsers` leer) oder der Nutzer bei NotebookLM nicht
  eingeloggt ist, entfällt er – dann Platzhalter lassen, Nutzer informieren,
  Video nachziehen. Nie kommentarlos überspringen.
- **Keine Zugangsdaten an Claude.** Der User loggt sich selbst in Chrome bei
  notebooklm.google.com ein; Claude steuert danach die eingeloggte Session
  über die Browser-Tools (claude-in-chrome). Niemals Passwörter entgegennehmen
  oder in Login-Formulare tippen (Google-Bot-Erkennung + 2FA machen das
  ohnehin unzuverlässig).
- **Best-Effort in der Ausführung:** UI-Automatisierung ist fragil (Google-UI
  ändert sich). Bricht sie ab: Platzhalter bleibt im Kurs, User erzeugt das
  Video manuell – aber der Schritt wird bei jedem Kurs *versucht*.
- **Dauer kommunizieren:** Die Video-Generierung dauert mehrere Minuten.
  User vorab informieren; geduldig pollen, NICHT eng loopen.

## Ablauf (erprobt 2026-07-05 — exakt so ausführen)

1. **Dossier erzeugen:**
   `python <skill-dir>/scripts/export_course_dossier.py course.json -o dossier.md`
   — EIN konsolidiertes Markdown (Handlungssituation, Lernziele, alle
   Seiten/Bücher, Auftragstext, Glossar; OHNE Quiz-Lösungen, ohne verborgene
   Lehrkraft-Sektion, ohne Datei-/Link-/Organisations-Aktivitäten). Ein
   Dossier statt vieler Einzel-PDFs: weniger Quellen, kohärenterer Kontext,
   volle Kontrolle darüber, was das Video „weiß".
2. **Browser verbinden:** claude-in-chrome-Tools laden (ToolSearch,
   gebündelt), `tabs_context_mcp{createIfEmpty:true}`. Wenn kein Browser
   verbunden ist (`list_connected_browsers` = leer): User bitten, die
   Claude-Erweiterung in Chrome mit seinem Konto anzumelden. Der User loggt
   sich selbst bei notebooklm.google.com ein.
3. **Notebook + Quelle:** notebooklm.google.com öffnen (legt automatisch ein
   leeres Notebook an; „Willkommen"-Dialog mit Ok wegklicken). Quelle
   einbringen über **„Quellen hinzufügen → Kopierter Text"** — NICHT
   „Dateien hochladen" (Datei-Upload aus der Claude-Sandbox ist blockiert,
   nur session-geteilte Dateien). Dossier-Inhalt in Blöcken à ~3–5k Zeichen
   eintippen (ein Riesenblock läuft in einen 30s-CDP-Timeout), Ende per
   Screenshot verifizieren, „Einfügen" klicken. NotebookLM benennt das
   Notebook automatisch nach der Quelle.
4. **Videoübersicht anfordern:** Studio-Kachel „Videoübersicht" → Chevron
   (>) öffnet „Video-Zusammenfassung anpassen": Format „Erklärvideo",
   **Sprache Deutsch** prüfen, in das Fokus-Feld („Worauf sollen sich die
   KI-Moderatoren konzentrieren?") den **Brief** eintippen (Vorlagen unten —
   für den Recap-Platzhalter IMMER die Rückblick-Variante), „Erstellen".
5. **Warten:** Generierung ~5 min; moderat pollen (Screenshots im
   ~1-Minuten-Abstand). Fertiges Video erscheint als Studio-Eintrag mit
   Titel + Länge.
6. **Herunterladen:** ⋮-Menü des Studio-Eintrags → „Herunterladen" → MP4
   landet im Browser-Download-Ordner (`~/Downloads`, Titel mit Unterstrichen).
   In den Kursordner (`assets/`) kopieren.
7. **Recap-Platzhalter ersetzen** — Ein-Schritt-Einbau mit
   `scripts/set_recap_video.py` (idempotent, ein erneuter Lauf tauscht das
   Video aus):
   - Datei (MP4): `python set_recap_video.py course.json --file "<pfad>/recap.mp4"`
   - Teilen-Link: `python set_recap_video.py course.json --url https://…`
     (schlanker: kein großes Video in der Sicherung — aber Lernende brauchen
     dann Zugriff auf den Link)
   Danach normal bauen (`make_materials` → `build_mbz` → `validate` →
   `preview`) und **verifizieren**, dass die Video-Ressource im Kurs-Recap
   sitzt; falls das Widget offen ist, regenerieren — `.mbz` erst bei
   `finalize` bauen.

**Der Brief entscheidet über die Funktion des Videos!** Ohne klare Vorgabe
erzählt NotebookLM die Handlungssituation als NEUE Geschichte — das Video
fühlt sich dann wie ein Einstieg an, obwohl es im Kurs-Recap steht (real
passiert am 2026-07-05). Lege daher fest, WELCHE Rolle das Video hat, und
lege den Brief als `*_notebooklm_brief.txt` neben das Dossier:

- **Kurs-Recap (Standard, ersetzt den Platzhalter):** ausdrücklich als
  RÜCKBLICK framen: „Die Lernenden haben das Modul bereits durchgearbeitet.
  Sprich durchgehend rückblickend (‚In diesem Modul haben Sie gelernt…').
  Beginne NICHT mit der Handlungssituation als neuer Geschichte — erinnere
  höchstens kurz daran. Fasse die Kernpunkte zusammen, Schluss: Transfer-
  Impuls + Gratulation zum abgeschlossenen Modul." Dazu: Zielgruppe,
  B1-Sprache, Sie-Anrede, 2–3 min, keine Testlösungen.
- **Einstieg/Advance Organizer (optionale zweite Variante für Abschnitt 1):**
  „Neugierig machen, die Handlungssituation als offene Frage aufwerfen,
  Überblick über das Kommende geben, nichts auflösen."

Hinweis: Die Minutenangabe ist für NotebookLM nur ein Richtwert (bestellt
2–3 min, geliefert 5:32).

## Spike-Checkliste — BESTANDEN (2026-07-05, Kurs „Drehen und Fräsen")

- [x] Quelle einbringen funktioniert — ABER: Datei-Upload aus der Sandbox ist
  blockiert (nur session-geteilte Dateien). **Robuster Weg: „Kopierter Text"**
  (Quellen hinzufügen → Kopierter Text → Dossier-Inhalt eintippen → Einfügen).
- [x] Video-Overview auf Deutsch verfügbar: Kachel „Videoübersicht" →
  Chevron öffnet „Anpassen" (Format Erklärvideo, Sprache Deutsch, Fokus-Feld
  für den Brief). Ergebnis war didaktisch brauchbar (5:32 min, Titel und
  roter Faden aus der Handlungssituation übernommen).
- [x] Download klappt: ⋮-Menü der fertigen Videoübersicht → „Herunterladen"
  → MP4 landet im Browser-Download-Ordner (~29 MB bei 5:32).
- [x] Gesamtdauer akzeptabel: Generierung ~5 min (moderat pollen).

Alle dabei gefundenen Automatisierungs-Fallen sind oben in den Ablauf
eingearbeitet (Kopierter Text statt Datei-Upload, Chunk-Typing,
Willkommens-Dialog). Zweiter Lauf am selben Tag: Rückblick-Brief → Titel
„Rückblick: Drehen & Fräsen", 4:17 min — das Framing im Brief wirkt.
