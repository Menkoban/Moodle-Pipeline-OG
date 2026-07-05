# Video-Recap via NotebookLM (Best-Effort-Workflow)

Automatisiert den bislang manuellen Platzhalter „Videozusammenfassung" im
Kurs-Recap. Status: **Folgeprojekt** — vor Produktivnutzung einen manuell
begleiteten Spike fahren. Auslöser: `video_recap`-Action aus dem Editor-Widget
oder direkte User-Bitte.

## Grundsätze

- **Keine Zugangsdaten an Claude.** Der User loggt sich selbst in Chrome bei
  notebooklm.google.com ein; Claude steuert danach die eingeloggte Session
  über die Browser-Tools (claude-in-chrome). Niemals Passwörter entgegennehmen
  oder in Login-Formulare tippen (Google-Bot-Erkennung + 2FA machen das
  ohnehin unzuverlässig).
- **Best-Effort:** UI-Automatisierung ist fragil (Google-UI ändert sich).
  Fallback ist immer: Platzhalter bleibt im Kurs, User erzeugt das Video
  manuell.
- **Dauer kommunizieren:** Die Video-Generierung dauert mehrere Minuten.
  User vorab informieren; geduldig pollen, NICHT eng loopen.

## Ablauf

1. Dossier erzeugen:
   `python <skill-dir>/scripts/export_course_dossier.py course.json -o dossier.md`
   — EIN konsolidiertes Markdown (Handlungssituation, Lernziele, alle
   Seiten/Bücher, Auftragstext, Glossar; OHNE Quiz-Lösungen, ohne verborgene
   Lehrkraft-Sektion, ohne Datei-/Link-/Organisations-Aktivitäten). Ein
   Dossier statt vieler Einzel-PDFs: weniger Quellen, kohärenterer Kontext,
   volle Kontrolle darüber, was das Video „weiß".
2. User bitten, sich in Chrome bei NotebookLM einzuloggen; Browser-Tools laden
   (ToolSearch, gebündelt).
3. Neues Notebook anlegen (Titel = Kurs-Shortname), `dossier.md` als Quelle
   hochladen.
4. Video-Overview anfordern (Sprache Deutsch wählen, sofern verfügbar —
   Qualität im Spike prüfen).
5. Auf Fertigstellung warten (Minuten; moderat pollen).
6. MP4 herunterladen → im Kursordner ablegen.
7. Recap-Platzhalter ersetzen — **Ein-Schritt-Einbau** mit dem Helfer
   `scripts/set_recap_video.py` (ersetzt die „Videozusammenfassung"-Leerstelle):
   - Teilen-Link:  `python set_recap_video.py course.json --url https://…`
   - Datei (MP4/Audio): `python set_recap_video.py course.json --file "<pfad>/recap.mp4"`
   Danach normal bauen (`make_materials` → `build_mbz` → `validate` → `preview`);
   falls das Widget offen ist, regenerieren und `.mbz` erst bei `finalize` bauen.
   Der Link-Weg (`url`) ist schlanker (kein großes Video in der Sicherung).

**Tipp:** `export_course_dossier.py` erzeugt die NotebookLM-Quelle; lege daneben
optional einen kurzen Auftragstext (`*_notebooklm_brief.txt`: deutsche
Audioübersicht, ~2–3 min, einfache Sprache, keine Testlösungen) als Vorlage fürs
„Anpassen/Customize"-Feld ab.

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

**Automatisierungs-Fallen (beim nächsten Lauf beachten):**
- `computer type` mit >10k Zeichen läuft in einen 30s-CDP-Timeout, tippt aber
  im Hintergrund weiter — Dossier in **Blöcken à ~3–5k Zeichen** eintippen und
  danach per Screenshot verifizieren, dass das Ende angekommen ist.
- Beim ersten NotebookLM-Besuch erscheint ein „Willkommen"-Info-Dialog (nur
  Ok) — wegklicken, sonst blockiert er die Klicks dahinter.
- NotebookLM benennt das Notebook automatisch nach der Quelle.
