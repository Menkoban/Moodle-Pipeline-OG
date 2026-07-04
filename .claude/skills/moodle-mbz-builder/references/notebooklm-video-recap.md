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
7. In der Kurs-JSON den Recap-Platzhalter ersetzen durch
   `{"type": "resource", "name": "Videozusammenfassung", "file": "<pfad>/recap.mp4"}`
   und (falls Widget offen) das Widget regenerieren; `.mbz` erst bei
   `finalize` bauen.

## Spike-Checkliste (vor erster echter Nutzung)

- [ ] Upload eines Markdown-Dossiers funktioniert
- [ ] Video-Overview auf Deutsch verfügbar und didaktisch brauchbar
- [ ] Download des MP4 automatisierbar
- [ ] Gesamtdauer akzeptabel (User informieren)
