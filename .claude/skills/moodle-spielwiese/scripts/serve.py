# -*- coding: utf-8 -*-
"""serve.py — Persistenter Daemon-Server für die Moodle-Spielwiese.

Hält MariaDB (Port 3308) und Apache (Port 8090) dauerhaft am Leben,
überwacht die Prozesse und verhindert das automatische Schließen durch
Prozess-Cleanup.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import spielwiese  # noqa: E402


def main():
    print("[serve] Starte Moodle-Spielwiese im persistenten Daemon-Modus...")
    spielwiese.fordere_instanz()
    spielwiese.fordere_keine_wartung()
    
    # 1. Starten
    spielwiese.starte_mariadb()
    spielwiese.starte_apache()
    print(f"[serve] Spielwiese läuft dauerhaft auf http://localhost:{spielwiese.WWW_PORT}")
    print("[serve] Überwachung aktiv. Drücke Strg+C zum Beenden.")
    sys.stdout.flush()

    # 2. Persistente Überwachungsschleife
    try:
        while True:
            time.sleep(2)
            if not spielwiese.port_open(spielwiese.DB_PORT):
                print("[serve] MariaDB verloren — starte neu...")
                spielwiese.starte_mariadb()
            if not spielwiese.port_open(spielwiese.WWW_PORT):
                print("[serve] Apache verloren — starte neu...")
                spielwiese.starte_apache()
            sys.stdout.flush()
    except KeyboardInterrupt:
        print("[serve] Fahre Dienste herunter...")
        spielwiese.stoppe_apache()
        spielwiese.stoppe_mariadb()
        print("[serve] Beendet.")


if __name__ == "__main__":
    main()
