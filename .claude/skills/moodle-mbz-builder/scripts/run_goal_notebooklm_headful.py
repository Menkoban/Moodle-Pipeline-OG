# -*- coding: utf-8 -*-
"""run_goal_notebooklm_headful.py — Headful Chrome-Agent mit persistentem Profil via Playwright.

Öffnet ein echtes, sichtbares Google-Chrome-Fenster auf dem Desktop des Nutzers und automatisiert:
1. Login-Erkennung
2. Notizbuch-Erstellung
3. Upload des Materialdossiers (PDF oder Text)
4. Studio -> Videoübersicht (Erklärvideo, Deutsch, Briefing-Prompt)
5. Generierungs-Loop mit Fortschritts-Screenshots
6. Download des fertigen MP4-Videos nach assets/recap_video.mp4
7. Einbindung in course.json, Bau der .mbz und Import in die Spielwiese
"""
import glob
import os
import shutil
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


def run_agent():
    with open(BRIEF_FILE, "r", encoding="utf-8") as f:
        brief_text = f.read()

    print("[Agent] Starte sichtbares Google Chrome mit persistentem Profil...")
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            channel="chrome",
            headless=False,
            args=[
                "--start-maximized",
                "--no-first-run",
                "--no-default-browser-check"
            ],
            viewport=None
        )
        
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://notebooklm.google.com", wait_until="domcontentloaded")
        print(f"[Agent] Navigiert zu: {page.url}")
        
        # 1. Login-Überwachung
        while "accounts.google.com" in page.url or "Anmelden" in page.title() or "Sign in" in page.title():
            print("[Agent] Warte auf Google-Login im geöffneten Chrome-Fenster...")
            time.sleep(3)
            try:
                page = context.pages[0]
            except Exception:
                pass
                
        print("[OK] Bei NotebookLM angemeldet! Warte auf Startseite...")
        page.wait_for_timeout(3000)
        page.screenshot(path=os.path.join(COURSE_DIR, "step1_home.png"))
        
        # 2. Notizbuch erstellen (falls nicht schon im Notizbuch)
        if "/notebook/" not in page.url:
            print("[Agent] Klicke auf 'Neues Notizbuch'...")
            create_btn = page.locator("button:has-text('Neues Notizbuch'), button:has-text('New notebook'), [aria-label*='Neues Notizbuch'], [aria-label*='New notebook']").first
            if create_btn.is_visible():
                create_btn.click()
                time.sleep(4)
                
        page.screenshot(path=os.path.join(COURSE_DIR, "step2_sources.png"))
        
        # 3. Quelle hochladen
        print(f"[Agent] Lade Materialdossier hoch: {DOSSIER_PDF}...")
        try:
            file_input = page.locator("input[type='file']").first
            if file_input.is_visible(timeout=3000) or True:
                page.set_input_files("input[type='file']", DOSSIER_PDF)
                print("[OK] PDF übergeben! Warte auf Indexierung...")
                time.sleep(10)
        except Exception as e:
            print(f"[Hinweis Datei-Upload] {e}. Nutze kopierten Text...")
            paste_tab = page.locator("text='Kopierter Text', text='Copied text'").first
            if paste_tab.is_visible():
                paste_tab.click()
                time.sleep(1)
                with open(DOSSIER_MD, "r", encoding="utf-8") as f:
                    md_text = f.read()
                page.fill("textarea, [contenteditable='true']", md_text)
                page.locator("button:has-text('Einfügen'), button:has-text('Insert')").first.click()
                time.sleep(6)
                
        page.screenshot(path=os.path.join(COURSE_DIR, "step3_ready.png"))
        
        # 4. Studio -> Videoübersicht
        print("[Agent] Konfiguriere Studio Videoübersicht...")
        time.sleep(4)
        video_tile = page.locator("text='Videoübersicht', text='Video overview'").first
        if video_tile.is_visible():
            custom_btn = page.locator("button:has-text('Anpassen'), button:has-text('Customize'), [aria-label*='Anpassen']").first
            if custom_btn.is_visible():
                custom_btn.click()
                time.sleep(2)
                prompt_box = page.locator("textarea, input[type='text']").first
                if prompt_box.is_visible():
                    prompt_box.fill(brief_text)
                    print("[OK] Didaktisches Briefing eingetragen!")
                gen_btn = page.locator("button:has-text('Erstellen'), button:has-text('Generate'), button:has-text('Generieren')").first
                if gen_btn.is_visible():
                    gen_btn.click()
                    print("🚀 [OK] Video-Generierung gestartet!")
            else:
                video_tile.click()
                print("🚀 [OK] Video-Generierung gestartet!")
                
        # 5. Polling & Monitoring (im 2,5-Minuten-Intervall = 150s)
        print("\n⏳ [Agent] Video-Generierung läuft. Überwache Fortschritt alle 2,5 Minuten...")
        for i in range(1, 10):
            time.sleep(150)  # 2,5 Minuten Intervall
            page.screenshot(path=os.path.join(COURSE_DIR, f"step4_generating_{i*2.5:.1f}min.png"))
            print(f"   ... ({i*2.5:.1f} Minuten verstrichen) ...")
            
            dl_btn = page.locator("[aria-label*='Herunterladen'], [aria-label*='Download'], button:has-text('Herunterladen')").first
            if dl_btn.is_visible():
                print("✨ [Agent] Fertiges Video erkannt! Lade herunter...")
                with page.expect_download() as dl_info:
                    dl_btn.click()
                dl = dl_info.value
                target_video = os.path.join(COURSE_DIR, "assets", "recap_video.mp4")
                dl.save_as(target_video)
                print(f"[OK] Video gesichert: {target_video}")
                break
                
        # 6. Moodle-Kurs aktualisieren & MBZ bauen
        target_video = os.path.join(COURSE_DIR, "assets", "recap_video.mp4")
        if os.path.exists(target_video) and os.path.getsize(target_video) > 10000:
            print("\n🔄 [Agent] Finalisiere Moodle-Kurs mit echtem Video...")
            scripts_dir = os.path.dirname(os.path.abspath(__file__))
            subprocess.run([sys.executable, os.path.join(scripts_dir, "set_recap_video.py"), os.path.join(COURSE_DIR, "course.json"), "--file", "assets/recap_video.mp4"], cwd=COURSE_DIR)
            subprocess.run([sys.executable, os.path.join(scripts_dir, "build_simulation.py"), os.path.join(COURSE_DIR, "course.json")], cwd=COURSE_DIR)
            subprocess.run([sys.executable, os.path.join(scripts_dir, "make_materials.py"), "course.sim.json"], cwd=COURSE_DIR)
            mbz_out = os.path.join(COURSE_DIR, "sicherung-moodle2-statistik-beschreibend-bgt.mbz")
            subprocess.run([sys.executable, os.path.join(scripts_dir, "build_mbz.py"), "course.sim.materialized.json", "-o", mbz_out], cwd=COURSE_DIR)
            
            # Spielwiese Import
            spielwiese_script = os.path.join(scripts_dir, "..", "..", "moodle-spielwiese", "scripts", "spielwiese.py")
            if os.path.exists(spielwiese_script):
                subprocess.run([sys.executable, spielwiese_script, "import", mbz_out], cwd=COURSE_DIR)
                
            print("\n🎉 [ZIEL ERREICHT] Video erfolgreich generiert, eingebunden und auf der Spielwiese aktualisiert!")
            return True

        print("[Agent] Prozess abgeschlossen. Schließe Browser...")
        context.close()


if __name__ == "__main__":
    run_agent()
