# moodle-spielwiese

Eine zweite, **persistente** Moodle-4.5-Instanz unter `C:\moodle-playground` —
Entwicklungsumgebung für eigene Moodle-Plugins und Erprobungsumgebung für
generierte Kurse. Läuft parallel zum sterilen **Gate-Lab** des Skills
`moodle-testinstanz`, ohne es zu berühren.

## Warum zwei Instanzen?

| | Gate-Lab (`moodle-testinstanz`) | Spielwiese (dieser Skill) |
|---|---|---|
| Wesen | steril, Teardown per Default | persistent, absichtlich schmutzig |
| Beantwortet | **Geht diese `.mbz` hoch?** | **Tut der Kurs / das Plugin, was er soll?** |
| Plugins | keine fremden | eigene, per Junction eingehängt |
| Web-UI | nur bei Bedarf, PHP-Server | dauerhaft, Apache + mod_fcgid |
| Ort | `~/.claude/moodle-lab` | `C:\moodle-playground` |
| Ports | MariaDB 3307 · HTTP 8088 | MariaDB **3308** · HTTP **8090** |

Der Wert des Gate-Labs beruht vollständig auf seiner Sterilität: Nur weil dort
nichts Fremdes lebt, ist ein fehlgeschlagener Restore eindeutig als
*Kursfehler* lesbar. Deshalb wird es hier nie mitbenutzt.

> **Das Gate-Lab entscheidet über die `.mbz`, die Spielwiese über Inhalt und
> Logik. Niemals andersherum.**

## Schnellstart

```bash
python scripts/spielwiese.py setup     # einmalig, ~5 min (Zips liegen lokal)
python scripts/spielwiese.py start
# -> http://localhost:8090 · admin / Admin123!
python scripts/spielwiese.py status --json
python scripts/spielwiese.py stop
```

Danach liegt auf dem Desktop eine Verknüpfung **„Moodle Spielwiese"**, die
`start.cmd` aufruft und den Browser öffnet.

## Kommandos

| Aufruf | Wirkung | Stand |
|---|---|---|
| `setup [--force]` | Instanz aufbauen, idempotent (inkl. deutschem Sprachpaket, best effort) | Stufe 1 ✔ |
| `start` / `stop` / `status` | Dienste steuern und prüfen | Stufe 1 ✔ |
| `snapshot <name> \| --list` | Zustand sichern (`db-data` + `data`, Dienste danach wieder hoch) | Stufe 2 ✔ |
| `reset <name> [--snapshot <n>] [--force]` | Delta zeigen, zurückspielen, Moodle wieder hoch | Stufe 2 ✔ |
| `seed` | Testschüler + Beispielkurs anlegen/reparieren, idempotent | Stufe 3 ✔ |
| `import <kurs.mbz> [--schueler]` | `.mbz` dauerhaft einspielen, ohne Teardown | Stufe 3 ✔ |
| `plugin link/unlink/list` / `purge` / `upgrade` | Plugin-Werkstatt (Junction, Caches, Installation) | Stufe 4 ✔ |
| adaptives Durchspielen | KI-Workflow über Playwright, siehe `SKILL.md` | Stufe 5 ✔ |

Alle Kommandos verstehen `--json`.
Exit-Codes: `0` ok · `2` fachlicher Fehler · `3` Umgebung kaputt/fehlt.

Was noch nicht gebaut ist, meldet sich mit Exit 2 und der zugehörigen Stufe —
es tut nie so, als hätte es gearbeitet.

## Bezugsquellen

Nichts davon liegt im Repo; `setup` holt alles von den offiziellen Quellen
bzw. spiegelt die bereits geladenen Zips aus dem Gate-Lab:

- PHP 8.2 NTS x64 — windows.php.net
- MariaDB 10.11 — archive.mariadb.org
- Moodle 4.5 — packaging.moodle.org
- format_tiles — download.moodle.org (Plugin-API)
- **Apache 2.4.68 + mod_fcgid 2.3.10 — apachelounge.com** *(vierte
  Bezugsquelle, hier offengelegt: es ist kein Angebot der ASF, sondern ein
  Fremdbuild — verlangt VC++-Redistributable ≥ 14.51)*

## Aufbau auf der Platte

```
C:\moodle-playground\
  php\        PHP 8.2 NTS — php.exe (CLI) und php-cgi.exe (FastCGI)
  mariadb\    MariaDB 10.11, Port 3308
  db-data\    Datadir  ─┐
  data\       moodledata ┴─ zusammen der Inhalt eines Snapshots
  moodle\     Moodle 4.5 + format_tiles — DocumentRoot
  apache\     Apache 2.4 + mod_fcgid, conf\httpd.conf ist generiert
  _dl\        Zips (Rebuild-Cache)
  snapshots\  benannte Zustände (je: db-data\ + data\ + meta.json)
  .wartung    nur während snapshot/reset: Lock gegen parallelen Start
  start.cmd · stop.cmd · mariadbd.log
```

Der Snapshot `nullzustand` (frisch installiertes, leeres Moodle) wird in
Stufe 2 angelegt und ist der Anker für „alles wegwerfen, neu anfangen":
`spielwiese.py reset nullzustand`.

Bewusst **außerhalb** von OneDrive: der Moodle-Baum hat ~29.000 Dateien, dazu
kämen offene InnoDB-Dateien. Auf dem Desktop liegt nur die Verknüpfung.

## Warum Apache und nicht der eingebaute PHP-Server

Gemessen, nicht vermutet: Der eingebaute Server ist unter Windows **strikt
seriell** — 3 parallele Requests à 3 s brauchen 9.189 ms mit und 9.186 ms ohne
`PHP_CLI_SERVER_WORKERS=8`; die Variable setzt `fork()` voraus und ist auf
Windows wirkungslos. Für eine Instanz, in der man klickt, während im
Hintergrund ein Restore läuft, ist das untauglich. Begründung im Detail:
`Desktop\Moodle-Werkstatt\docs\adr\0002-apache-fastcgi-statt-eingebautem-php-server.md`.

## Fallstricke

Siehe `SKILL.md`, Abschnitt „Fallstricke, die hier schon bezahlt sind" —
`extension_dir` absolut, `cgi.force_redirect=0`, `AcceptPathInfo On`,
Fcgid-Timeouts hoch, Dev-Block vor `lib/setup.php`, MariaDB nie abschießen.

## Stand

**Alle fünf Stufen des Plans stehen und sind abgenommen** — inklusive
zweier adversarialer Review-Runden durch separate Agenten (31 Befunde:
30 gefixt bzw. dokumentiert, 1 bewusst verworfen). Die adaptive
Verzweigungslogik wurde am Kurs `hydraulik-adaptiv` in beide Richtungen
(Aufstieg 100 %, Abstieg 0 %) real im Browser belegt. Oberfläche Deutsch;
Login-Seite ~1,2 s statt anfangs ~3,7 s (IPv6-Listener + opcache + Caches).
Details: `Desktop\Moodle-Werkstatt\STATUS.md` (Stand), `PLAN.md`
(Vorgehen), `CONTEXT.md` (Begriffe), `docs\adr\` (warum).
