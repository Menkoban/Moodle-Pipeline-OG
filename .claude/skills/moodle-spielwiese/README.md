# moodle-spielwiese 🎮🧪

[![Moodle 4.5 LTS](https://img.shields.io/badge/Moodle-4.5%20LTS-orange.svg)](https://moodle.org/)
[![Port 8090](https://img.shields.io/badge/Web--UI-Port%208090-brightgreen.svg)](http://localhost:8090)
[![Port 3308](https://img.shields.io/badge/MariaDB-Port%203308-blue.svg)](README.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Persistente Moodle-4.5-Spielwiese & Plugin-Entwicklungsumgebung.**  
Läuft lokal unter `C:\moodle-playground` (Apache 2.4 + mod_fcgid auf Port **8090**, MariaDB auf Port **3308**). Dient als dauerhafte Umgebung, um generierte Kurse mit Testschülern (`schueler01`–`schueler05`) interaktiv durchzuklicken und eigene Moodle-Plugins zu entwickeln.

---

## ⚖️ Abgrenzung: Spielwiese vs. Testinstanz (Gate-Lab)

| Eigenschaft | Gate-Lab (`moodle-testinstanz`) | Moodle-Spielwiese (`moodle-spielwiese`) |
|---|---|---|
| **Zweck** | **Steriler Restore-Check (Gate 7)** | **Inhaltliche & interaktive Erprobung (Gate 8)** |
| **Lebensdauer** | Temporär (automatischer Teardown nach Check) | **Dauerhaft / Persistent** |
| **Webserver** | Eingebauter PHP-Server (Port 8088) | **Apache 2.4 + mod_fcgid** (Port 8090) |
| **Datenbank** | MariaDB Port 3307 | **MariaDB Port 3308** |
| **Benutzer** | Admin | **Admin + 5 Testschüler (`schueler01`–`schueler05`)** |
| **Hintergrund-Daemon** | — | `scripts/serve.py` (hält Dienste dauerhaft aktiv) |

---

## 💻 Installation & Setup

Dieser Skill ist Teil des Monorepos [`Moodle-Pipeline-OG-`](https://github.com/Menkoban/Moodle-Pipeline-OG-) und liegt dort unter `.claude/skills/moodle-spielwiese/`. Installation und Aktualisierung für alle Skills gemeinsam: siehe [README im Hauptverzeichnis](../../../README.md#installation).

**Einmalige Einrichtung der Spielwiese:**
```bash
python scripts/spielwiese.py setup
```
*Lädt Moodle 4.5, PHP 8.2 NTS, MariaDB 10.11, Apache 2.4 und das Plugin format_tiles herunter und richtet die Instanz unter `C:\moodle-playground` ein.*

---

## 🚀 Wichtige CLI-Befehle

```bash
# 1. Spielwiese starten (oder im Hintergrund via serve.py)
python scripts/spielwiese.py start
# -> Web-UI: http://localhost:8090 (Admin: admin / Admin123!)

# 2. Status prüfen
python scripts/spielwiese.py status

# 3. Kurs (.mbz) dauerhaft einspielen & Testschüler einschreiben
python scripts/spielwiese.py import mein-kurs.mbz --schueler

# 4. Testschüler seeden / reparieren
python scripts/spielwiese.py seed
# -> Accounts: schueler01 .. schueler05 (Passwort: Schueler123!)

# 5. Snapshot anlegen / zurücksetzen
python scripts/spielwiese.py snapshot meilenstein_1
python scripts/spielwiese.py reset nullzustand --force

# 6. Spielwiese stoppen
python scripts/spielwiese.py stop
```

---

## 📄 Lizenz

Dieses Projekt ist unter der **MIT-Lizenz** lizenziert.
