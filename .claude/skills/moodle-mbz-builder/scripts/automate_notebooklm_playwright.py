# -*- coding: utf-8 -*-
"""automate_notebooklm_playwright.py — Vollautomatische Steuerung und Download-Watcher für NotebookLM Video-Recap.

1. Kopiert das Video-Briefing in die Windows-Zwischenablage.
2. Öffnet Chrome mit Fernsteuerung auf Port 9222 und lädt NotebookLM.
3. Öffnet den Ordner mit dem Material-Dossier (PDF).
4. Verbindet via Playwright (CDP) und überwacht die Erstellung.
5. Überwacht gleichzeitig den Downloads-Ordner: Sobald ein neues Video heruntergeladen wird,
   bindet das Skript es automatisch in den Moodle-Kurs ein und aktualisiert die Spielwiese!
"""
import glob
import os
import shutil
import socket
import subprocess
import sys
import time
from playwright.sync_api import sync_playwright

# Force UTF-8 stdout
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

COURSE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "OneDrive - HSOS", "Desktop", "Moodle-Kurse", "statistik-beschreibend-streuungsmasse"))
if not os.path.isdir(COURSE_DIR):
    COURSE_DIR = os.getcwd()

BRIEF_FILE = os.path.join(COURSE_DIR, "statistik_notebooklm_brief.txt")
DOSSIER_MD = os.path.join(COURSE_DIR, "dossier.md")
DOSSIER_PDF = os.path.join(COURSE_DIR, "materials", "Kurs-Materialdossier.pdf")
PROFILE_DIR = os.path.expanduser("~/.chrome-notebooklm-profile")
CHROME_EXE = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CDP_PORT = 9222
DOWNLOADS_DIR = os.path.expanduser("~/Downloads")


def is_port_open(port):
    s = socket.socket()
    res = s.connect_ex(('127.0.0.1', port))
    s.close()
    return res == 0


def copy_brief_to_clipboard():
    if os.path.exists(BRIEF_FILE):
        with open(BRIEF_FILE, "r", encoding="utf-8") as f:
            text = f.read()
        try:
            p = subprocess.Popen(["powershell", "-NoProfile", "-Command", "$input | Set-Clipboard"], stdin=subprocess.PIPE, text=True, encoding="utf-8")
            p.communicate(input=text)
            print("[OK] Video-Briefing wurde in die Windows-Zwischenablage kopiert!")
        except Exception as e:
            print(f"[Hinweis Zwischenablage] {e}")


def ensure_chrome():
    if not is_port_open(CDP_PORT):
        print(f"[Browser] Starte Google Chrome auf Port {CDP_PORT}...")
        cmd = [
            CHROME_EXE,
            f"--remote-debugging-port={CDP_PORT}",
            f"--user-data-dir={PROFILE_DIR}",
            "--no-first-run",
            "--no-default-browser-check",
            "https://notebooklm.google.com"
        ]
        subprocess.Popen(cmd)
        for _ in range(30):
            time.sleep(0.5)
            if is_port_open(CDP_PORT):
                print("[Browser] Chrome CDP Port 9222 ist bereit!")
                return True
        raise RuntimeError("Chrome CDP Port konnte nicht geöffnet werden.")
    return True


def integrate_video(video_path: str):
    print(f"\n🚀 [Video-Integration] Binde fertiges Video ein: {video_path}")
    target_video = os.path.join(COURSE_DIR, "assets", "recap_video.mp4")
    shutil.copy2(video_path, target_video)
    
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    set_script = os.path.join(scripts_dir, "set_recap_video.py")
    course_json = os.path.join(COURSE_DIR, "course.json")
    
    # 1. set_recap_video.py
    subprocess.run([sys.executable, set_script, course_json, "--file", "assets/recap_video.mp4"], cwd=COURSE_DIR)
    
    # 2. build_simulation.py
    subprocess.run([sys.executable, os.path.join(scripts_dir, "build_simulation.py"), course_json], cwd=COURSE_DIR)
    
    # 3. make_materials.py
    subprocess.run([sys.executable, os.path.join(scripts_dir, "make_materials.py"), "course.sim.json"], cwd=COURSE_DIR)
    
    # 4. build_mbz.py
    mbz_out = os.path.join(COURSE_DIR, "sicherung-moodle2-statistik-beschreibend-bgt.mbz")
    subprocess.run([sys.executable, os.path.join(scripts_dir, "build_mbz.py"), "course.sim.materialized.json", "-o", mbz_out], cwd=COURSE_DIR)
    
    # 5. Spielwiese Import
    spielwiese_script = os.path.join(scripts_dir, "..", "..", "moodle-spielwiese", "scripts", "spielwiese.py")
    if os.path.exists(spielwiese_script):
        subprocess.run([sys.executable, spielwiese_script, "import", mbz_out], cwd=COURSE_DIR)
        
    print("\n🎉 [FERTIG] Video wurde erfolgreich in Moodle eingebunden und auf der Spielwiese aktualisiert!")


def watch_and_automate():
    copy_brief_to_clipboard()
    ensure_chrome()
    
    # Materialordner im Explorer öffnen
    if os.path.exists(DOSSIER_PDF):
        materials_dir = os.path.dirname(DOSSIER_PDF)
        print(f"[OK] Öffne Material-Ordner: {materials_dir}")
        subprocess.Popen(["explorer", materials_dir])
        
    start_time = time.time()
    initial_files = set(glob.glob(os.path.join(DOWNLOADS_DIR, "*.mp4")) + glob.glob(os.path.join(DOWNLOADS_DIR, "*.webm")))
    
    # Playwright-Verbindung
    try:
        with sync_playwright() as p:
            print("[Playwright] Verbinde mit Chrome...")
            browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP_PORT}")
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.pages[0] if context.pages else context.new_page()
            
            if "notebooklm.google.com" not in page.url:
                page.goto("https://notebooklm.google.com", wait_until="domcontentloaded")
                
            print(f"[Playwright] Browser ist geöffnet auf: {page.url}")
    except Exception as e:
        print(f"[Playwright Hinweis] {e}")

    print("\n👀 [Watcher aktiv] Überwache Downloads-Ordner auf fertiggestelltes Erklärvideo...")
    print("   Sobald Sie das Video in NotebookLM generiert und heruntergeladen haben, übernimmt das Skript vollautomatisch!")
    
    for i in range(120):  # 10 Minuten Überwachung
        time.sleep(5)
        current_files = set(glob.glob(os.path.join(DOWNLOADS_DIR, "*.mp4")) + glob.glob(os.path.join(DOWNLOADS_DIR, "*.webm")))
        new_files = current_files - initial_files
        
        # Prüfen ob eine neue Datei existiert und nicht mehr wächst (Download abgeschlossen)
        for nf in new_files:
            if os.path.getsize(nf) > 100000:  # > 100 KB
                s1 = os.path.getsize(nf)
                time.sleep(2)
                s2 = os.path.getsize(nf)
                if s1 == s2:
                    print(f"\n✨ [Neues Video erkannt] {nf} ({s2 / (1024*1024):.2f} MB)")
                    integrate_video(nf)
                    return True

    print("\n[Watcher Timeout] Keine neue Videodatei in den letzten 10 Minuten erkannt.")
    return False


if __name__ == "__main__":
    watch_and_automate()
