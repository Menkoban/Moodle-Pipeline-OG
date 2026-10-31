# -*- coding: utf-8 -*-
"""run_goal_notebooklm.py — Autonomer, fehlertoleranter Agent für NotebookLM Video-Generierung.

Resilient gegenüber Page-Switches, Popups und Reconnects.
"""
import glob
import os
import shutil
import socket
import subprocess
import sys
import time
from playwright.sync_api import sync_playwright

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


def ensure_chrome():
    if not is_port_open(CDP_PORT):
        print(f"[Agent] Starte Chrome mit Fernsteuerung auf Port {CDP_PORT}...")
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
                print("[Agent] Chrome Port 9222 ist bereit!")
                return True
        raise RuntimeError("Chrome konnte nicht gestartet werden.")
    return True


def get_active_page(context):
    pages = [p for p in context.pages if not p.is_closed()]
    if not pages:
        return context.new_page()
    for p in reversed(pages):
        try:
            if "notebooklm.google.com" in p.url or "accounts.google.com" in p.url:
                return p
        except Exception:
            pass
    return pages[-1]


def run_pipeline():
    ensure_chrome()
    
    with open(BRIEF_FILE, "r", encoding="utf-8") as f:
        brief_text = f.read()

    with sync_playwright() as p:
        print("[Agent] Verbinde ueber Chrome DevTools Protocol...")
        browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP_PORT}")
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = get_active_page(context)
        
        print(f"[Agent] Aktuelle URL: {page.url}")
        
        # 1. Login-Überwachung
        while True:
            try:
                page = get_active_page(context)
                if "notebooklm.google.com" in page.url and "accounts.google.com" not in page.url:
                    print("[OK] Login erkannt!")
                    break
                print("[Agent] Warte auf Google-Login im geöffneten Chrome-Fenster...")
                time.sleep(3)
            except Exception as e:
                print(f"[Agent Reconnect] {e}")
                time.sleep(3)

        time.sleep(2)
        page = get_active_page(context)
        page.bring_to_front()
        page.screenshot(path=os.path.join(COURSE_DIR, "step1_home.png"))
        
        # 2. Notizbuch erstellen / Quellendialog
        # Prüfen ob wir bereits in einem Notizbuch sind oder auf der Startseite
        if "/notebook/" not in page.url:
            print("[Agent] Klicke auf 'Neues Notizbuch'...")
            create_btn = page.locator("button:has-text('Neues Notizbuch'), button:has-text('New notebook'), [aria-label*='Neues Notizbuch'], [aria-label*='New notebook']").first
            if create_btn.is_visible():
                create_btn.click()
                time.sleep(4)
        
        page = get_active_page(context)
        page.screenshot(path=os.path.join(COURSE_DIR, "step2_modal.png"))
        
        # 3. Quelle hochladen
        print(f"[Agent] Lade Quelle hoch: {DOSSIER_PDF}...")
        try:
            file_input = page.locator("input[type='file']").first
            if file_input.is_visible(timeout=3000) or True:
                page.set_input_files("input[type='file']", DOSSIER_PDF)
                print("[OK] PDF übergeben!")
                time.sleep(10)
        except Exception as e:
            print(f"[Hinweis File-Input] {e}. Versuche Text...")
            paste_tab = page.locator("text='Kopierter Text', text='Copied text'").first
            if paste_tab.is_visible():
                paste_tab.click()
                time.sleep(1)
                with open(DOSSIER_MD, "r", encoding="utf-8") as f:
                    md_text = f.read()
                page.fill("textarea, [contenteditable='true']", md_text)
                insert_btn = page.locator("button:has-text('Einfügen'), button:has-text('Insert')").first
                if insert_btn.is_visible():
                    insert_btn.click()
                    time.sleep(6)

        page.screenshot(path=os.path.join(COURSE_DIR, "step3_loaded.png"))
        
        # 4. Studio -> Videoübersicht anpassen
        print("[Agent] Suche Studio Videoübersicht...")
        time.sleep(3)
        page = get_active_page(context)
        
        video_tile = page.locator("text='Videoübersicht', text='Video overview'").first
        if video_tile.is_visible():
            custom_btn = page.locator("button:has-text('Anpassen'), button:has-text('Customize'), [aria-label*='Anpassen']").first
            if custom_btn.is_visible():
                custom_btn.click()
                time.sleep(2)
                prompt_box = page.locator("textarea, input[type='text']").first
                if prompt_box.is_visible():
                    prompt_box.fill(brief_text)
                    print("[OK] Briefing eingetragen!")
                gen_btn = page.locator("button:has-text('Erstellen'), button:has-text('Generate'), button:has-text('Generieren')").first
                if gen_btn.is_visible():
                    gen_btn.click()
                    print("🚀 [OK] Video-Generierung gestartet!")
            else:
                video_tile.click()
                print("🚀 [OK] Video-Generierung gestartet!")
                
        # 5. Polling auf Fertigstellung
        print("\n⏳ [Agent] Video-Generierung läuft (ca. 3–5 Minuten)...")
        for i in range(1, 20):
            time.sleep(30)
            page = get_active_page(context)
            page.screenshot(path=os.path.join(COURSE_DIR, f"step4_gen_{i*30}s.png"))
            print(f"   ... ({i*0.5:.1f} Min verstrichen) ...")
            
            # Prüfen ob Download-Option da ist
            dl_btn = page.locator("[aria-label*='Herunterladen'], [aria-label*='Download'], button:has-text('Herunterladen')").first
            if dl_btn.is_visible():
                print("✨ [Agent] Fertiges Video erkannt! Starte Download...")
                with page.expect_download() as download_info:
                    dl_btn.click()
                download = download_info.value
                target_path = os.path.join(COURSE_DIR, "assets", "recap_video.mp4")
                download.save_as(target_path)
                print(f"[OK] Video heruntergeladen: {target_path}")
                break
                
        # Video in Kurs integrieren
        target_video = os.path.join(COURSE_DIR, "assets", "recap_video.mp4")
        if os.path.exists(target_video) and os.path.getsize(target_video) > 10000:
            print("\n🔄 [Agent] Binde Video in den Kurs ein...")
            scripts_dir = os.path.dirname(os.path.abspath(__file__))
            subprocess.run([sys.executable, os.path.join(scripts_dir, "set_recap_video.py"), os.path.join(COURSE_DIR, "course.json"), "--file", "assets/recap_video.mp4"], cwd=COURSE_DIR)
            subprocess.run([sys.executable, os.path.join(scripts_dir, "build_simulation.py"), os.path.join(COURSE_DIR, "course.json")], cwd=COURSE_DIR)
            subprocess.run([sys.executable, os.path.join(scripts_dir, "make_materials.py"), "course.sim.json"], cwd=COURSE_DIR)
            mbz_out = os.path.join(COURSE_DIR, "sicherung-moodle2-statistik-beschreibend-bgt.mbz")
            subprocess.run([sys.executable, os.path.join(scripts_dir, "build_mbz.py"), "course.sim.materialized.json", "-o", mbz_out], cwd=COURSE_DIR)
            
            spielwiese_script = os.path.join(scripts_dir, "..", "..", "moodle-spielwiese", "scripts", "spielwiese.py")
            if os.path.exists(spielwiese_script):
                subprocess.run([sys.executable, spielwiese_script, "import", mbz_out], cwd=COURSE_DIR)
                
            print("\n🎉 [ZIEL ERREICHT] Video erfolgreich eingebunden und auf der Spielwiese aktualisiert!")
            return True
            
    return False


if __name__ == "__main__":
    run_pipeline()
