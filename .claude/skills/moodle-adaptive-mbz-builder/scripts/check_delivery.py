#!/usr/bin/env python3
"""Schluss-Gate vor der Übergabe eines Kurses: prüft, ob ALLE
Pflicht-Deliverables des Skills wirklich vorliegen. Erst bei Exit 0 wird
ausgeliefert — jede bewusste Ausnahme (z. B. Video-Platzhalter, weil kein
Browser verbunden war) muss per Flag erlaubt UND dem Autor im Chat
begründet werden.

Usage:
    python check_delivery.py <kursordner> [--allow-video-placeholder]
                                          [--allow-no-widget]

Prüft im Ordner:
  1. course.json (bzw. course.materialized.json) vorhanden, alle
     image/images/file/files-Pfade RELATIV (Ordner muss self-contained
     rebuildbar sein)
  2. genau eine .mbz, und validate_mbz.py läuft grün
  3. *_vorschau.html vorhanden
  4. editor.html vorhanden (Editor-Widget wurde gebaut)
  5. materials/ mit PDF+PPTX, wenn material:true-Seiten existieren
  6. referenzierte relative Assets existieren
  7. Video-Recap eingebaut (kein 'Videozusammenfassung'-label-Platzhalter)
  8. adaptiv (auto-erkannt an *.pathmap.json): simulate_pathways.py grün
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


def main() -> int:
    ap = argparse.ArgumentParser(description="Deliverable-Gate eines Kursordners.")
    ap.add_argument("folder")
    ap.add_argument("--allow-video-placeholder", action="store_true",
                    help="Video-Recap fehlt bewusst (kein Browser/Login) — im Chat begründen!")
    ap.add_argument("--allow-no-widget", action="store_true",
                    help="Editor-Widget fehlt bewusst — im Chat begründen!")
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
                            mbzs[0]], capture_output=True, text=True)
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

    # 5. Materialien
    n_material = sum(1 for a in walk_activities(spec) if a.get("material"))
    if n_material:
        pdfs = glob.glob(os.path.join(d, "materials", "*.pdf"))
        pptx = glob.glob(os.path.join(d, "materials", "*.pptx"))
        if len(pdfs) >= n_material and len(pptx) >= n_material:
            ok.append(f"Materialien: {len(pdfs)} PDF + {len(pptx)} PPTX "
                      f"fuer {n_material} Infoblaetter")
        else:
            fehler.append(f"materials/ unvollstaendig: {len(pdfs)} PDF/"
                          f"{len(pptx)} PPTX fuer {n_material} material:true-Seiten")
    else:
        warn.append("keine material:true-Seiten — bei einem echten Kurs unueblich")

    # 7. Video-Recap
    placeholder = [a for a in walk_activities(spec)
                   if a.get("type") == "label"
                   and "video" in a.get("name", "").lower()]
    if not placeholder:
        ok.append("Video-Recap eingebaut (kein Platzhalter-Label mehr)")
    elif args.allow_video_placeholder:
        warn.append("Video-Platzhalter noch offen (per Flag erlaubt — "
                    "Autor informiert? Video nachziehen!)")
    else:
        fehler.append("'Videozusammenfassung' ist noch Platzhalter — NotebookLM-Flow "
                      "fahren oder mit --allow-video-placeholder begruenden")

    # 8. adaptiv: Ratschen-Gate
    pathmaps = glob.glob(os.path.join(d, "*.pathmap.json"))
    sim = os.path.join(HERE, "simulate_pathways.py")
    if pathmaps and os.path.exists(sim):
        if len(mbzs) == 1:
            r = subprocess.run([sys.executable, sim, mbzs[0], pathmaps[0]],
                               capture_output=True, text=True)
            if r.returncode == 0:
                ok.append("simulate_pathways: adaptiver Pfad gruen")
            else:
                fehler.append(f"simulate_pathways FAIL:\n"
                              f"{(r.stdout + r.stderr).strip()[-800:]}")
    elif os.path.exists(sim):
        fehler.append("adaptiver Skill, aber keine *.pathmap.json im Ordner "
                      "(build_adaptive.py nicht gelaufen?)")

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
