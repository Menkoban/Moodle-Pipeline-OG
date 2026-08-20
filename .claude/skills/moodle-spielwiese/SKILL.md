---
name: moodle-spielwiese
description: >-
  Betreibt die persistente Moodle-4.5-Spielwiese unter C:\moodle-playground
  (Apache 2.4 + mod_fcgid auf Port 8090, MariaDB auf 3308) — die
  Entwicklungsumgebung für eigene Moodle-Plugins und die Erprobungsumgebung,
  in der generierte Kurse eingespielt und als Testschüler durchgeklickt
  werden. Use this skill whenever the user wants to start/stop/check the
  Moodle-Spielwiese ("Spielwiese starten", "Moodle-Playground hochfahren",
  "läuft die Spielwiese?"), an eigenen Moodle-Plugins arbeiten will, oder
  einen Kurs dauerhaft einspielen und als Schüler durchklicken möchte.
  ABGRENZUNG: Geht es nur um die Frage, ob eine .mbz überhaupt restauriert
  ("teste die Kurssicherung", "Restore-Stacktrace"), ist der Skill
  moodle-testinstanz zuständig — nicht dieser.
---

# moodle-spielwiese — persistente Moodle-Instanz zum Entwickeln und Erproben

Zweite Moodle-4.5-Instanz **neben** dem Gate-Lab, mit gegenteiligem Wesen:
dauerhaft laufende Web-UI, eigene Plugins im Baum, Testschüler, angesammelte
Kurse. Bedient wird sie primär **durch die KI** über ein Entry-Skript mit
festem Kontrakt; der Desktop-Starter ist der Nebeneingang für den Menschen.

## Zuständigkeitsregel (VERBINDLICH)

> Das **Gate-Lab** (`moodle-testinstanz`) entscheidet über die `.mbz`.
> Die **Spielwiese** entscheidet über Inhalt und Logik.
> Niemals andersherum.

Ein Kurs, der in der Spielwiese hochgeht, ist **kein** grünes Gate — hier
hängen eigene Plugins im Baum, die das Ergebnis verfälschen können. Der
Umkehrschluss „läuft bei mir in der Spielwiese, also ist die Sicherung gut"
ist die zentrale Fehlbedienung, gegen die dieses Modell schützt.

## Entry-Skript & Vertrag

```
~/.claude/skills/moodle-spielwiese/scripts/spielwiese.py
(Override: Env MOODLE_SPIELWIESE_HOME, Default C:\moodle-playground)
```

| Aufruf | Bedeutung | Stand |
|---|---|---|
| `setup [--force]` | Instanz aufbauen, idempotent | **Stufe 1** |
| `start` | MariaDB + Apache hochfahren (verweigert bei Wartungs-Lock oder `*.vor-reset`-Trümmern) | **Stufe 1** |
| `serve` | Persistenter Daemon-Server (`serve.py` mit `IsDaemon: true`) — überwacht Dienste und hält localhost dauerhaft aktiv | **Zusatz** |
| `stop` | beide stoppen (DB **sauber** über `mariadb-admin`; meldet Fehlschlag statt still weiterzugehen) | **Stufe 1** |
| `status` | Zustand beider Dienste + HTTP-Probe; „up" nur bei verifizierten eigenen PIDs **und** antwortendem Login-Formular | **Stufe 1** |
| `snapshot <name> \| --list` | Zustand sichern: Dienste stoppen (Prozessende belegt), `db-data` + `data` kopieren, Dienste wieder hoch, wenn sie liefen | **Stufe 2** |
| `reset <name> [--snapshot <n>] [--force]` | Delta **vor** dem Stoppen benennen, zurückspielen (atomar mit Rollback), Moodle wieder hochfahren. `--snapshot` sichert vorher, `--force` überspringt die Delta-Ausgabe | **Stufe 2** |
| `seed` | 5 Testschüler + Beispielkurs anlegen bzw. **reparieren** (entsperrt Bestandskonten, setzt abweichende Passwörter zurück); idempotent | **Stufe 3** |
| `import <kurs.mbz> [--schueler]` | Kurs dauerhaft einspielen (KEIN Teardown); `--schueler` schreibt die Testschüler ein (Exit 2, wenn es noch keine gibt) | **Stufe 3** |
| `plugin link <quelle>` | Quelle per Junction einhängen; Zielname folgt IMMER dem `component` (Moodle erzwingt Ordnername==Pluginname) | **Stufe 4** |
| `plugin unlink <name>` · `list` | Junction entfernen (Quelle bleibt) · Bestand mit Zustandsprüfung | **Stufe 4** |
| `purge` · `upgrade` | Caches leeren · Upgrade-Lauf (installiert frisch eingehängte Plugins) | **Stufe 4** |
| `debug [schnell\|entwickler]` | Debug-Modus zeigen/umschalten: **schnell** ≈ 0,1 s/Seite (Fehler+Warnungen sichtbar, Default) · **entwickler** ≈ 1 s/Seite (volle Backtraces) | Zusatz |

Alle Kommandos des Kontrakts sind umgesetzt (Stufen 1–4).

## Snapshots & Reset (Stufe 2)

Ein Snapshot ist die Kopie von `db-data` + `data` bei **nachweislich**
gestoppten Diensten. Er umfasst absichtlich NICHT den `moodle/`-Baum:
eingehängte Plugin-Quellen überleben jeden Reset, und ein Reset auf einen
Snapshot, der ein Plugin noch nicht kannte, testet dessen Erstinstallation
gratis mit.

- **Namen:** alphanumerischer Beginn, dann `A-Za-z0-9._-`, max. 64 Zeichen.
- **Nie halb gültig:** kopiert wird nach `_unfertig_<name>` und erst nach
  vollständiger Kopie (inkl. `meta.json` mit Zählung) umbenannt.
- **Guards:** kein Snapshot/Reset bei laufender DB (Exit 2); ein `mariadbd`
  auf unserem Datadir, das nicht auf 3308 lauscht, ist ein *fremder Prozess*
  und blockiert ebenfalls (Exit 2). Die Datadir-Erkennung parst die
  Kommandozeile und vergleicht **pfadnormalisiert** — kein Substring-Match.
- **Wartungs-Lock:** während `snapshot`/`reset` liegt `.wartung` im
  Instanzordner; `start` (auch über den Desktop-Starter) verweigert solange.
  Ein Lock mit toter Besitzer-PID wird still weggeräumt; ein **unlesbares**
  Lock blockiert (fail-closed) und muss von Hand geklärt werden.
- **Trümmer-Regel:** existiert `db-data.vor-reset` oder `data.vor-reset`,
  verweigern `start` und `reset` — das ist womöglich der letzte gute Zustand
  eines abgebrochenen Resets. Erst manuell klären.
- **Delta statt Zwangssicherung:** `reset` benennt vor dem Stoppen, was seit
  dem Zielsnapshot entstanden ist (Kurse/Nutzer/Plugins). Keine Rückfrage,
  kein erzwungenes Backup — `--snapshot <n>` sichert auf Wunsch,
  `--force` ist für den Skriptbetrieb.

**Exit-Disziplin** (identisch zu `moodle-testinstanz`):
`0` ok · `2` fachlicher Fehler · `3` Umgebung kaputt/fehlt.
`status` liefert `0`, wenn **beide** Dienste laufen, sonst `3`.

**`--json`** verstehen alle Kommandos und liefern EIN Objekt auf stdout:

```json
{"status":"up","spielwiese":"C:\\moodle-playground","instanz_vorhanden":true,
 "mariadb":{"port":3308,"laeuft":true,"pid":1234},
 "apache":{"port":8090,"laeuft":true,"pid":5678},
 "http":{"url":"http://localhost:8090/login/index.php","code":200,
         "login_formular":true},
 "moodle_version":"4.5.12+ (Build: 20260708)"}
```

## Feste Zahlen

| | Gate-Lab | Spielwiese |
|---|---|---|
| Ort | `~/.claude/moodle-lab` | `C:\moodle-playground` |
| MariaDB-Port | 3307 | **3308** |
| Webserver-Port | 8088 | **8090** |
| Webserver | eingebauter PHP-Server | **Apache 2.4 + mod_fcgid** |
| Oberflächensprache | Englisch | **Deutsch** (Setup installiert das de-Paket, best effort) |

Zugänge: `admin` / `Admin123!` · (ab Stufe 3) `schueler01`–`schueler05` /
`Schueler123!`. Apache lauscht bewusst nur auf `127.0.0.1` und setzt
`Require local` — Testkonten mit bekannten Passwörtern gehören nicht ins Netz.

## Typische Nutzung

```bash
python ~/.claude/skills/moodle-spielwiese/scripts/spielwiese.py setup
python ~/.claude/skills/moodle-spielwiese/scripts/spielwiese.py start
python ~/.claude/skills/moodle-spielwiese/scripts/spielwiese.py status --json
python ~/.claude/skills/moodle-spielwiese/scripts/spielwiese.py stop
```

Für alles, was Oberfläche ist, danach der Playwright-MCP gegen
`http://localhost:8090`.

## Aufbau (was `setup` tut)

1. Zips aus dem Gate-Lab nach `_dl\` spiegeln (spart ~210 MB Download).
2. `setup_lab.py` des Skills **`moodle-testinstanz` wiederverwenden** (nicht
   kopieren) mit `MOODLE_LAB_HOME=C:\moodle-playground --port 3308
   --wwwport 8090`. Das Flag `--wwwport` stammt aus genau diesem Vorhaben.
3. `php-cgi.exe` sicherstellen (steckt im `php.zip`).
4. `php.ini` neu schreiben — `extension_dir` **absolut** und die
   CGI-Schalter, siehe Fallstricke.
5. Apache + `mod_fcgid` von Apache Lounge holen, `httpd.conf` erzeugen und
   von Apache selbst prüfen lassen (`httpd -t` muss „Syntax OK" sagen).
6. Dev-Einstellungen in `config.php` **vor** `require lib/setup.php` einsetzen.
7. `start.cmd`, `stop.cmd`, Desktop-Verknüpfung „Moodle Spielwiese".

`setup` ist idempotent und beliebig oft aufrufbar.

## Stufe 5 — adaptive Kurse maschinell durchspielen (Workflow)

Stufe 5 ist bewusst KEIN Python-Kommando, sondern ein Workflow der KI mit
dem Playwright-MCP — Bewertungslogik ist nur mit echten Teilnehmerkonten
prüfbar (Admin-Vorschau schreibt keine Noten):

1. Ausgangszustand wählen: `reset bestueckt` (oder gezielter Snapshot).
2. `import <adaptiver-kurs.mbz> --schueler` — die Soll-Erwartungen stehen
   in der `course.pathmap.json` des Kurs-Ordners (Sections je Niveau,
   Schwellen, Einstieg).
3. Playwright: als `schueler01` anmelden, Test der Einstiegsstufe mit
   GEZIELTER Punktzahl abschließen (Antworten stehen in der Kursdefinition).
4. Kursseite prüfen: Genau die erwartete Niveau-Kachel der nächsten Stufe
   muss sichtbar geworden sein — andere nicht.
5. Gegenrichtung mit `schueler02` (absichtlich unter der Abstiegsschwelle).

Erprobt am Kurs `hydraulik-adaptiv` (2026-07-18): 100 % auf S1-Mittel →
S2-Fortgeschritten öffnet; 0 % → S1-Förder-Kachel + S2-Anfänger öffnen;
jeweils nichts anderes. Browser-Eigenheit: Nach `Submit`-Klicks mit
5-s-Timeout NICHT erneut klicken, sondern per Snapshot prüfen, wo die
Seite steht — der Klick war fast immer schon durch (Moodle rendert nur
langsam), und ein Doppel-Klick verbraucht Login-Token oder Versuche.

## Fallstricke, die hier schon bezahlt sind

- **`extension_dir` muss absolut sein.** Das Lab schreibt `extension_dir="ext"`
  relativ; das funktioniert nur, solange PHP im PHP-Ordner startet. Von Apache
  gestartetes `php-cgi.exe` hat ein anderes Arbeitsverzeichnis und lädt dann
  **keine einzige** Extension — Moodle stirbt an fehlendem `mysqli`.
- **`cgi.force_redirect = 0`** ist Pflicht, sonst antwortet `php-cgi.exe` mit
  „Security Alert! The PHP CGI cannot be accessed directly."
- **`cgi.fix_pathinfo = 1` + `AcceptPathInfo On`**, sonst funktioniert
  `/pluginfile.php/...` nicht (Moodles „slasharguments").
- **`FcgidIOTimeout`/`FcgidBusyTimeout` hochsetzen.** Die Vorgabe von 40 s
  bricht mitten in einem Moodle-Upgrade oder einem großen Restore ab.
- **Dev-Block gehört VOR `require_once(__DIR__.'/lib/setup.php')`.** Danach
  gesetzte `$CFG`-Werte wirken nicht mehr.
- **MariaDB niemals abschießen.** `stop` fährt über `mariadb-admin shutdown`
  herunter und prüft, dass der Prozess wirklich weg ist. Ein abgeschossenes
  `mariadbd` hinterlässt halb geschriebenes InnoDB — daran hängt Stufe 2.
- **`mariadbd` wird über die Kommandozeile identifiziert**, nicht über den
  Prozessnamen: Im Gate-Lab kann ein zweites laufen, das uns nichts angeht.
  Der Datadir wird geparst und **pfadnormalisiert** verglichen — ein
  Substring-Match scheitert an gemischten Pfadstilen
  (real beobachtet: `C:\Users\User/.claude/moodle-lab\db-data`).
- **opcache läuft MIT mtime-Validierung** (`validate_timestamps=1`,
  `revalidate_freq=0`): Quelländerungen wirken sofort, nur das
  Neu-Kompilieren entfällt. Die frühere „kein opcache"-Regel galt dem
  Stale-Bytecode-Risiko — das ist damit vom Tisch. `cachejs` und
  `langstringcache` sind AN; nach JS-/Sprachdatei-Änderungen: `purge`.
- **DEVELOPER-Debug kostet ~1 s PRO SEITE — durch Design.** Moodle
  validiert in dem Modus Plugin- und Klassenkarten bei jedem Request neu
  (hunderte Verzeichnis-Stats); kein Cache, kein opcache und keine
  Defender-Ausnahme ändern daran etwas (alles gemessen). Deshalb ist
  `debug schnell` (DEBUG_NORMAL) der Default — Fehler, Warnungen und
  Fehlerseiten bleiben sichtbar — und `debug entwickler` der Schalter für
  die Backtrace-Jagd. Messreihe: 3687 ms (Start) → 1141 ms (IPv6+opcache+
  Caches) → **78 ms** (debug schnell).
- **`localhost` kostet ohne IPv6-Listener 2 s pro Hop.** Windows löst
  `localhost` zuerst auf `::1` auf; lauscht Apache nur auf `127.0.0.1`,
  zahlt jeder Request (und jeder Redirect-Hop!) ~2 s Fallback. Gemessen:
  statische Datei 2046 ms via localhost, 0 ms via 127.0.0.1. Deshalb
  lauscht Apache auf BEIDEN Loopback-Adressen. Gesamteffekt der
  Tempo-Runde: Login-Seite 3687 → ~1150 ms.
- **`--als` gibt es nicht mehr:** Moodles `upgradelib` wirft
  `plugin_misplaced_exception`, sobald der Ordnername nicht zum
  `component` passt — ein abweichender Zielname bricht ALSO IMMER das
  nächste `upgrade`. Der Zielordner heißt darum stets wie das Plugin.
- **Junction-Prüfungen nie mit `os.path.exists`:** Es folgt dem Junction
  und meldet False, wenn die QUELLE fehlt — die tote Junction bliebe im
  Baum liegen. `lexists`/Reparse-Point-Attribut verwenden.
- **Junctions nicht über `cmd /c mklink` anlegen:** cmd expandiert `%VAR%`
  selbst innerhalb von Anführungszeichen und deutet `&` als
  Befehlstrenner. `_winapi.CreateJunction` parst nichts.
- **PIDs nie ohne Imagenamen prüfen.** `httpd.pid` überlebt einen Kill;
  nach Windows-PID-Recycling zeigt sie auf einen fremden Prozess. Jede
  Prüfung, an der ein `taskkill` hängt, verlangt den Imagenamen
  (`httpd.exe`), und nach verifiziertem Stopp wird die PID-Datei gelöscht.
- **Moodle legt `data\secret\key\sodium.key` schreibgeschützt an** — ein
  nacktes `shutil.rmtree` bricht daran ab. Alle Löschpfade laufen über
  `loesche_baum()`, das den Schreibschutz nimmt und erneut versucht.
- **Das Apache-Lounge-Zip hat eine Markierungsdatei als ersten Eintrag**
  (`-- Win64 VS18  --`), nicht den Ordner `Apache24/`. Der abzuschneidende
  Wurzelordner wird beim Entpacken ausdrücklich benannt, nie geraten.
- **`PHP_FCGI_MAX_REQUESTS` steht auf 0** (PHP beendet sich nie selbst) —
  stünde dort derselbe Wert wie in `FcgidMaxRequestsPerProcess`, gäbe es die
  klassische sporadische „read data timeout"-500er-Race.
- **Logs rotieren nicht** (bewusst): `rotatelogs.exe` als Piped-Log-Kind
  würde das Prozessmanagement genau dort verkomplizieren, wo PID-Recycling
  schon heikel ist. Bei Bedarf `apache\logs\` gelegentlich leeren.

## Grenzen

- Eine Instanz, eine Moodle-Version (4.5 LTS), Windows-only (portable Binaries).
- `Require local` — nicht im Netz erreichbar, das ist Absicht. Zusätzlich
  werden Entwickler-/Metadateien (composer.*, `*.dist`, `install.xml`, `*.md`,
  `*.txt`, …) nicht statisch ausgeliefert und Versions-Banner unterdrückt.
- Stufen 3–5 (Testschüler/Import, Plugin-Werkstatt, maschinelles
  Durchspielen adaptiver Kurse) sind geplant, aber noch nicht gebaut. Stand:
  `Desktop\Moodle-Werkstatt\STATUS.md`.
