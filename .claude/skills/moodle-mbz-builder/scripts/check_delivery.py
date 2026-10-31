#!/usr/bin/env python3
"""Schluss-Gate vor der Übergabe eines Kurses: prüft, ob ALLE
Pflicht-Deliverables des Skills wirklich vorliegen. Erst bei Exit 0 wird
ausgeliefert — jede bewusste Ausnahme (z. B. Video-Platzhalter, weil kein
Browser verbunden war) muss per Flag erlaubt UND dem Autor im Chat
begründet werden.

Usage:
    python check_delivery.py <kursordner> [--allow-video-placeholder]
                                          [--allow-no-widget]
                                          [--require-live-restore]

Prüft im Ordner:
  1. course.json (bzw. course.materialized.json) vorhanden, alle
     image/images/file/files-Pfade RELATIV (Ordner muss self-contained
     rebuildbar sein)
  2. genau eine .mbz, und validate_mbz.py läuft grün
  3. *_vorschau.html vorhanden
  4. editor.html vorhanden (Editor-Widget wurde gebaut)
  5. materials/ mit PDF+PPTX+DOCX, wenn material:true-Seiten existieren
  6. referenzierte relative Assets existieren
  7. Video-Recap eingebaut (kein 'Videozusammenfassung'-label-Platzhalter)
  8. adaptiv (auto-erkannt an *.pathmap.json): simulate_pathways.py grün
  9. Live-Restore (OPTIONAL): ist der Skill 'moodle-testinstanz' installiert,
     wird die .mbz wirklich ins lokale Moodle-Lab restauriert. Fehlt der Skill
     oder ist das Lab nicht erreichbar -> WARN + weiter (Gate bleibt grün);
     rot nur bei echtem Restore-Fehler. --require-live-restore erzwingt ihn.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ABS_RX = re.compile(r"^(?:[A-Za-z]:[/\\]|[/\\])")

# Optionaler Live-Restore-Skill (siehe docs/superpowers/specs/
# 2026-07-15-moodle-testinstanz-restore-gate-design.md). Fehlt er, laeuft das
# Gate wie bisher (nur statische Checks).
def _find_testinstanz_home():
    env_path = os.environ.get("MOODLE_TESTINSTANZ_HOME")
    if env_path and os.path.isdir(env_path):
        return env_path
    # Zuerst der Geschwisterordner im Monorepo (.claude/skills/moodle-testinstanz),
    # damit nie eine veraltete globale Installation gewinnt.
    sibling = os.path.normpath(os.path.join(HERE, "..", "..", "moodle-testinstanz"))
    candidates = [
        sibling,
        os.path.expanduser("~/.claude/skills/moodle-testinstanz"),
        os.path.expanduser("~/.gemini/config/skills/moodle-testinstanz"),
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    return sibling

TESTINSTANZ_HOME = _find_testinstanz_home()


def walk_paths(node, keys=("image", "file")):
    """Alle Pfad-Strings aus image/images/file/files-Feldern."""
    out = []
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ("image", "file") and isinstance(v, str):
                out.append(v)
            elif k in ("images", "files") and isinstance(v, list):
                out += [x for x in v if isinstance(x, str)]
            else:
                out += walk_paths(v)
    elif isinstance(node, list):
        for v in node:
            out += walk_paths(v)
    return out


def walk_activities(spec):
    for sec in spec.get("sections", []):
        for a in sec.get("activities", []):
            yield a


def live_restore_probe(mbz_path, require):
    """Optionaler dynamischer Check: echte .mbz gegen das lokale Moodle-Lab
    restaurieren. Gibt (ok, warn, fehler) zurueck. Weiches Gate:
      - Skript fehlt    -> skip (leer)          ausser --require-live-restore
      - Lab down (rc=3) -> WARN                  ausser --require-live-restore
      - Restore-Fehler  -> FEHLER (Gate rot)
    Exit-Code-Vertrag von run_restore.py:
      --health        : 0 = Lab up, 3 = Lab down/fehlt
      <mbz> [--json]  : 0 = ok, 2 = echter Restore-Fehler, 3 = Lab verloren
    """
    ok, warn, fehler = [], [], []
    runner = os.path.join(TESTINSTANZ_HOME, "scripts", "run_restore.py")
    if not os.path.exists(runner):
        if require:
            fehler.append("--require-live-restore gesetzt, aber Skill "
                          f"'moodle-testinstanz' nicht gefunden ({runner})")
        return ok, warn, fehler  # sonst still ueberspringen (Gate wie bisher)

    # Preflight: laeuft das Lab ueberhaupt?
    h = subprocess.run([sys.executable, runner, "--health"],
                       capture_output=True, text=True)
    if h.returncode != 0:
        msg = ("Moodle-Lab nicht erreichbar — Live-Restore uebersprungen "
               f"(rc={h.returncode}: {h.stdout.strip()[-200:]})")
        (fehler if require else warn).append(msg)
        return ok, warn, fehler

    # Echter Restore
    r = subprocess.run([sys.executable, runner, mbz_path, "--json"],
                       capture_output=True, text=True)
    if r.returncode == 0:
        ver = ""
        try:
            info = json.loads(r.stdout)
            ver = (f" (Moodle {info.get('moodle_version', '?')}, "
                   f"tiles={info.get('format_tiles')})")
        except Exception:
            pass
        ok.append(f"Live-Restore gruen: Kurs geht hoch{ver}")
    elif r.returncode == 3:
        (fehler if require else warn).append(
            "Lab waehrend Restore verloren — uebersprungen")
    else:  # rc == 2 (oder unerwartet) -> echter Fehler
        tail = (r.stdout + r.stderr).strip()[-800:]
        fehler.append(f"LIVE-RESTORE FAIL (Moodle lehnt .mbz ab):\n{tail}")
    return ok, warn, fehler


def main() -> int:
    ap = argparse.ArgumentParser(description="Deliverable-Gate eines Kursordners.")
    ap.add_argument("folder")
    ap.add_argument("--allow-video-placeholder", action="store_true",
                    help="Video-Recap ist noch ein Platzhalter — im Chat begründen!")
    ap.add_argument("--allow-no-video", action="store_true",
                    help="Video-Recap fehlt bewusst (kein Video & kein Platzhalter) — im Chat begründen!")
    ap.add_argument("--allow-no-widget", action="store_true",
                    help="Editor-Widget fehlt bewusst — im Chat begründen!")
    ap.add_argument("--require-live-restore", action="store_true",
                    help="Live-Restore gegen moodle-testinstanz erzwingen — "
                         "Abwesenheit/Lab-down werden dann zum Fehler.")
    args = ap.parse_args()
    d = args.folder
    fehler, warn, ok = [], [], []

    # 1. Kursdefinitionen: QUELLE (course.json) muss relativ + self-contained
    #    sein; der BUILD-STAND (course.materialized.json, abgeleitet) darf
    #    absolute Pfade der generierten Materialien enthalten und ist die
    #    Referenz fuer Material-/Video-Checks.
    src_path = os.path.join(d, "course.json")
    mat_path = os.path.join(d, "course.materialized.json")
    spec = {}
    if not os.path.exists(src_path):
        fehler.append("course.json (Quelle) fehlt — Ordner nicht rebuildbar")
    else:
        src = json.load(open(src_path, encoding="utf-8"))
        ok.append("Kursdefinition (Quelle): course.json")
        absolute = [p for p in walk_paths(src) if ABS_RX.match(p)]
        if absolute:
            fehler.append(f"{len(absolute)} ABSOLUTE Pfad(e) in course.json "
                          f"(Ordner nicht self-contained), z. B. {absolute[0]!r}")
        else:
            ok.append("alle Asset-Pfade in course.json relativ")
        # 6. referenzierte Assets existieren
        missing = [p for p in walk_paths(src)
                   if not ABS_RX.match(p) and not os.path.exists(os.path.join(d, p))]
        if missing:
            fehler.append(f"referenzierte Datei(en) fehlen: {missing[:5]}")
        spec = src
    if os.path.exists(mat_path):
        spec = json.load(open(mat_path, encoding="utf-8"))  # Build-Stand

    # 2. mbz + validate
    mbzs = glob.glob(os.path.join(d, "*.mbz"))
    if len(mbzs) != 1:
        fehler.append(f"{len(mbzs)} .mbz im Ordner — erwartet genau 1")
    else:
        r = subprocess.run([sys.executable, os.path.join(HERE, "validate_mbz.py"),
                            mbzs[0]], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode == 0:
            ok.append(f"validate_mbz: {os.path.basename(mbzs[0])} gruen")
        else:
            fehler.append(f"validate_mbz FAIL:\n{(r.stdout + r.stderr).strip()[-800:]}")

    # 3. Vorschau, 4. Editor-Widget
    if glob.glob(os.path.join(d, "*_vorschau.html")):
        ok.append("Lese-Vorschau vorhanden")
    else:
        fehler.append("*_vorschau.html fehlt (preview_mbz.py nicht gelaufen?)")
    if os.path.exists(os.path.join(d, "editor.html")):
        ok.append("Editor-Widget gebaut (editor.html)")
    elif args.allow_no_widget:
        warn.append("Editor-Widget fehlt (per Flag erlaubt — im Chat begründet?)")
    else:
        fehler.append("editor.html fehlt — build_editor_widget.py nicht gelaufen "
                      "(und Rendern via show_widget nicht vergessen!)")

    # 4b. Mathematische Formel-Qualität (validate_math_formulas.py & validate_math_symbols.py)
    val_math = os.path.join(HERE, "validate_math_formulas.py")
    if os.path.exists(val_math) and os.path.exists(src_path):
        r = subprocess.run([sys.executable, val_math, src_path], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode == 0:
            ok.append("validate_math_formulas: mathematische Typografie sauber (Brüche & Indizes)")
        else:
            warn.append(f"validate_math_formulas: {r.stdout.strip()[-300:]}")

    val_sym = os.path.join(HERE, "validate_math_symbols.py")
    svg_files = glob.glob(os.path.join(d, "assets", "*.svg"))
    if os.path.exists(val_sym) and svg_files:
        r = subprocess.run([sys.executable, val_sym] + svg_files, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode == 0:
            ok.append("validate_math_symbols: mathematische Symbole & Orientierungen fehlerfrei")
        else:
            fehler.append(f"validate_math_symbols FAIL:\n{r.stdout.strip()[-400:]}")

    # 4c. Interaktive Medien (validate_interactive_media.py)
    val_media = os.path.join(HERE, "validate_interactive_media.py")
    if os.path.exists(val_media) and os.path.exists(src_path):
        r = subprocess.run([sys.executable, val_media, src_path], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode == 0:
            ok.append("validate_interactive_media: Hotspots, Simulationen & Formulare vollständig")
        else:
            fehler.append(f"validate_interactive_media FAIL: {r.stdout.strip()[-300:]}")

    # 4d. Material-Coverage (Inbox-Primat, validate_material_coverage.py)
    val_cov = os.path.join(HERE, "validate_material_coverage.py")
    ingested_files = glob.glob(os.path.join(d, "ingested_*.json"))
    if os.path.exists(val_cov) and ingested_files and os.path.exists(src_path):
        r = subprocess.run([sys.executable, val_cov, src_path, ingested_files[0]], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode == 0:
            ok.append("validate_material_coverage: Inbox-Primat erfüllt (Aufgaben & Daten verbaut)")
        else:
            warn.append(f"validate_material_coverage: {r.stdout.strip()[-300:]}")

    # 5. Materialien
    n_material = sum(1 for a in walk_activities(spec) if a.get("material"))
    if n_material:
        pdfs = glob.glob(os.path.join(d, "materials", "*.pdf"))
        pptx = glob.glob(os.path.join(d, "materials", "*.pptx"))
        docx = glob.glob(os.path.join(d, "materials", "*.docx"))
        if (len(pdfs) >= n_material and len(pptx) >= n_material
                and len(docx) >= n_material):
            ok.append(f"Materialien: {len(pdfs)} PDF + {len(pptx)} PPTX + "
                      f"{len(docx)} DOCX fuer {n_material} Infoblaetter")
        else:
            fehler.append(f"materials/ unvollstaendig: {len(pdfs)} PDF/"
                          f"{len(pptx)} PPTX/{len(docx)} DOCX fuer "
                          f"{n_material} material:true-Seiten")
    else:
        warn.append("keine material:true-Seiten — bei einem echten Kurs unueblich")

    # 7. Video-Recap (Härtung: echtes Video vs. Platzhalter vs. Fehlen)
    real_video = [a for a in walk_activities(spec)
                  if (a.get("type") in ("resource", "url") and "video" in (a.get("name") or "").lower())
                  or (a.get("type") == "resource" and str(a.get("file", "")).lower().endswith((".mp4", ".webm", ".m4v")))
                  or (a.get("type") == "url" and "notebooklm.google.com" in str(a.get("externalurl", "")))]
    placeholder = [a for a in walk_activities(spec)
                   if a.get("type") in ("label", "page")
                   and "video" in (a.get("name") or "").lower()]

    if real_video:
        vid = real_video[0]
        ref = vid.get("file") or vid.get("externalurl") or vid.get("name")
        if vid.get("type") == "resource" and vid.get("file"):
            fpath = os.path.join(d, vid["file"]) if not ABS_RX.match(vid["file"]) else vid["file"]
            if not os.path.exists(fpath):
                fehler.append(f"Video-Ressource verlinkt Datei, die nicht existiert: {vid['file']}")
            else:
                sz_mb = os.path.getsize(fpath) / (1024 * 1024)
                ok.append(f"Video-Recap eingebaut: {vid.get('name')} ({vid['file']}, {sz_mb:.2f} MB)")
        else:
            ok.append(f"Video-Recap eingebaut: {vid.get('name')} ({ref})")
    elif placeholder:
        if args.allow_video_placeholder or args.allow_no_video:
            warn.append("Video-Platzhalter noch offen (per Flag erlaubt — "
                        "Autor informiert? Video nachziehen!)")
        else:
            fehler.append("Video-Recap ist noch ein Platzhalter — Gate 6 (NotebookLM-Flow) "
                          "fahren oder mit --allow-video-placeholder begründen")
    else:
        # Weder echtes Video noch Platzhalter vorhanden
        if args.allow_video_placeholder or args.allow_no_video:
            warn.append("Kein Video-Recap im Kurs vorhanden (per Flag erlaubt)")
        else:
            fehler.append("Kein Video-Recap und kein Platzhalter gefunden! "
                          "Ein vollwertiger Kurs verlangt im Kurs-Recap ein Video-Recap. "
                          "Gate 6 (NotebookLM Video-Recap mit ask_question) MUSS durchlaufen werden "
                          "oder mit --allow-video-placeholder begründet werden.")

    # 8. adaptiv: Ratschen-Gate
    pathmaps = glob.glob(os.path.join(d, "*.pathmap.json"))
    sim = os.path.join(HERE, "simulate_pathways.py")
    if pathmaps and os.path.exists(sim):
        if len(mbzs) == 1:
            r = subprocess.run([sys.executable, sim, mbzs[0], pathmaps[0]],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            if r.returncode == 0:
                ok.append("simulate_pathways: adaptiver Pfad gruen")
            else:
                fehler.append(f"simulate_pathways FAIL:\n"
                              f"{(r.stdout + r.stderr).strip()[-800:]}")
    elif os.path.exists(sim):
        fehler.append("adaptiver Skill, aber keine *.pathmap.json im Ordner "
                      "(build_adaptive.py nicht gelaufen?)")

    # 9. Live-Restore (optional, nur wenn Skill moodle-testinstanz vorhanden)
    if len(mbzs) == 1:
        lok, lwarn, lfehler = live_restore_probe(mbzs[0], args.require_live_restore)
        ok += lok
        warn += lwarn
        fehler += lfehler
    elif args.require_live_restore:
        fehler.append("--require-live-restore, aber keine eindeutige .mbz im Ordner")

    enc = dict(encoding="utf-8", errors="replace")
    out = open(sys.stdout.fileno(), "w", closefd=False, **enc)
    for line in ok:
        out.write(f"  ok:     {line}\n")
    for line in warn:
        out.write(f"  WARN:   {line}\n")
    for line in fehler:
        out.write(f"  FEHLER: {line}\n")
    if fehler:
        out.write("GATE ROT: NICHT ausliefern — erst beheben (oder Ausnahme "
                  "per Flag + Begruendung im Chat).\n")
        return 1
    out.write("GATE GRUEN: alle Pflicht-Deliverables vorhanden — ausliefern.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
