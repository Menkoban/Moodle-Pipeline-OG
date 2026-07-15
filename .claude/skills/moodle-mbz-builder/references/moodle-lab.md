# Lokales Moodle-Restore-Lab (Projekt-Konvention, ohne Docker)

Portable Moodle-Testinstanz auf DIESEM Rechner zum **echten Restore-Testen**
und zur **Diagnose von Restore-Fehlern** (zeigt bei DEVELOPER-Debugging das
exakte fehlgeschlagene SQL-Statement). Zwei reale Restore-Blocker wurden NUR
hierüber gefunden — statische Analyse der .mbz versagte beide Male:
`$@NULL@$` in einem XML-Attribut (2026-07-12) und `$@NULL@$` in der
NOT-NULL-Spalte `mdl_feedback_item.name` (2026-07-15).

## Lage & Bestandteile

```
C:\Users\User\.claude\moodle-lab\
  php\        portable PHP 8.2 (NTS x64)          php.zip     (Rebuild-Quelle)
  mariadb\    MariaDB 10.11, Minimal-Binaries      mariadb.zip
  db-data\    MariaDB-Datadir (Port 3307, root/root)
  moodle\     Moodle 4.5 + format_tiles            moodle.zip, tiles45.zip
  data\       moodledata ($CFG->dataroot)
```

- Moodle-Login: `admin` / `Admin123!` · wwwroot `http://localhost:8088`
- `config.php`: DB `127.0.0.1:3307`, user `root`/`root`, DB-Name `moodle`;
  **debug = DEVELOPER + debugdisplay=1 sind bereits an.**
- Dauerhafter Standort seit 2026-07-15 (vorher flüchtig unter `%TEMP%`);
  entspricht dem `MOODLE_LAB_HOME`-Vertrag des `moodle-testinstanz`-Skills.
  Die beiliegenden Zips erlauben den Wiederaufbau (~15 min). Das Moodle ist
  **minimal extrahiert** (admin/cli hat nur install/restore_backup/upgrade) —
  fehlende Dateien bei Bedarf aus `moodle.zip` nachziehen.

## Bedienung

```bash
LAB="C:/Users/User/.claude/moodle-lab"

# 1) DB starten (im Hintergrund laufen lassen)
"$LAB/mariadb/bin/mariadbd.exe" --datadir="$LAB/db-data" --port=3307 --console

# 2) Restore per CLI (aus dem moodle-Ordner heraus!) — DER Diagnose-Schritt
cd "$LAB/moodle"
"$LAB/php/php.exe" admin/cli/restore_backup.php \
    --file="<absoluter Pfad>/kurs.mbz" --categoryid=1
# Erfolg endet mit:  == ID des wiederhergestellten Kurses: N ==
# Fehler zeigen das ECHTE Problem (z. B. dmlwriteexception mit vollem INSERT).

# 3) Ergebnis in der DB verifizieren (Beispiele)
"$LAB/mariadb/bin/mariadb.exe" --port=3307 -h 127.0.0.1 -u root -proot moodle \
  -e "SELECT COUNT(*) FROM mdl_course_modules WHERE course=N;"
#   Quiz-Slots, Glossar-Einträge, feedback_items, mdl_files analog abfragen.

# 4) Optional: Web-UI (mehrere Worker, sonst hängt der Single-Thread-Server)
cd "$LAB/moodle" && PHP_CLI_SERVER_WORKERS=8 "$LAB/php/php.exe" -S localhost:8088

# 5) DB sauber stoppen (KEIN mysqladmin im Minimal-Paket!)
"$LAB/mariadb/bin/mariadb.exe" --port=3307 -h 127.0.0.1 -u root -proot -e "SHUTDOWN;"
```

## Wann einsetzen (Empfehlung)

- **Immer bei Restore-Fehlern auf dem Ziel-Moodle des Users** — die dortigen
  Fehlerseiten sind ohne Admin-Debugging wertlos (die „Weitere
  Informationen"-Seite zeigt z. B. irreführend „Notwendiger Parameter
  (contextid) fehlt", egal was wirklich schiefging).
- **Nach größeren Generator-Änderungen** (neue Aktivitätstypen, neue
  XML-Strukturen) als E2E-Gate zusätzlich zu `validate_mbz.py`.

## Gotchas

- **Unvollständige Moodle-Extraktion möglich:** Fehler wie *„Attempt to
  require a JavaScript file that does not exist (/comment/comment.js)"*
  bedeuten fehlende Dateien im Lab, nicht einen Kurs-Defekt — fehlende
  Dateien aus `moodle.zip` nachextrahieren und erneut versuchen.
- Die Warnung *„existing temptables found when disposing database"* nach
  einer Exception ist Folge-Rauschen, keine eigene Ursache.
- Admin-**Vorschau**-Versuche in Quizzen schreiben keine Noten — bewertungs-
  abhängige Features (adaptive Fenster) nur mit echtem Teilnehmer testen.
- CLI-Meldung „Unknown setting: questionbank" beim Laden ist harmlos.
- Screenshots auf format_tiles-Seiten timeouten sporadisch — Prüfungen
  besser per DOM/JS oder direkt per SQL.
