#!/usr/bin/env python3
"""spielwiese.py — Entry-Skript der Moodle-Spielwiese.

Baut und betreibt eine zweite, PERSISTENTE Moodle-4.5-Instanz unter
C:\\moodle-playground, getrennt vom sterilen Gate-Lab (~/.claude/moodle-lab).

    <pg>/php       portable PHP 8.2 NTS (php.exe UND php-cgi.exe)
    <pg>/mariadb   MariaDB 10.11, Port 3308, Datadir db-data\\
    <pg>/moodle    Moodle 4.5 + format_tiles — DocumentRoot
    <pg>/data      moodledata (nie ueber den Webserver erreichbar)
    <pg>/apache    Apache 2.4 + mod_fcgid, Port 8090
    <pg>/_dl       Zips (Rebuild-Cache)
    <pg>/snapshots Zustaende (Stufe 2)

Zustaendigkeitsregel: Das Gate-Lab entscheidet ueber die .mbz, die Spielwiese
ueber Inhalt und Logik. Niemals andersherum — hier haengen eigene Plugins im
Baum, ein gruener Restore hier ist KEIN gruenes Gate.

Ziel:   Env MOODLE_SPIELWIESE_HOME  oder  C:\\moodle-playground
Exit:   0 ok · 2 fachlicher Fehler · 3 Umgebung kaputt/fehlt
Alle Unterkommandos verstehen --json.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime

# --- Feste Orte und Zahlen -------------------------------------------------

PG = os.environ.get("MOODLE_SPIELWIESE_HOME", r"C:\moodle-playground")
GATE_LAB = os.environ.get("MOODLE_GATE_LAB",
                          os.path.expanduser(r"~\.claude\moodle-lab"))
TESTINSTANZ = os.environ.get(
    "MOODLE_TESTINSTANZ_HOME",
    os.path.expanduser(r"~\.claude\skills\moodle-testinstanz"))

DB_PORT = 3308
WWW_PORT = 8090

DL = os.path.join(PG, "_dl")
WARTUNG = os.path.join(PG, ".wartung")  # Lock: snapshot/reset arbeiten am Datadir
PLUGINS_JSON = os.path.join(PG, "plugins.json")  # Registry eingehaengter Quellen
PHP_DIR = os.path.join(PG, "php")
MOODLE = os.path.join(PG, "moodle")
DATA = os.path.join(PG, "data")
DBDATA = os.path.join(PG, "db-data")
APACHE = os.path.join(PG, "apache")
SNAPSHOTS = os.path.join(PG, "snapshots")

PHP = os.path.join(PHP_DIR, "php.exe")
PHP_CGI = os.path.join(PHP_DIR, "php-cgi.exe")
MARIADBD = os.path.join(PG, "mariadb", "bin", "mariadbd.exe")
MARIADB_ADMIN = os.path.join(PG, "mariadb", "bin", "mariadb-admin.exe")
MARIADB_CLIENT = os.path.join(PG, "mariadb", "bin", "mariadb.exe")
HTTPD = os.path.join(APACHE, "bin", "httpd.exe")
HTTPD_CONF = os.path.join(APACHE, "conf", "httpd.conf")
HTTPD_PID = os.path.join(APACHE, "logs", "httpd.pid")

APACHE_URL = ("https://www.apachelounge.com/download/VS18/binaries/"
              "httpd-2.4.68-260617-Win64-VS18.zip")
FCGID_URL = ("https://www.apachelounge.com/download/VS18/modules/"
             "mod_fcgid-2.3.10-win64-VS18.zip")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")

PHP_EXTENSIONS = ["curl", "fileinfo", "gd", "intl", "mbstring", "exif",
                  "mysqli", "openssl", "soap", "sodium", "zip"]

DETACHED = 0x00000008 | 0x00000200 | 0x01000000  # DETACHED_PROCESS | NEW_PROCESS_GROUP | CREATE_BREAKAWAY_FROM_JOB

# Markierung des Blocks, den wir in config.php verwalten. Wird bei jedem
# setup-Lauf zwischen den Markern ersetzt statt angehaengt — sonst wuechse
# config.php bei jedem Lauf.
DEV_BEGIN = "// >>> spielwiese: Entwicklungs-Einstellungen (generiert)"
DEV_END = "// <<< spielwiese"


class Abbruch(Exception):
    """Fachlich (2) oder Umgebung (3) — der Exit-Code steckt mit drin."""

    def __init__(self, msg: str, code: int = 2):
        super().__init__(msg)
        self.code = code


# --- kleine Helfer ---------------------------------------------------------

_QUIET = False


def log(msg: str) -> None:
    if not _QUIET:
        print(f"[spielwiese] {msg}", flush=True)


def port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1.0):
            return True
    except OSError:
        return False


def warte_auf(bedingung, sekunden: float) -> bool:
    ende = time.monotonic() + sekunden
    while time.monotonic() < ende:
        if bedingung():
            return True
        time.sleep(0.5)
    return bedingung()


def run(cmd, cwd=None, timeout=1800, check=True) -> subprocess.CompletedProcess:
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
    except FileNotFoundError as e:  # fehlendes Binary sauber melden statt Traceback
        raise Abbruch(f"Programm nicht gefunden: {cmd[0]}", 3) from e
    except subprocess.TimeoutExpired as e:
        # Einheitlich fachlicher Fehler (2), kein Traceback — dieselbe
        # Klassifikation fuer seed, import, purge und upgrade.
        raise Abbruch(f"Zeitlimit ({timeout} s) ueberschritten: "
                      f"{os.path.basename(str(cmd[0]))}", 2) from e
    if check and r.returncode != 0:
        raise Abbruch(f"{os.path.basename(str(cmd[0]))} rc={r.returncode}\n"
                      f"{(r.stdout or '')[-1500:]}\n{(r.stderr or '')[-1500:]}")
    return r


def download(url: str, dest: str, mindest_bytes: int = 10_000) -> str:
    """Download mit unvergiftbarem Cache.

    Geladen wird nach <dest>.part und erst nach bestandener ZIP-Pruefung
    umbenannt; ein Cache-Treffer wird ebenfalls geprueft. Sonst hinterlaesst
    ein abgebrochener Download eine Partialdatei, die jeder weitere Lauf
    fuer einen gueltigen Cache haelt — die Idempotenz von setup waere dahin.
    """
    if os.path.exists(dest):
        if zipfile.is_zipfile(dest) and os.path.getsize(dest) >= mindest_bytes:
            log(f"Cache: {os.path.basename(dest)} vorhanden")
            return dest
        log(f"verwerfe unbrauchbaren Cache: {os.path.basename(dest)}")
        os.remove(dest)
    teilstueck = dest + ".part"
    log(f"lade {url}")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=300) as r, \
                open(teilstueck, "wb") as f:
            shutil.copyfileobj(r, f)
    except Exception as e:  # noqa: BLE001
        raise Abbruch(f"Download fehlgeschlagen ({url}): {e}", 3) from e
    if not zipfile.is_zipfile(teilstueck) or \
            os.path.getsize(teilstueck) < mindest_bytes:
        os.remove(teilstueck)
        raise Abbruch(f"{url} lieferte kein brauchbares ZIP (Hotlink-Schutz?)", 3)
    os.replace(teilstueck, dest)
    return dest


def entpacke(zip_path: str, ziel: str, strip: str | None = None,
             nur: str | None = None) -> None:
    """Zip entpacken.

    `strip` ist der Name des Wurzelordners im Zip, der wegfallen soll —
    ausdruecklich benannt, NICHT aus dem ersten Eintrag geraten. Das Apache-
    Lounge-Zip legt neben `Apache24/` noch eine Markierungsdatei
    (`-- Win64 VS18  --`) und eine ReadMe an, und die steht an erster Stelle;
    aus ihr einen Praefix abzuleiten schneidet nichts ab und schiebt den
    ganzen Baum eine Ebene zu tief. Eintraege ausserhalb von `strip` werden
    uebersprungen.

    `nur` entpackt ausschliesslich Dateien mit diesem Basisnamen.
    """
    log(f"entpacke {os.path.basename(zip_path)} -> {os.path.relpath(ziel, PG)}")
    praefix = f"{strip}/" if strip else ""
    geschrieben = 0
    with zipfile.ZipFile(zip_path) as z:
        for n in z.namelist():
            if n.endswith("/"):
                continue
            if nur and os.path.basename(n) != nur:
                continue
            if praefix:
                if not n.startswith(praefix):
                    continue
                rel = n[len(praefix):]
            else:
                rel = n
            if not rel:
                continue
            dest = os.path.join(ziel, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with z.open(n) as src, open(dest, "wb") as out:
                shutil.copyfileobj(src, out)
            geschrieben += 1
    if geschrieben == 0:
        raise Abbruch(f"{os.path.basename(zip_path)}: nichts entpackt "
                      f"(strip={strip!r}, nur={nur!r}) — Zip-Aufbau geaendert?", 3)


def pid_laeuft(pid: int, image: str | None = None) -> bool:
    """Lebt die PID — und gehoert sie (optional) zum erwarteten Programm?

    Ohne Imagenamen ist eine PID nach Windows-PID-Recycling wertlos: sie
    kann laengst einem voellig fremden Prozess gehoeren. Ueberall dort, wo
    an die Antwort ein Kill haengt, MUSS der Imagename mitgeprueft werden.
    """
    cmd = ["tasklist", "/FI", f"PID eq {pid}", "/NH"]
    if image:
        cmd[1:1] = ["/FI", f"IMAGENAME eq {image}"]
    r = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    return str(pid) in (r.stdout or "")


def apache_pid() -> int | None:
    """PID aus logs/httpd.pid — aber nur, wenn dahinter wirklich ein
    httpd.exe lebt.

    Nach einem Kill bleibt httpd.pid liegen; vergibt Windows die PID neu,
    zeigt die Datei auf einen fremden Prozess. Ohne Imagenamen-Pruefung
    wuerde stoppe_apache() den dann mit /T /F abschiessen — schlimmstenfalls
    das Gate-Lab-mariadbd.
    """
    try:
        with open(HTTPD_PID, encoding="utf-8") as f:
            pid = int(f.read().strip())
    except (OSError, ValueError):
        return None
    return pid if pid_laeuft(pid, "httpd.exe") else None


def mariadb_pid() -> int | None:
    """PID des mariadbd, das AUS DIESER Spielwiese laeuft.

    Ueber die Kommandozeile identifiziert, nicht ueber den Prozessnamen —
    im Gate-Lab laeuft moeglicherweise ein zweites mariadbd, das uns nichts
    angeht und das wir niemals anfassen duerfen.

    Ueber CIM statt wmic: wmic ist unter Windows 11 abgekuendigt und auf
    aktuellen Installationen nicht mehr verlaesslich vorhanden.

    Der Datadir wird aus der CommandLine GEPARST und pfadnormalisiert
    verglichen — kein Substring-Match. Substring scheitert an gemischten
    Pfadstilen (real beobachtet: `C:\\Users\\User/.claude/moodle-lab\\db-data`),
    und ein stiller Fehlgriff hier macht saemtliche DB-Guards blind.
    """
    ps = ("[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; "
          "Get-CimInstance Win32_Process -Filter \"Name='mariadbd.exe'\" | "
          "Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress")
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive",
                        "-Command", ps],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    roh = (r.stdout or "").strip()
    if not roh:
        return None
    try:
        treffer = json.loads(roh)
    except json.JSONDecodeError:
        return None
    if isinstance(treffer, dict):
        treffer = [treffer]
    mein = os.path.normcase(os.path.normpath(DBDATA))
    for t in treffer:
        m = re.search(r'--datadir=(?:"([^"]+)"|(\S+))',
                      t.get("CommandLine") or "")
        if not m:
            continue
        dd = os.path.normcase(os.path.normpath(m.group(1) or m.group(2)))
        if dd == mein:
            try:
                return int(t["ProcessId"])
            except (KeyError, TypeError, ValueError):
                continue
    return None


def instanz_da() -> bool:
    return os.path.exists(os.path.join(MOODLE, "config.php"))


def fordere_instanz() -> None:
    if not instanz_da():
        raise Abbruch(f"Keine Spielwiese unter {PG} — erst `spielwiese.py setup`", 3)


# --- setup -----------------------------------------------------------------

def zips_aus_gate_lab() -> list[str]:
    """Grosse Zips aus dem Gate-Lab spiegeln — spart ~210 MB Download."""
    paare = [("php.zip", "php.zip"), ("mariadb.zip", "mariadb.zip"),
             ("moodle.zip", "moodle.zip"), ("tiles45.zip", "format_tiles.zip")]
    os.makedirs(DL, exist_ok=True)
    kopiert = []
    for quelle, ziel in paare:
        q = os.path.join(GATE_LAB, quelle)
        z = os.path.join(DL, ziel)
        if os.path.exists(q) and not os.path.exists(z):
            if not zipfile.is_zipfile(q):
                log(f"ueberspringe {quelle}: kein gueltiges ZIP")
                continue
            teilstueck = z + ".part"  # nie eine halbe Kopie als Cache hinterlassen
            shutil.copy2(q, teilstueck)
            os.replace(teilstueck, z)
            kopiert.append(ziel)
    if kopiert:
        log(f"aus dem Gate-Lab gespiegelt: {', '.join(kopiert)}")
    return kopiert


def baue_moodle(force: bool) -> None:
    """setup_lab.py des Skills moodle-testinstanz WIEDERVERWENDEN."""
    setup_lab = os.path.join(TESTINSTANZ, "scripts", "setup_lab.py")
    if not os.path.exists(setup_lab):
        raise Abbruch(f"setup_lab.py nicht gefunden: {setup_lab}\n"
                      "Skill moodle-testinstanz fehlt oder "
                      "MOODLE_TESTINSTANZ_HOME zeigt falsch.", 3)
    env = dict(os.environ, MOODLE_LAB_HOME=PG)
    cmd = [sys.executable, setup_lab, "--port", str(DB_PORT),
           "--wwwport", str(WWW_PORT)]
    if force or instanz_da():
        cmd.append("--force")
    log(f"rufe setup_lab.py (Port {DB_PORT}, wwwroot :{WWW_PORT})")
    # Im --json-Modus ist der Vertrag EIN Objekt auf stdout — setup_lab darf
    # dann nicht durchschreiben; sein Ausgabeschwanz wandert nur im
    # Fehlerfall in die Meldung.
    r = subprocess.run(cmd, env=env, text=True, encoding="utf-8",
                       errors="replace", timeout=5400, capture_output=_QUIET)
    if r.returncode != 0:
        schwanz = ""
        if _QUIET:
            schwanz = "\n" + ((r.stdout or "")[-600:] + (r.stderr or "")[-600:])
        # Fehler der Werkzeugkette sind Umgebung (3), kein fachliches Urteil
        raise Abbruch(f"setup_lab.py rc={r.returncode}{schwanz}", 3)


def stelle_php_cgi_sicher() -> None:
    """php-cgi.exe ist fuer FastCGI zwingend; sie steckt im php.zip."""
    if os.path.exists(PHP_CGI):
        return
    php_zip = os.path.join(DL, "php.zip")
    if not os.path.exists(php_zip):
        raise Abbruch(f"php-cgi.exe fehlt und {php_zip} ist nicht da", 3)
    log("extrahiere php-cgi.exe aus php.zip nach")
    entpacke(php_zip, PHP_DIR, nur="php-cgi.exe")
    if not os.path.exists(PHP_CGI):
        raise Abbruch("php-cgi.exe war nicht im php.zip", 3)


def schreibe_php_ini() -> None:
    """php.ini fuer BEIDE Betriebsarten (CLI und FastCGI).

    Wichtig gegenueber der Lab-Fassung: extension_dir absolut. Relativ ("ext")
    loest PHP gegen das Arbeitsverzeichnis auf — bei einem von Apache
    gestarteten php-cgi.exe ist das nicht der PHP-Ordner, es wuerde also
    keine einzige Extension laden.
    """
    ext = "\n".join(f"extension={e}" for e in PHP_EXTENSIONS)
    inhalt = f"""; generiert von spielwiese.py — Spielwiese (CLI + FastCGI)
memory_limit = 512M
; muss zum FastCGI-Budget passen (FcgidBusyTimeout 900): PHP darf nicht
; frueher abbrechen als der Webserver, sonst sterben lange Web-Upgrades
; und grosse Restores an PHPs eigener Uhr statt an gar keiner
max_execution_time = 900
post_max_size = 256M
upload_max_filesize = 256M
max_input_vars = 5000
date.timezone = Europe/Berlin
; keine Versions-Werbung im X-Powered-By-Header
expose_php = Off

; absolut, NICHT relativ: php-cgi.exe startet mit Apaches Arbeitsverzeichnis
extension_dir = "{os.path.join(PHP_DIR, 'ext')}"
{ext}

; --- FastCGI ---
; ohne force_redirect=0 verweigert php-cgi.exe den Dienst
; ("Security Alert! The PHP CGI cannot be accessed directly.")
cgi.force_redirect = 0
; Moodle braucht PATH_INFO fuer /pluginfile.php/... (slasharguments)
cgi.fix_pathinfo = 1
cgi.rfc2616_headers = 0
fastcgi.impersonate = 0

; --- opcache ---
; Mit validate_timestamps=1 + revalidate_freq=0 prueft PHP bei JEDEM Request
; die mtime der Quelldateien: Aenderungen an (per Junction eingehaengten)
; Plugin-Quellen wirken sofort, veralteter Bytecode ist ausgeschlossen.
; Nur das Neu-KOMPILIEREN entfaellt. Die frueher hier dokumentierte
; "kein opcache"-Regel galt dem Stale-Bytecode-Risiko — das ist mit
; dieser Validierung vom Tisch.
zend_extension=opcache
opcache.enable=1
opcache.enable_cli=0
opcache.memory_consumption=192
opcache.max_accelerated_files=16229
opcache.validate_timestamps=1
opcache.revalidate_freq=0
"""
    with open(os.path.join(PHP_DIR, "php.ini"), "w", encoding="utf-8") as f:
        f.write(inhalt)
    log("php.ini geschrieben (extension_dir absolut, CGI-Schalter gesetzt)")


def installiere_apache() -> None:
    os.makedirs(DL, exist_ok=True)
    if not os.path.exists(HTTPD):
        entpacke(download(APACHE_URL, os.path.join(DL, os.path.basename(APACHE_URL)),
                          1_000_000),
                 APACHE, strip="Apache24")
        if not os.path.exists(HTTPD):
            raise Abbruch(f"httpd.exe fehlt nach dem Entpacken: {HTTPD}", 3)
    modul = os.path.join(APACHE, "modules", "mod_fcgid.so")
    if not os.path.exists(modul):
        entpacke(download(FCGID_URL, os.path.join(DL, os.path.basename(FCGID_URL)),
                          10_000),
                 os.path.join(APACHE, "modules"), nur="mod_fcgid.so")
    if not os.path.exists(modul):
        raise Abbruch("mod_fcgid.so wurde nicht installiert", 3)
    os.makedirs(os.path.join(APACHE, "logs"), exist_ok=True)


def schreibe_httpd_conf() -> None:
    p = lambda pfad: pfad.replace("\\", "/")  # noqa: E731 — Apache will /
    conf = f"""# generiert von spielwiese.py — NICHT von Hand aendern,
# jeder setup-Lauf ueberschreibt diese Datei.
ServerRoot "{p(APACHE)}"
# BEIDE Loopback-Familien. Windows loest `localhost` zuerst auf ::1 auf;
# lauscht hier nur 127.0.0.1, zahlt JEDER Request (und jeder Redirect-Hop)
# ~2 s IPv6-Fallback — gemessen: statische Datei 2046 ms via localhost,
# 0 ms via 127.0.0.1. `Require local` deckt ::1 mit ab.
Listen 127.0.0.1:{WWW_PORT}
Listen [::1]:{WWW_PORT}
ServerName localhost:{WWW_PORT}
PidFile "logs/httpd.pid"

# Keine Versions-Werbung an lokale Mitleser
ServerTokens Prod
ServerSignature Off

# Nur, was tatsaechlich gebraucht wird. authz_host liefert "Require local";
# mpm_winnt ist im Apache-Lounge-Build statisch einkompiliert.
LoadModule authz_core_module modules/mod_authz_core.so
LoadModule authz_host_module modules/mod_authz_host.so
LoadModule dir_module modules/mod_dir.so
LoadModule mime_module modules/mod_mime.so
LoadModule log_config_module modules/mod_log_config.so
LoadModule fcgid_module modules/mod_fcgid.so

DocumentRoot "{p(MOODLE)}"
DirectoryIndex index.php index.html
TypesConfig conf/mime.types

# Standard: nichts freigeben. Nur der Moodle-Baum unten wird geoeffnet.
<Directory />
    AllowOverride none
    Require all denied
</Directory>

<Directory "{p(MOODLE)}">
    Options FollowSymLinks ExecCGI
    AllowOverride None
    # Spielwiese: nur vom eigenen Rechner. Testschueler-Konten mit
    # bekannten Passwoertern haben im Netz nichts verloren.
    Require local
</Directory>

# moodledata liegt ausserhalb des DocumentRoot und ist damit ohnehin
# unerreichbar; die Regel steht als zweite Sicherung trotzdem hier.
<Directory "{p(DATA)}">
    Require all denied
</Directory>

<FilesMatch "^\\.ht">
    Require all denied
</FilesMatch>

# Entwickler-/Metadateien nicht statisch ausliefern: composer.json & Co.
# verraten Build-Version und DB-Schema an jeden lokalen Mitleser.
# Browser-relevante Statik (js/css/Bilder/Fonts) ist nicht betroffen.
<FilesMatch "(?i)(^(composer\\.(json|lock)|package\\.json|environment\\.xml|install\\.xml)$|\\.(dist|md|txt|lock|sql|bak|orig|rej)$)">
    Require all denied
</FilesMatch>

ErrorLog "logs/error.log"
LogLevel warn
LogFormat "%h %l %u %t \\"%r\\" %>s %b" common
CustomLog "logs/access.log" common

# --- PHP ueber mod_fcgid ---
AcceptPathInfo On
FcgidInitialEnv PHPRC "{p(PHP_DIR)}"
# 0 = PHP beendet sich NIE selbst. Stuende hier derselbe Wert wie in
# FcgidMaxRequestsPerProcess, beendet sich php-cgi am selben Zaehlerstand,
# an dem mod_fcgid den Prozess noch verwenden will — die klassische
# sporadische "read data timeout"-500er-Race. Recycling macht allein mod_fcgid.
FcgidInitialEnv PHP_FCGI_MAX_REQUESTS 0
FcgidMaxRequestsPerProcess 1000
FcgidMaxProcesses 8
# 2 warme Prozesse statt 0: der erste Klick nach einer Pause soll nicht
# Prozessstart + kalten opcache bezahlen.
FcgidMinProcessesPerClass 2
# Moodles Erstinstallation und grosse Restores laufen lange — die
# Vorgabe von 40 s wuerde mitten im Upgrade abbrechen.
FcgidIOTimeout 900
FcgidBusyTimeout 900
FcgidConnectTimeout 60
# 16 MiB Marge ueber post_max_size (256M): der multipart-Overhead darf nicht
# dazu fuehren, dass mod_fcgid vor PHP mit einem nackten 500 abbricht —
# PHP soll die saubere "Datei zu gross"-Meldung liefern.
FcgidMaxRequestLen 285212672
FcgidWrapper "{p(PHP_CGI)}" .php
AddHandler fcgid-script .php
"""
    os.makedirs(os.path.dirname(HTTPD_CONF), exist_ok=True)
    with open(HTTPD_CONF, "w", encoding="utf-8") as f:
        f.write(conf)
    r = run([HTTPD, "-t", "-f", HTTPD_CONF], check=False)
    ausgabe = (r.stdout or "") + (r.stderr or "")
    if "Syntax OK" not in ausgabe:
        raise Abbruch(f"httpd.conf wird von Apache nicht akzeptiert:\n{ausgabe}", 2)
    log("httpd.conf geschrieben — Apache meldet: Syntax OK")


def schreibe_dev_einstellungen(entwickler: bool = False) -> None:
    """Dev-Block in config.php pflegen — VOR dem require von lib/setup.php.

    Nach dem require gesetzte Werte wirken nicht mehr; deshalb wird der Block
    eingefuegt und nicht angehaengt.

    Zwei Debug-Modi (`spielwiese.py debug …`):
    - schnell (Default):  DEBUG_NORMAL — Fehler/Warnungen/Notices sichtbar,
      Seiten in ~0,1 s. Gemessen: DEVELOPER kostet ~1 s PRO SEITE, weil
      Moodle dann Plugin- und Klassenkarten bei jedem Request neu validiert
      (hunderte Verzeichnis-Stats) — mit keinem Cache wegzubekommen.
    - entwickler:         E_ALL + volle Backtraces, fuer die Fehlerjagd.
    """
    cfg = os.path.join(MOODLE, "config.php")
    if not os.path.exists(cfg):
        raise Abbruch(f"config.php fehlt: {cfg}", 3)
    with open(cfg, encoding="utf-8") as f:
        text = f.read()

    if DEV_BEGIN in text:  # alten Block herausschneiden
        vor, _, rest = text.partition(DEV_BEGIN)
        _, _, nach = rest.partition(DEV_END)
        text = vor + nach.lstrip("\n")

    if entwickler:
        debug_zeilen = (
            "// Modus ENTWICKLER: volle Backtraces, ~1 s je Seite (Moodle\n"
            "// validiert saemtliche Plugin-/Klassenkarten pro Request).\n"
            "// Zurueck mit: spielwiese.py debug schnell\n"
            "$CFG->debug = (E_ALL | E_STRICT);")
    else:
        debug_zeilen = (
            "// Modus SCHNELL (DEBUG_NORMAL): Fehler, Warnungen und Notices\n"
            "// samt Meldungsseite bleiben sichtbar; nur die teure\n"
            "// DEVELOPER-Revalidierung entfaellt (~1 s je Seite).\n"
            "// Volle Backtraces: spielwiese.py debug entwickler\n"
            "$CFG->debug = (E_ERROR | E_PARSE | E_WARNING | E_NOTICE);")

    block = f"""{DEV_BEGIN}
{debug_zeilen}
$CFG->debugdisplay = 1;
// Caches AN: die Spielwiese soll sich fluessig anfuehlen. Nach Aenderungen
// an JS- oder Sprachdateien eines Plugins: `spielwiese.py purge`.
// Wer tief an Core-JS arbeitet, stellt cachejs voruebergehend auf false.
$CFG->cachejs = true;
$CFG->langstringcache = true;
$CFG->noemailever = true;         // Spielwiese schickt NIE Mails nach draussen

// Themedesigner-Modus: nur einschalten, wenn du an einem Theme arbeitest.
// Er deaktiviert saemtliches CSS/JS-Caching und macht Moodle spuerbar zaeh.
$CFG->themedesignermode = false;
{DEV_END}

"""
    marker = "require_once(__DIR__ . '/lib/setup.php');"
    if marker not in text:
        raise Abbruch("In config.php fehlt das require von lib/setup.php — "
                      "die Datei sieht nicht aus wie erwartet.", 2)
    text = text.replace(marker, block + marker, 1)
    with open(cfg, "w", encoding="utf-8") as f:
        f.write(text)
    log(f"Dev-Einstellungen gesetzt (Debug-Modus: "
        f"{'entwickler' if entwickler else 'schnell'})")


def cmd_debug(args) -> tuple[int, dict]:
    fordere_instanz()
    cfg = os.path.join(MOODLE, "config.php")
    with open(cfg, encoding="utf-8") as f:
        text = f.read()
    aktuell = "entwickler" if "E_ALL | E_STRICT" in text.partition(DEV_BEGIN)[2] \
        else "schnell"
    if not args.modus:
        log(f"Debug-Modus: {aktuell}")
        return 0, {"status": "ok", "modus": aktuell}
    schreibe_dev_einstellungen(entwickler=(args.modus == "entwickler"))
    log(f"Debug-Modus: {aktuell} -> {args.modus} (wirkt ab dem naechsten "
        "Request, kein Neustart noetig)")
    return 0, {"status": "ok", "modus": args.modus, "vorher": aktuell}


PHP_SPRACHE = """<?php
// generiert von spielwiese.py — deutsches Sprachpaket + Standardsprache
define('CLI_SCRIPT', 1);
require('@KONFIG@');

$rc = ['installiert' => 0, 'standard' => null];
if (!array_key_exists('de', get_string_manager()->get_list_of_translations())) {
    $controller = new \\tool_langimport\\controller();
    $rc['installiert'] = $controller->install_languagepacks('de');
    get_string_manager()->reset_caches();
}
if (get_config('core', 'lang') !== 'de') {
    set_config('lang', 'de');
}
$DB->execute("UPDATE {user} SET lang = 'de' WHERE deleted = 0");
$rc['standard'] = get_config('core', 'lang');
echo '@@', json_encode($rc), '@@';
"""


def installiere_sprachpaket_de() -> None:
    """Deutsches Sprachpaket + Standardsprache de (best effort).

    Braucht Netz (download.moodle.org). Scheitert der Download, bleibt die
    Instanz auf Englisch lauffaehig — deshalb Warnung statt Abbruch: das
    Offline-Setup aus dem Zip-Cache darf daran nicht sterben.
    """
    skript = os.path.join(PG, "_sprache.php")
    with open(skript, "w", encoding="utf-8") as f:
        f.write(PHP_SPRACHE.replace(
            "@KONFIG@", _php_pfad(os.path.join(MOODLE, "config.php"))))
    try:
        rc = _php_marker(skript, timeout=600)
        log(f"Sprache: de (Pakete neu installiert: {rc['installiert']})")
    except Abbruch as e:
        log(f"WARNUNG: deutsches Sprachpaket nicht installierbar ({e}) — "
            "Instanz laeuft auf Englisch weiter")


def schreibe_starter() -> None:
    ich = os.path.abspath(__file__)
    start_cmd = os.path.join(PG, "start.cmd")
    with open(start_cmd, "w", encoding="utf-8") as f:
        f.write("@echo off\r\n"
                "rem generiert von spielwiese.py\r\n"
                f'"{sys.executable}" "{ich}" start\r\n'
                "if errorlevel 1 (echo. & echo Start fehlgeschlagen. & pause & exit /b 1)\r\n"
                f"start \"\" http://localhost:{WWW_PORT}\r\n")
    with open(os.path.join(PG, "stop.cmd"), "w", encoding="utf-8") as f:
        f.write("@echo off\r\n"
                "rem generiert von spielwiese.py\r\n"
                f'"{sys.executable}" "{ich}" stop\r\n')

    ps = (
        "$w = New-Object -ComObject WScript.Shell;"
        "$d = [Environment]::GetFolderPath('Desktop');"
        "$l = $w.CreateShortcut((Join-Path $d 'Moodle Spielwiese.lnk'));"
        f"$l.TargetPath = '{start_cmd}';"
        f"$l.WorkingDirectory = '{PG}';"
        "$l.WindowStyle = 7;"
        "$l.Description = 'Moodle-Spielwiese starten (localhost:%d)';"
        "$l.Save(); Write-Output $l.FullName" % WWW_PORT
    )
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive",
                        "-Command", ps], capture_output=True, text=True,
                       errors="replace")
    if r.returncode == 0:
        log(f"Desktop-Verknuepfung: {(r.stdout or '').strip()}")
    else:
        log("Desktop-Verknuepfung konnte nicht angelegt werden (unkritisch)")


def cmd_setup(args) -> tuple[int, dict]:
    os.makedirs(PG, exist_ok=True)
    os.makedirs(SNAPSHOTS, exist_ok=True)
    if instanz_da() and not args.force:
        log("Instanz existiert — repariere/aktualisiere (idempotent)")
    zips_aus_gate_lab()
    baue_moodle(args.force)
    stelle_php_cgi_sicher()
    schreibe_php_ini()
    installiere_apache()
    schreibe_httpd_conf()
    schreibe_dev_einstellungen()
    installiere_sprachpaket_de()
    schreibe_starter()
    log("FERTIG. Naechster Schritt: spielwiese.py start")
    return 0, {"status": "ok", "spielwiese": PG,
               "db_port": DB_PORT, "www_port": WWW_PORT}


# --- start / stop / status -------------------------------------------------

def starte_mariadb() -> None:
    if port_open(DB_PORT):
        log(f"MariaDB laeuft bereits auf {DB_PORT}")
        return
    log(f"starte MariaDB auf Port {DB_PORT}")
    with open(os.path.join(PG, "mariadbd.log"), "ab") as lf:
        subprocess.Popen([MARIADBD, f"--datadir={DBDATA}",
                          f"--port={DB_PORT}", "--console",
                          # Wegwerf-Instanz: kein fsync je Commit (Absturz
                          # kostet schlimmstenfalls ~1 s Transaktionen —
                          # die Absicherung heisst hier `reset`), und ein
                          # Buffer-Pool, der Kurse im Speicher haelt.
                          # Beschleunigt vor allem Importe/Restores.
                          "--innodb-flush-log-at-trx-commit=2",
                          "--innodb-buffer-pool-size=512M"],
                         stdout=lf, stderr=lf, creationflags=DETACHED)
    if not warte_auf(lambda: port_open(DB_PORT), 60):
        raise Abbruch(f"MariaDB kommt nicht hoch — siehe {PG}\\mariadbd.log", 3)


def starte_apache() -> None:
    if port_open(WWW_PORT):
        log(f"Apache laeuft bereits auf {WWW_PORT}")
        return
    log(f"starte Apache auf Port {WWW_PORT}")
    subprocess.Popen([HTTPD, "-f", HTTPD_CONF], creationflags=DETACHED,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not warte_auf(lambda: port_open(WWW_PORT), 30):
        fehler = os.path.join(APACHE, "logs", "error.log")
        schwanz = ""
        if os.path.exists(fehler):
            with open(fehler, encoding="utf-8", errors="replace") as f:
                schwanz = "".join(f.readlines()[-15:])
        raise Abbruch(f"Apache kommt nicht hoch:\n{schwanz}", 3)


def cmd_start(args) -> tuple[int, dict]:
    fordere_instanz()
    fordere_keine_wartung()
    for t in ("db-data", "data"):
        if os.path.exists(os.path.join(PG, t + ".vor-reset")):
            raise Abbruch(f"{t}.vor-reset existiert — Truemmer eines "
                          "abgebrochenen Resets, womoeglich der letzte gute "
                          "Zustand. Kein Start auf ungeklaertem Datadir.", 2)
    starte_mariadb()
    starte_apache()
    log(f"Spielwiese laeuft: http://localhost:{WWW_PORT}  (admin / Admin123!)")
    return 0, {"status": "ok", "url": f"http://localhost:{WWW_PORT}",
               "mariadb_port": DB_PORT, "apache_port": WWW_PORT}


def stoppe_apache() -> bool:
    pid = apache_pid()
    if pid is None:
        if port_open(WWW_PORT):
            raise Abbruch(f"Port {WWW_PORT} ist belegt, aber logs/httpd.pid "
                          "nennt keinen lebenden httpd.exe — das ist nicht "
                          "unser Apache und wird nicht angefasst.", 2)
        try:  # liegengebliebene PID-Datei eines frueheren Laufs aufraeumen
            os.remove(HTTPD_PID)
        except OSError:
            pass
        return False
    log(f"stoppe Apache (PID {pid})")
    r = subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                       capture_output=True, text=True, errors="replace")
    tot = warte_auf(lambda: not pid_laeuft(pid, "httpd.exe"), 15)
    if not tot or port_open(WWW_PORT):
        raise Abbruch(f"Apache (PID {pid}) laesst sich nicht stoppen "
                      f"(taskkill rc={r.returncode}) — kein stiller Erfolg.", 2)
    try:  # sonst zeigt die PID-Datei nach Windows-Recycling auf Fremde
        os.remove(HTTPD_PID)
    except OSError:
        pass
    return True


def stoppe_mariadb() -> bool:
    """Sauber herunterfahren, nicht abschiessen.

    Ein abgeschossenes mariadbd hinterlaesst einen halb geschriebenen
    InnoDB-Zustand. Stufe 2 (Snapshots) haengt daran, dass hier wirklich
    sauber beendet wird — deshalb schon jetzt ueber mariadb-admin.
    """
    if not port_open(DB_PORT) and mariadb_pid() is None:
        return False
    pid = mariadb_pid()
    log(f"stoppe MariaDB (PID {pid})")
    run([MARIADB_ADMIN, f"--port={DB_PORT}", "-h", "127.0.0.1", "-u", "root",
         "-proot", "shutdown"], check=False, timeout=120)
    if not warte_auf(lambda: not port_open(DB_PORT), 60):
        raise Abbruch("MariaDB laesst sich nicht sauber stoppen — "
                      "NICHT abschiessen, sonst ist der Datadir inkonsistent.", 2)
    if pid is not None and not warte_auf(lambda: not pid_laeuft(pid), 30):
        raise Abbruch(f"Port {DB_PORT} ist zu, Prozess {pid} lebt aber noch.", 2)
    return True


def cmd_stop(args) -> tuple[int, dict]:
    a = stoppe_apache()
    m = stoppe_mariadb()
    if not (a or m):
        log("nichts zu stoppen — Spielwiese lief nicht")
    return 0, {"status": "ok", "apache_gestoppt": a, "mariadb_gestoppt": m}


def http_probe() -> dict:
    url = f"http://localhost:{WWW_PORT}/login/index.php"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "spielwiese/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            code = r.getcode()
            body = r.read(200_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return {"url": url, "code": e.code, "login_formular": False}
    except Exception as e:  # noqa: BLE001
        return {"url": url, "code": None, "login_formular": False,
                "fehler": str(e)}
    formular = 'name="username"' in body and 'name="password"' in body
    return {"url": url, "code": code, "login_formular": formular}


def moodle_version() -> str | None:
    """$CFG->release, oder None wenn Moodle gerade nicht antwortet.

    Waehrend einer laufenden Erstinstallation bzw. eines Upgrades wirft
    Moodle hier eine Exception ("Site is being upgraded"). Das ist ein
    voruebergehender Zustand und kein Versionsstring — dann lieber None,
    als einen Stacktrace als Version auszuweisen.
    """
    if not os.path.exists(PHP) or not instanz_da():
        return None
    r = run([PHP, "-r", "define('CLI_SCRIPT',1);require 'config.php';"
             "echo $CFG->release;"], cwd=MOODLE, check=False, timeout=120)
    ausgabe = (r.stdout or "").strip()
    if r.returncode != 0 or not ausgabe or "\n" in ausgabe or len(ausgabe) > 80:
        return None
    return ausgabe


def cmd_status(args) -> tuple[int, dict]:
    apid, mpid = apache_pid(), mariadb_pid()
    zustand = {
        "spielwiese": PG,
        "instanz_vorhanden": instanz_da(),
        "mariadb": {"port": DB_PORT, "laeuft": port_open(DB_PORT), "pid": mpid},
        "apache": {"port": WWW_PORT, "laeuft": port_open(WWW_PORT), "pid": apid},
    }
    if zustand["apache"]["laeuft"]:
        zustand["http"] = http_probe()
    if zustand["mariadb"]["laeuft"]:
        zustand["moodle_version"] = moodle_version()

    # "up" heisst: UNSERE Prozesse (PIDs verifiziert) UND Moodle antwortet
    # mit einem Login-Formular. Zwei offene TCP-Ports allein koennen auch
    # zwei fremde Prozesse sein — das waere ein gelogenes Exit 0.
    db_ok = zustand["mariadb"]["laeuft"] and mpid is not None
    web_ok = (zustand["apache"]["laeuft"] and apid is not None
              and zustand.get("http", {}).get("login_formular", False))
    beide = db_ok and web_ok
    irgendwas = zustand["mariadb"]["laeuft"] or zustand["apache"]["laeuft"]
    zustand["status"] = "up" if beide else ("partial" if irgendwas else "down")

    if not _QUIET:
        log(f"Spielwiese: {PG}")
        log(f"  MariaDB  :{DB_PORT}  {'laeuft' if zustand['mariadb']['laeuft'] else 'aus'}"
            f"{f' (PID {mpid})' if mpid else ''}")
        log(f"  Apache   :{WWW_PORT}  {'laeuft' if zustand['apache']['laeuft'] else 'aus'}"
            f"{f' (PID {apid})' if apid else ''}")
        if "http" in zustand:
            h = zustand["http"]
            log(f"  HTTP     {h['code']} · Login-Formular: "
                f"{'ja' if h['login_formular'] else 'nein'}")
        if zustand.get("moodle_version"):
            log(f"  Moodle   {zustand['moodle_version']}")
    return (0 if beide else 3), zustand


# --- Stufe 2: Snapshots und Reset ------------------------------------------
#
# Ein Snapshot ist die Kopie von db-data + data bei NACHWEISLICH gestoppten
# Diensten. Er umfasst absichtlich NICHT den moodle/-Baum: eingehaengte
# Plugin-Quellen ueberleben jeden Reset, und ein Reset auf einen Snapshot,
# der ein Plugin noch nicht kannte, testet dessen Erstinstallation gratis mit.

def _setze_wartung(zweck: str) -> None:
    with open(WARTUNG, "w", encoding="utf-8") as f:
        json.dump({"pid": os.getpid(), "zweck": zweck,
                   "seit": datetime.now().isoformat(timespec="seconds")}, f)


def _loese_wartung() -> None:
    try:
        os.remove(WARTUNG)
    except OSError:
        pass


def fordere_keine_wartung() -> None:
    """Blockt start (und weitere snapshot/reset), waehrend am Datadir
    kopiert wird.

    Der Desktop-Starter ist der Nebeneingang fuer den Menschen — ohne diese
    Sperre koennte er die DB hochfahren, WAEHREND db-data kopiert wird, und
    der Snapshot froere einen heissen InnoDB-Zustand ein. Ein Lock, dessen
    Besitzer-PID nicht mehr lebt, ist verwaist und wird still entfernt.
    """
    if not os.path.exists(WARTUNG):
        return
    try:
        # utf-8-sig: auch ein von Hand (PowerShell, mit BOM) geschriebenes
        # Lock muss lesbar sein
        with open(WARTUNG, encoding="utf-8-sig") as f:
            info = json.load(f)
    except (OSError, ValueError) as e:
        # Unlesbar heisst NICHT verwaist. Ein Guard, der bei Unlesbarkeit
        # oeffnet statt schliesst, ist falsch herum — fail-closed.
        raise Abbruch(f"Wartungs-Lock {WARTUNG} ist unlesbar ({e}) — wenn "
                      "sicher kein Snapshot/Reset laeuft, die Datei von Hand "
                      "loeschen.", 2) from e
    pid = info.get("pid")
    if isinstance(pid, int) and pid_laeuft(pid):
        raise Abbruch(f"Snapshot/Reset laeuft gerade ({info.get('zweck', '?')} "
                      f"seit {info.get('seit', '?')}, PID {pid}) — kein Start, "
                      "solange am Datadir kopiert wird.", 2)
    log("verwaistes Wartungs-Lock entfernt")
    _loese_wartung()


def loesche_baum(pfad: str, still: bool = False) -> None:
    """rmtree, das Windows-Schreibschutz uebersteht.

    Moodle legt z. B. data\\secret\\key\\sodium.key schreibgeschuetzt an;
    ein nacktes shutil.rmtree bricht daran mit PermissionError ab. Der
    Handler nimmt den Schreibschutz und versucht es erneut.
    """
    def _entschuetzen(func, p, _exc):
        os.chmod(p, stat.S_IWRITE)
        func(p)

    try:
        shutil.rmtree(pfad, onerror=_entschuetzen)
    except OSError:
        if not still:
            raise


def _gueltiger_name(name: str) -> str:
    if not name or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", name):
        raise Abbruch(f"Unbrauchbarer Snapshot-Name: {name!r} — erlaubt sind "
                      "Buchstaben, Ziffern, Punkt, Bindestrich, Unterstrich "
                      "(Beginn alphanumerisch, max. 64 Zeichen).", 2)
    return name


def fordere_kein_fremder_mariadbd(zweck: str) -> None:
    """Ein mariadbd auf unserem Datadir, der NICHT auf unserem Port lauscht,
    ist ein fremder Prozess (z. B. von Hand gestartet). Stoppen wuerden wir
    ihn ueber Port 3308 nie erreichen — also gar nicht erst anfangen."""
    pid = mariadb_pid()
    if pid is not None and not port_open(DB_PORT):
        raise Abbruch(f"Ein mariadbd (PID {pid}) arbeitet auf unserem Datadir, "
                      f"lauscht aber nicht auf {DB_PORT} — fremder Prozess, "
                      f"{zweck} verweigert.", 2)


def fordere_tote_dienste() -> None:
    """Letzte Verteidigungslinie vor jedem Kopieren/Tauschen von db-data.

    Lieber Abbruch als ein Snapshot, der einen halb geschriebenen
    InnoDB-Zustand einfriert und erst beim Zurueckspielen als kaputt auffaellt.
    """
    pid = mariadb_pid()
    if port_open(DB_PORT) or pid is not None:
        raise Abbruch(f"mariadbd arbeitet noch auf dem Datadir (PID {pid}) — "
                      "kein Snapshot/Reset bei laufender DB.", 2)
    if port_open(WWW_PORT) or apache_pid() is not None:
        raise Abbruch("Apache laeuft noch — er schreibt Sessions nach data\\.", 2)


def zaehle_inhalte() -> dict:
    """Kurse (ohne Startseite), aktive Nutzer, installierte Plugins."""
    sql = ("SELECT (SELECT COUNT(*) FROM mdl_course WHERE id>1), "
           "(SELECT COUNT(*) FROM mdl_user WHERE deleted=0), "
           "(SELECT COUNT(*) FROM mdl_config_plugins WHERE name='version')")
    r = run([MARIADB_CLIENT, f"--port={DB_PORT}", "-h", "127.0.0.1",
             "-u", "root", "-proot", "moodle", "-N", "-B", "-e", sql])
    teile = (r.stdout or "").split()
    if len(teile) != 3:
        raise Abbruch(f"Zaehlabfrage lieferte Unerwartetes: {r.stdout!r}", 2)
    return {"kurse": int(teile[0]), "nutzer": int(teile[1]),
            "plugins": int(teile[2])}


def verzeichnis_masse(pfad: str) -> tuple[int, int]:
    dateien, gesamt = 0, 0
    for wurzel, _dirs, files in os.walk(pfad):
        for f in files:
            dateien += 1
            try:
                gesamt += os.path.getsize(os.path.join(wurzel, f))
            except OSError:
                pass
    return dateien, gesamt


def _schreibe_snapshot(name: str, zaehlung: dict, version: str | None) -> dict:
    """Kopiert db-data + data nach snapshots\\<name>. Setzt gestoppte,
    verifizierte Dienste voraus (fordere_tote_dienste() ist gelaufen).

    Erst in ein _unfertig_-Verzeichnis, dann umbenennen: ein halb kopierter
    Snapshot sieht dadurch nie wie ein gueltiger aus.
    """
    ziel = os.path.join(SNAPSHOTS, name)
    tmp = os.path.join(SNAPSHOTS, f"_unfertig_{name}")
    if os.path.exists(tmp):  # Truemmer eines frueheren Abbruchs — nie gueltig gewesen
        loesche_baum(tmp)
    log(f"kopiere db-data + data -> snapshots\\{name}")
    try:
        for teil in ("db-data", "data"):
            shutil.copytree(os.path.join(PG, teil), os.path.join(tmp, teil))
        if not os.path.exists(os.path.join(tmp, "db-data", "mysql")):
            raise Abbruch("Kopie unvollstaendig: db-data\\mysql fehlt.", 2)
        dateien, groesse = verzeichnis_masse(tmp)
        meta = {"erstellt": datetime.now().isoformat(timespec="seconds"),
                "moodle_version": version, **zaehlung,
                "dateien": dateien, "mb": round(groesse / 1_048_576, 1)}
        with open(os.path.join(tmp, "meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=1)
        os.rename(tmp, ziel)
    except BaseException:
        loesche_baum(tmp, still=True)
        raise
    return meta


def _spiele_zurueck(quelle: str) -> None:
    """Tauscht db-data + data gegen die Snapshot-Kopien — mit Rollback.

    Beide Verzeichnisse werden ERST beiseitegestellt, DANN kopiert. Schlaegt
    irgendetwas fehl — auch schon das Beiseitestellen selbst —, kommt der
    vorherige Zustand vollstaendig zurueck: nie ein Mischmasch aus altem
    data und neuem db-data. Die .vor-reset-Sicherungen raeumt der AUFRUFER
    nach dem Neustart der Dienste weg; inhaltlich ist der Reset hier durch.

    Scheitert der Rollback selbst (gesperrte Datei), wird das ausdruecklich
    gemeldet — die Originale liegen dann unter *.vor-reset, und cmd_start
    verweigert den Start auf dem ungeklaerten Datadir.
    """
    teile = ("db-data", "data")
    log("spiele Snapshot zurueck (db-data + data)")
    beiseite: list[str] = []
    try:
        for t in teile:
            os.rename(os.path.join(PG, t), os.path.join(PG, t + ".vor-reset"))
            beiseite.append(t)
        for t in teile:
            shutil.copytree(os.path.join(quelle, t), os.path.join(PG, t))
    except BaseException as e:
        log("Reset fehlgeschlagen — stelle vorherigen Zustand wieder her")
        misslungen = []
        for t in beiseite:
            ziel = os.path.join(PG, t)
            kaputt = ziel + ".kaputt"
            try:
                if os.path.exists(ziel):
                    # Wegbenennen statt loeschen: billiger, und scheitert
                    # seltener an Virenscanner-Locks auf frischen Dateien.
                    loesche_baum(kaputt, still=True)
                    os.rename(ziel, kaputt)
                os.rename(ziel + ".vor-reset", ziel)
                loesche_baum(kaputt, still=True)
            except OSError:
                misslungen.append(t)
        if misslungen:
            raise Abbruch(
                f"Rollback unvollstaendig fuer: {', '.join(misslungen)} — die "
                f"Originale liegen unter *.vor-reset in {PG}. NICHT starten, "
                "erst von Hand zurueckbenennen.", 2) from e
        raise


def cmd_snapshot(args) -> tuple[int, dict]:
    fordere_instanz()
    os.makedirs(SNAPSHOTS, exist_ok=True)

    if args.liste:
        if args.name:
            raise Abbruch("Entweder ein Name ODER --list, nicht beides.", 2)
        eintraege = []
        for d in sorted(os.listdir(SNAPSHOTS)):
            voll = os.path.join(SNAPSHOTS, d)
            if not os.path.isdir(voll) or d.startswith("_unfertig_"):
                continue
            meta = {}
            meta_pfad = os.path.join(voll, "meta.json")
            if os.path.exists(meta_pfad):
                with open(meta_pfad, encoding="utf-8") as f:
                    meta = json.load(f)
            eintraege.append({"name": d, **meta})
        if not eintraege:
            log("keine Snapshots vorhanden")
        for e in eintraege:
            log(f"  {e['name']:<18} {e.get('erstellt', '?'):<20} "
                f"Kurse={e.get('kurse', '?')} Nutzer={e.get('nutzer', '?')} "
                f"Plugins={e.get('plugins', '?')} · {e.get('mb', '?')} MB")
        return 0, {"status": "ok", "snapshots": eintraege}

    if not args.name:
        raise Abbruch("snapshot braucht einen Namen (oder --list).", 2)
    name = _gueltiger_name(args.name)
    if os.path.exists(os.path.join(SNAPSHOTS, name)):
        raise Abbruch(f"Snapshot '{name}' existiert schon — anderen Namen "
                      "waehlen oder den alten vorher loeschen.", 2)
    fordere_keine_wartung()
    fordere_kein_fremder_mariadbd("Snapshot")

    war_db = port_open(DB_PORT)
    war_apache = port_open(WWW_PORT)
    if not war_db:
        starte_mariadb()  # nur fuer die Zaehlung; danach wird ohnehin gestoppt
    zaehlung = zaehle_inhalte()
    version = moodle_version()

    _setze_wartung(f"snapshot {name}")
    try:
        stoppe_apache()
        stoppe_mariadb()
        fordere_tote_dienste()
        meta = _schreibe_snapshot(name, zaehlung, version)
        if war_db:
            starte_mariadb()
        if war_apache:
            starte_apache()
    finally:
        _loese_wartung()
    log(f"Snapshot '{name}': {zaehlung['kurse']} Kurse, "
        f"{zaehlung['nutzer']} Nutzer, {zaehlung['plugins']} Plugins, "
        f"{meta['mb']} MB")
    return 0, {"status": "ok", "snapshot": name, **meta}


def cmd_reset(args) -> tuple[int, dict]:
    fordere_instanz()
    name = _gueltiger_name(args.name)
    quelle = os.path.join(SNAPSHOTS, name)
    if not os.path.exists(os.path.join(quelle, "meta.json")):
        raise Abbruch(f"Snapshot '{name}' gibt es nicht (oder er ist "
                      "unvollstaendig). `snapshot --list` zeigt, was da ist.", 2)
    for t in ("db-data", "data"):
        if os.path.exists(os.path.join(PG, t + ".vor-reset")):
            raise Abbruch(f"{t}.vor-reset existiert — Truemmer eines "
                          "abgebrochenen Resets, womoeglich der letzte gute "
                          "Zustand. Erst manuell klaeren, dann erneut.", 2)
    with open(os.path.join(quelle, "meta.json"), encoding="utf-8") as f:
        meta = json.load(f)
    fordere_keine_wartung()
    fordere_kein_fremder_mariadbd("Reset")

    sicherung = args.sicherung
    if sicherung:
        sicherung = _gueltiger_name(sicherung)
        if os.path.exists(os.path.join(SNAPSHOTS, sicherung)):
            raise Abbruch(f"Vorsicherung '{sicherung}' existiert schon.", 2)

    # Delta VOR dem Stoppen benennen — informierte Zustimmung statt
    # Zwangssicherung. --force ueberspringt das fuer den Skriptbetrieb.
    delta = None
    jetzt = version = None
    if not args.force or sicherung:
        if not port_open(DB_PORT):
            starte_mariadb()
        jetzt = zaehle_inhalte()
        version = moodle_version()
        delta = {k: {"jetzt": jetzt[k], "snapshot": meta.get(k)}
                 for k in ("kurse", "nutzer", "plugins")}
        if not args.force:
            log(f"Delta gegenueber '{name}' (erstellt {meta.get('erstellt', '?')}):")
            for k, v in delta.items():
                diff = v["jetzt"] - (v["snapshot"] or 0)
                log(f"  {k:<8} jetzt {v['jetzt']:>4} · im Snapshot "
                    f"{v['snapshot']} ({'+' if diff >= 0 else ''}{diff})")
            log("Das geht mit dem Reset verloren.")

    _setze_wartung(f"reset {name}")
    try:
        stoppe_apache()
        stoppe_mariadb()
        fordere_tote_dienste()
        if sicherung:
            _schreibe_snapshot(sicherung, jetzt, version)
            log(f"Vorsicherung '{sicherung}' angelegt")
        _spiele_zurueck(quelle)
        starte_mariadb()
        starte_apache()
    finally:
        _loese_wartung()

    # Aufraeumen erst NACH dem Start: inhaltlich ist der Reset durch, Moodle
    # laeuft — scheitert nur noch die Loeschung, sagen wir das deutlich,
    # statt mit heruntergefahrenen Diensten dazustehen.
    for t in ("db-data", "data"):
        try:
            loesche_baum(os.path.join(PG, t + ".vor-reset"))
        except OSError as e:
            raise Abbruch(
                f"Reset ist zurueckgespielt und Moodle laeuft, aber "
                f"{t}.vor-reset liess sich nicht loeschen ({e}) — von Hand "
                "entfernen, sonst verweigern start und reset kuenftig.", 2) from e
    log(f"Reset auf '{name}' fertig — Moodle laeuft: http://localhost:{WWW_PORT}")
    return 0, {"status": "ok", "reset_auf": name, "delta": delta,
               "vorsicherung": sicherung}


# --- Stufe 3: Bespielbar (seed, import) ------------------------------------

RESTORE_CLI = os.path.join(MOODLE, "admin", "cli", "restore_backup.php")
# Erfolgs-Marker der Moodle-Restore-CLI (deutsch + englisch, sprachrobust) —
# identisch zu run_restore.py des Gate-Labs
KURS_ID_RX = re.compile(
    r"(?:ID des wiederhergestellten Kurses|Restored course id)\D*(\d+)", re.I)

SCHUELER_PASSWORT = "Schueler123!"

# PHP-Vorlagen. Bewusst KEIN str.format (PHP ist voller geschweifter
# Klammern) — Platzhalter werden per replace() eingesetzt.
PHP_SEED = """<?php
// generiert von spielwiese.py seed — idempotent
define('CLI_SCRIPT', 1);
require('@KONFIG@');
require_once($CFG->dirroot . '/course/lib.php');
require_once($CFG->dirroot . '/user/lib.php');
require_once($CFG->dirroot . '/lib/enrollib.php');

$ergebnis = ['kurs' => null, 'kurs_neu' => false, 'nutzer_neu' => [],
             'eingeschrieben' => [], 'repariert' => []];

$short = 'spielwiese-beispiel';
$kurs = $DB->get_record('course', ['shortname' => $short]);
if (!$kurs) {
    $d = new stdClass();
    $d->fullname  = 'Spielwiese Beispielkurs';
    $d->shortname = $short;
    $d->category  = 1;
    $d->summary   = 'Angelegt von spielwiese.py seed - Spielfeld der Testschueler.';
    $d->numsections = 3;
    $kurs = create_course($d);
    $ergebnis['kurs_neu'] = true;
}
$ergebnis['kurs'] = (int)$kurs->id;

$studentrole = $DB->get_record('role', ['shortname' => 'student'], '*', MUST_EXIST);
$manual = enrol_get_plugin('manual');
$instanz = null;
foreach (enrol_get_instances($kurs->id, false) as $i) {
    if ($i->enrol === 'manual') { $instanz = $i; break; }
}
if (!$instanz) {
    $iid = $manual->add_instance($kurs);
    $instanz = $DB->get_record('enrol', ['id' => $iid], '*', MUST_EXIST);
}
$kontext = \\core\\context\\course::instance($kurs->id);

for ($n = 1; $n <= 5; $n++) {
    $username = sprintf('schueler%02d', $n);
    $u = $DB->get_record('user', ['username' => $username, 'deleted' => 0]);
    if (!$u) {
        $d = new stdClass();
        $d->username  = $username;
        $d->firstname = 'Schueler';
        $d->lastname  = sprintf('%02d', $n);
        $d->email     = $username . '@example.invalid';
        $d->auth      = 'manual';
        $d->confirmed = 1;
        $d->mnethostid = $CFG->mnet_localhost_id;
        $d->password  = '@PASSWORT@';
        $uid = user_create_user($d, true, false);
        $u = $DB->get_record('user', ['id' => $uid], '*', MUST_EXIST);
        $ergebnis['nutzer_neu'][] = $username;
    } else {
        // Bestandsnutzer auf die dokumentierten Zugaenge zuruecksetzen:
        // seed VERSPRICHT schueler01-05/@PASSWORT@ — ein in der UI
        // suspendierter Nutzer oder ein geaendertes Passwort wuerde das
        // sonst still brechen.
        $dirty = false;
        if ($u->suspended) { $u->suspended = 0; $dirty = true; }
        if ($u->auth !== 'manual') { $u->auth = 'manual'; $dirty = true; }
        if ($dirty) { user_update_user($u, false, false); }
        if (!validate_internal_user_password($u, '@PASSWORT@')) {
            update_internal_user_password($u, '@PASSWORT@');
            $dirty = true;
        }
        if ($dirty) { $ergebnis['repariert'][] = $username; }
    }
    if (!is_enrolled($kontext, $u)) {
        $manual->enrol_user($instanz, $u->id, $studentrole->id);
        $ergebnis['eingeschrieben'][] = $username;
    }
}
echo '@@', json_encode($ergebnis), '@@';
"""

PHP_ENROL = """<?php
// generiert von spielwiese.py import --schueler
define('CLI_SCRIPT', 1);
require('@KONFIG@');
require_once($CFG->dirroot . '/lib/enrollib.php');

$kursid = @KURSID@;
$kurs = $DB->get_record('course', ['id' => $kursid], '*', MUST_EXIST);
$studentrole = $DB->get_record('role', ['shortname' => 'student'], '*', MUST_EXIST);
$manual = enrol_get_plugin('manual');
$instanz = null;
foreach (enrol_get_instances($kursid, false) as $i) {
    if ($i->enrol === 'manual') { $instanz = $i; break; }
}
if (!$instanz) {
    $iid = $manual->add_instance($kurs);
    $instanz = $DB->get_record('enrol', ['id' => $iid], '*', MUST_EXIST);
}
$kontext = \\core\\context\\course::instance($kursid);
$rein = [];
$gefunden = 0;
for ($n = 1; $n <= 5; $n++) {
    $u = $DB->get_record('user',
        ['username' => sprintf('schueler%02d', $n), 'deleted' => 0]);
    if (!$u) { continue; }
    $gefunden++;
    if (!is_enrolled($kontext, $u)) {
        $manual->enrol_user($instanz, $u->id, $studentrole->id);
        $rein[] = $u->username;
    }
}
echo '@@', json_encode(['eingeschrieben' => $rein,
                        'gefunden' => $gefunden]), '@@';
"""


def fordere_db() -> None:
    """Instanz muss existieren, MariaDB muss laufen (wird ggf. gestartet).

    Das Wartungs-Lock wird VOR dem Start geprueft: sonst faehrt ein
    nebenlaeufiges seed/import/purge/upgrade die DB auf exakt dem Datadir
    hoch, das snapshot/reset gerade kopieren — der Snapshot froere einen
    heissen Zustand ein.
    """
    fordere_instanz()
    fordere_keine_wartung()
    if not port_open(DB_PORT):
        starte_mariadb()


def _php_pfad(pfad: str) -> str:
    """Pfad fuer eine einfach-quotierte PHP-Stringliterale escapen."""
    return pfad.replace("\\", "/").replace("'", "\\'")


def _php_marker(skript_pfad: str, timeout: int = 300) -> dict:
    """PHP-Skript laufen lassen und das @@json@@-Ergebnis herausziehen.

    Non-greedy + letzter Treffer: debugdisplay=1 kann nach dem Marker noch
    Ausgaben anhaengen, und ein greedy .* wuerde von der ersten bis zur
    LETZTEN Markerklammer alles einsammeln.
    """
    r = run([PHP, skript_pfad], cwd=MOODLE, timeout=timeout, check=False)
    ausgabe = (r.stdout or "") + ("\n" + r.stderr if r.stderr else "")
    treffer = re.findall(r"@@(\{.*?\})@@", ausgabe, re.S)
    if r.returncode != 0 or not treffer:
        raise Abbruch(f"{os.path.basename(skript_pfad)} fehlgeschlagen "
                      f"(rc={r.returncode}):\n{ausgabe[-1500:]}", 2)
    try:
        return json.loads(treffer[-1])
    except json.JSONDecodeError as e:
        raise Abbruch(f"{os.path.basename(skript_pfad)}: Marker-JSON "
                      f"unlesbar ({e}):\n{treffer[-1][:500]}", 2) from e


def cmd_seed(args) -> tuple[int, dict]:
    fordere_db()
    skript = os.path.join(PG, "_seed.php")
    with open(skript, "w", encoding="utf-8") as f:
        f.write(PHP_SEED
                .replace("@KONFIG@", _php_pfad(os.path.join(MOODLE, "config.php")))
                .replace("@PASSWORT@", SCHUELER_PASSWORT))
    ergebnis = _php_marker(skript)
    log(f"Beispielkurs: id={ergebnis['kurs']}"
        f"{' (neu angelegt)' if ergebnis['kurs_neu'] else ' (war schon da)'}")
    log(f"neue Nutzer: {', '.join(ergebnis['nutzer_neu']) or 'keine'}")
    if ergebnis.get("repariert"):
        log(f"Zugaenge repariert (entsperrt/Passwort zurueck): "
            f"{', '.join(ergebnis['repariert'])}")
    log(f"neu eingeschrieben: {', '.join(ergebnis['eingeschrieben']) or 'keine'}")
    log(f"Zugaenge: schueler01–schueler05 / {SCHUELER_PASSWORT}")
    return 0, {"status": "ok", **ergebnis}


def cmd_import(args) -> tuple[int, dict]:
    fordere_db()
    mbz = os.path.abspath(args.mbz)
    if not os.path.isfile(mbz):
        raise Abbruch(f".mbz nicht gefunden: {mbz}", 2)
    log(f"importiere {os.path.basename(mbz)} (dauerhaft, KEIN Teardown — "
        "das ist der Unterschied zum Gate-Lab)")
    r = run([PHP, RESTORE_CLI, f"--file={mbz}", "--categoryid=1"],
            cwd=MOODLE, timeout=1800, check=False)
    ausgabe = (r.stdout or "") + ("\n" + r.stderr if r.stderr else "")
    m = KURS_ID_RX.search(ausgabe)
    schwanz = "\n".join([z for z in ausgabe.splitlines() if z.strip()][-40:])
    if r.returncode == 0 and not m:
        raise Abbruch(
            "Restore lief durch (rc=0), aber die Kurs-ID war in der Ausgabe "
            "nicht zu erkennen (fremdes Sprachpaket? Format geaendert?). Der "
            "Kurs existiert vermutlich — NICHT blind erneut importieren, "
            "sonst stapeln sich Kopien. Ausgabe:\n" + schwanz, 2)
    if r.returncode != 0:
        if not port_open(DB_PORT):
            raise Abbruch("Datenbank waehrend des Restores verloren", 3)
        raise Abbruch(
            "Moodle lehnt die .mbz ab. Achtung: restore_backup.php legt den "
            "Zielkurs VOR dem Restore an — in Kategorie 1 kann ein "
            "Ruinen-Kurs zurueckbleiben (loeschen oder `reset`).\n" + schwanz, 2)
    kursid = int(m.group(1))
    log(f"Kurs restauriert: id={kursid}")

    eingeschrieben = []
    if args.schueler:
        skript = os.path.join(PG, "_enrol.php")
        with open(skript, "w", encoding="utf-8") as f:
            f.write(PHP_ENROL
                    .replace("@KONFIG@", _php_pfad(os.path.join(MOODLE, "config.php")))
                    .replace("@KURSID@", str(kursid)))
        enrol = _php_marker(skript)
        eingeschrieben = enrol["eingeschrieben"]
        if enrol["gefunden"] == 0:
            raise Abbruch(
                f"Kurs {kursid} ist importiert, aber es existiert KEIN "
                "einziger Testschueler — erst `spielwiese.py seed` laufen "
                "lassen, dann von Hand einschreiben oder erneut importieren.", 2)
        log(f"Testschueler eingeschrieben: "
            f"{', '.join(eingeschrieben) or 'alle waren schon drin'} "
            f"({enrol['gefunden']} von 5 Konten vorhanden)")
    return 0, {"status": "ok", "kursid": kursid,
               "url": f"http://localhost:{WWW_PORT}/course/view.php?id={kursid}",
               "eingeschrieben": eingeschrieben}


# --- Stufe 4: Plugin-Werkstatt ----------------------------------------------

# Frankenstyle-Typ -> Ordner im Moodle-Baum. Nicht abschliessend — fehlt ein
# Typ, bricht link mit Exit 2 und dieser Tabelle als Hinweis ab.
TYP_ORDNER = {
    "local": "local", "mod": "mod", "block": "blocks",
    "qtype": "question/type", "qbank": "question/bank",
    "format": "course/format", "theme": "theme", "auth": "auth",
    "enrol": "enrol", "filter": "filter", "repository": "repository",
    "tool": "admin/tool", "report": "report",
    "gradereport": "grade/report", "gradeexport": "grade/export",
    "availability": "availability/condition",
    "customfield": "customfield/field", "profilefield": "user/profile/field",
    "tiny": "lib/editor/tiny/plugins", "atto": "lib/editor/atto/plugins",
}


def _ist_junction(pfad: str) -> bool:
    try:
        st = os.lstat(pfad)
    except OSError:
        return False
    return bool(st.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _lese_komponente(quelle: str) -> str:
    vp = os.path.join(quelle, "version.php")
    if not os.path.isfile(vp):
        raise Abbruch(f"{vp} fehlt — das ist keine Plugin-Quelle.", 2)
    with open(vp, encoding="utf-8", errors="replace") as f:
        text = f.read()
    m = re.search(r"\$plugin->component\s*=\s*['\"]([a-z][a-z0-9]*_[a-z0-9_]+)['\"]",
                  text)
    if not m:
        raise Abbruch(f"In {vp} steht kein $plugin->component — ohne "
                      "Frankenstyle-Namen kein Einhaengeort bestimmbar.", 2)
    return m.group(1)


def _lade_registry() -> dict:
    if not os.path.exists(PLUGINS_JSON):
        return {}
    try:
        with open(PLUGINS_JSON, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise Abbruch(f"{PLUGINS_JSON} ist unlesbar ({e}) — von Hand "
                      "reparieren oder loeschen.", 2) from e


def _speichere_registry(reg: dict) -> None:
    # atomar (tmp + replace): ein Abbruch mitten im Schreiben darf keine
    # halbe Datei hinterlassen, die danach alle Plugin-Kommandos blockiert
    tmp = PLUGINS_JSON + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False, indent=1)
    os.replace(tmp, PLUGINS_JSON)


def cmd_plugin_link(args) -> tuple[int, dict]:
    fordere_instanz()
    reg = _lade_registry()  # VOR dem mklink: unlesbare Registry soll den
    #                         Link verhindern, nicht erst die Buchfuehrung
    quelle = os.path.abspath(args.quelle)
    komponente = _lese_komponente(quelle)
    typ, _, plugname = komponente.partition("_")
    unterordner = TYP_ORDNER.get(typ)
    if not unterordner:
        raise Abbruch(f"Plugintyp '{typ}' ({komponente}) fehlt in der "
                      f"Zuordnungstabelle TYP_ORDNER — nachtragen. Bekannt: "
                      f"{', '.join(sorted(TYP_ORDNER))}", 2)
    # Der Zielordner heisst IMMER wie das Plugin: Moodles upgradelib wirft
    # sonst plugin_misplaced_exception (Ordnername muss zum component
    # passen). Ein --als-Flag waere darum strukturell kaputt.
    # plugname stammt aus der component-Regex und ist pfadzeichenfrei.
    ziel = os.path.join(MOODLE, *unterordner.split("/"), plugname)

    if os.path.lexists(ziel):
        if _ist_junction(ziel) and os.path.normcase(
                os.path.normpath(os.path.realpath(ziel))) == os.path.normcase(
                os.path.normpath(os.path.realpath(quelle))):
            log(f"{komponente} ist bereits eingehaengt ({ziel})")
            return 0, {"status": "ok", "komponente": komponente,
                       "ziel": ziel, "bereits": True}
        raise Abbruch(f"{ziel} existiert und ist kein Junction auf diese "
                      "Quelle — nicht ueberschreiben.", 2)

    os.makedirs(os.path.dirname(ziel), exist_ok=True)
    # _winapi statt `cmd /c mklink`: cmd expandiert %VAR% selbst in Quotes
    # und deutet & | ^ als Befehlstrenner — ein Pfad wie C:\dev\a&b wuerde
    # Fremdkommandos ausfuehren. Der direkte Win32-Aufruf parst nichts.
    import _winapi
    try:
        _winapi.CreateJunction(quelle, ziel)
    except OSError as e:
        raise Abbruch(f"Junction fehlgeschlagen: {e}", 2) from e
    if not _ist_junction(ziel):
        raise Abbruch(f"Junction wurde nicht angelegt: {ziel}", 2)
    reg[plugname] = {"komponente": komponente, "quelle": quelle, "ziel": ziel,
                     "seit": datetime.now().isoformat(timespec="seconds")}
    _speichere_registry(reg)
    log(f"{komponente}: {quelle} -> {ziel}")
    log("naechster Schritt: `spielwiese.py upgrade` installiert das Plugin")
    return 0, {"status": "ok", "komponente": komponente, "name": plugname,
               "quelle": quelle, "ziel": ziel}


def cmd_plugin_unlink(args) -> tuple[int, dict]:
    fordere_instanz()
    reg = _lade_registry()
    eintrag = reg.get(args.name)
    if not eintrag:
        raise Abbruch(f"'{args.name}' steht nicht in der Registry "
                      f"({', '.join(sorted(reg)) or 'leer'}).", 2)
    ziel = eintrag["ziel"]
    # lexists/_ist_junction statt exists: exists() folgt dem Junction und
    # meldet False, wenn die QUELLE fehlt — die tote Junction bliebe dann
    # fuer immer im Baum liegen und blockierte jedes erneute link.
    if _ist_junction(ziel):
        os.rmdir(ziel)  # entfernt nur den Junction, nie die Quelle
    elif os.path.lexists(ziel):
        raise Abbruch(f"{ziel} ist KEIN Junction (mehr) — da liegen echte "
                      "Dateien, die loesche ich nicht.", 2)
    del reg[args.name]
    _speichere_registry(reg)
    log(f"{eintrag['komponente']} ausgehaengt — die Quelle bleibt unberuehrt.")
    log("Achtung: In der DB ist das Plugin noch installiert; Moodle meldet "
        "es als 'fehlt auf der Platte'. Deinstallieren oder `reset`.")
    return 0, {"status": "ok", "entfernt": args.name,
               "quelle_unberuehrt": eintrag["quelle"]}


def cmd_plugin_list(args) -> tuple[int, dict]:
    fordere_instanz()
    reg = _lade_registry()
    eintraege = []
    for name, e in sorted(reg.items()):
        if _ist_junction(e["ziel"]):
            if os.path.exists(os.path.join(e["quelle"], "version.php")):
                zustand = "ok"
            else:
                zustand = "quelle fehlt (tote junction)"
        elif os.path.lexists(e["ziel"]):
            zustand = "ziel ist kein junction (!)"
        else:
            zustand = "junction fehlt"
        eintraege.append({"name": name, **e, "zustand": zustand})
        log(f"  {name:<16} {e['komponente']:<24} {zustand:<24} {e['quelle']}")
    if not eintraege:
        log("keine Plugin-Quellen eingehaengt")
    return 0, {"status": "ok", "plugins": eintraege}


def cmd_purge(args) -> tuple[int, dict]:
    fordere_db()
    run([PHP, os.path.join(MOODLE, "admin", "cli", "purge_caches.php")],
        cwd=MOODLE, timeout=300)
    log("Caches geleert")
    return 0, {"status": "ok"}


def cmd_upgrade(args) -> tuple[int, dict]:
    fordere_db()
    log("Upgrade-Lauf (installiert auch frisch eingehaengte Plugins) …")
    r = run([PHP, os.path.join(MOODLE, "admin", "cli", "upgrade.php"),
             "--non-interactive"], cwd=MOODLE, timeout=3600, check=False)
    if r.returncode != 0:
        if not port_open(DB_PORT):
            raise Abbruch("Datenbank waehrend des Upgrades verloren", 3)
        raise Abbruch(f"upgrade.php rc={r.returncode}:\n"
                      f"{((r.stdout or '') + (r.stderr or ''))[-1500:]}", 2)
    log("Upgrade fertig")
    return 0, {"status": "ok"}


# --- CLI -------------------------------------------------------------------

def main() -> int:
    global _QUIET
    ap = argparse.ArgumentParser(
        prog="spielwiese.py",
        description="Moodle-Spielwiese: persistente Entwicklungs- und "
                    "Erprobungsinstanz neben dem sterilen Gate-Lab.")
    ap.add_argument("--json", action="store_true",
                    help="EIN JSON-Objekt auf stdout statt Fliesstext")

    # --json soll VOR und HINTER dem Unterkommando funktionieren; getippt
    # wird es fast immer hinten (`status --json`). SUPPRESS sorgt dafuer,
    # dass die hintere Variante die vordere nicht auf False zuruecksetzt.
    gemeinsam = argparse.ArgumentParser(add_help=False)
    gemeinsam.add_argument("--json", action="store_true",
                           default=argparse.SUPPRESS,
                           help="EIN JSON-Objekt auf stdout statt Fliesstext")

    sub = ap.add_subparsers(dest="kommando", required=True)

    p = sub.add_parser("setup", help="Instanz aufbauen (idempotent)",
                       parents=[gemeinsam])
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_setup)

    sub.add_parser("start", help="MariaDB + Apache starten",
                   parents=[gemeinsam]).set_defaults(fn=cmd_start)
    sub.add_parser("stop", help="MariaDB + Apache stoppen",
                   parents=[gemeinsam]).set_defaults(fn=cmd_stop)
    sub.add_parser("status", help="Zustand beider Dienste",
                   parents=[gemeinsam]).set_defaults(fn=cmd_status)

    p = sub.add_parser("snapshot", help="Zustand sichern (db-data + data)",
                       parents=[gemeinsam])
    p.add_argument("name", nargs="?", help="Name des Snapshots")
    p.add_argument("--list", dest="liste", action="store_true",
                   help="vorhandene Snapshots zeigen")
    p.set_defaults(fn=cmd_snapshot)

    p = sub.add_parser("reset", help="Snapshot zurueckspielen",
                       parents=[gemeinsam])
    p.add_argument("name", help="Zielsnapshot")
    p.add_argument("--snapshot", dest="sicherung", metavar="NAME",
                   help="aktuellen Zustand vorher unter NAME sichern")
    p.add_argument("--force", action="store_true",
                   help="Delta-Ausgabe ueberspringen (Skriptbetrieb)")
    p.set_defaults(fn=cmd_reset)

    p = sub.add_parser("seed", help="Testschueler + Beispielkurs (idempotent)",
                       parents=[gemeinsam])
    p.set_defaults(fn=cmd_seed)

    p = sub.add_parser("import", help="Kurs dauerhaft einspielen (kein Teardown)",
                       parents=[gemeinsam])
    p.add_argument("mbz", help="Pfad zur .mbz-Kurssicherung")
    p.add_argument("--schueler", action="store_true",
                   help="Testschueler danach als Teilnehmer einschreiben")
    p.set_defaults(fn=cmd_import)

    p = sub.add_parser("plugin", help="Plugin-Quelle per Junction verwalten",
                       parents=[gemeinsam])
    aktionen = p.add_subparsers(dest="aktion", required=True)
    q = aktionen.add_parser("link", parents=[gemeinsam],
                            help="Quelle in den Moodle-Baum einhaengen "
                            "(Zielname folgt IMMER dem component — Moodle "
                            "erzwingt Ordnername==Pluginname)")
    q.add_argument("quelle", help="Ordner mit version.php")
    q.set_defaults(fn=cmd_plugin_link)
    q = aktionen.add_parser("unlink", parents=[gemeinsam],
                            help="Junction entfernen (Quelle bleibt)")
    q.add_argument("name")
    q.set_defaults(fn=cmd_plugin_unlink)
    q = aktionen.add_parser("list", parents=[gemeinsam],
                            help="eingehaengte Quellen zeigen")
    q.set_defaults(fn=cmd_plugin_list)

    p = sub.add_parser("debug", help="Debug-Modus zeigen oder umschalten "
                       "(schnell ~0,1 s/Seite · entwickler ~1 s/Seite mit "
                       "vollen Backtraces)", parents=[gemeinsam])
    p.add_argument("modus", nargs="?", choices=["schnell", "entwickler"],
                   help="ohne Angabe: aktuellen Modus zeigen")
    p.set_defaults(fn=cmd_debug)

    sub.add_parser("purge", help="Moodle-Caches leeren",
                   parents=[gemeinsam]).set_defaults(fn=cmd_purge)
    sub.add_parser("upgrade", help="Upgrade-Lauf (nach version.php-Bump "
                   "oder plugin link)",
                   parents=[gemeinsam]).set_defaults(fn=cmd_upgrade)

    args = ap.parse_args()
    _QUIET = args.json

    try:
        code, nutzlast = args.fn(args)
    except Abbruch as e:
        nutzlast = {"status": "fehler", "meldung": str(e)}
        code = e.code
        if args.json:
            print(json.dumps(nutzlast, ensure_ascii=False))
        else:
            print(f"[spielwiese] FEHLER: {e}", file=sys.stderr, flush=True)
        return code
    except KeyboardInterrupt:
        # Auch Strg-C haelt den Vertrag: definierte Meldung, Exit 3. Die
        # Zustands-Sicherheit haengt nicht hieran — Snapshot/Reset raeumen
        # ihre Baustellen ueber eigene except-BaseException-Pfade.
        if args.json:
            print(json.dumps({"status": "fehler",
                              "meldung": "abgebrochen (Strg-C)"},
                             ensure_ascii=False))
        else:
            print("[spielwiese] abgebrochen (Strg-C)", file=sys.stderr,
                  flush=True)
        return 3
    except Exception as e:  # noqa: BLE001 — Vertrag ist 0/2/3, nie ein nackter Traceback
        import traceback
        tb = traceback.format_exc()
        if args.json:
            print(json.dumps({"status": "fehler",
                              "meldung": f"Unerwarteter Fehler: {e}",
                              "traceback": tb}, ensure_ascii=False))
        else:
            print(tb, file=sys.stderr, flush=True)
            print(f"[spielwiese] UNERWARTETER FEHLER: {e}", file=sys.stderr,
                  flush=True)
        return 3

    if args.json:
        print(json.dumps(nutzlast, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
