# -*- coding: utf-8 -*-
"""open_notebooklm_helper.py — Unterstützt den NotebookLM Video-Recap Flow.

1. Kopiert das Briefing für die KI-Moderatoren direkt in die Windows-Zwischenablage.
2. Öffnet NotebookLM im Standard-Browser (Chrome).
3. Öffnet den Ordner mit dem Material-Dossier (PDF) und dem Text-Dossier (MD).
"""
import os
import subprocess
import sys

# Force UTF-8 stdout
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

COURSE_DIR = os.getcwd()
BRIEF_FILE = os.path.join(COURSE_DIR, "statistik_notebooklm_brief.txt")
DOSSIER_PDF = os.path.join(COURSE_DIR, "materials", "Kurs-Materialdossier.pdf")


def copy_brief_to_clipboard():
    if os.path.exists(BRIEF_FILE):
        with open(BRIEF_FILE, "r", encoding="utf-8") as f:
            text = f.read()
        try:
            p = subprocess.Popen(["powershell", "-NoProfile", "-Command", "$input | Set-Clipboard"], stdin=subprocess.PIPE, text=True, encoding="utf-8")
            p.communicate(input=text)
            print("[OK] Briefing-Text wurde in die Zwischenablage kopiert!")
        except Exception as e:
            print(f"[Hinweis] Zwischenablage: {e}")


def open_browser_and_folders():
    print("[OK] Oeffne NotebookLM im Browser...")
    subprocess.Popen(["cmd", "/c", "start", "https://notebooklm.google.com"], shell=True)
    if os.path.exists(DOSSIER_PDF):
        materials_dir = os.path.dirname(DOSSIER_PDF)
        print(f"[OK] Oeffne Material-Ordner: {materials_dir}")
        subprocess.Popen(["explorer", materials_dir])


if __name__ == "__main__":
    copy_brief_to_clipboard()
    open_browser_and_folders()
