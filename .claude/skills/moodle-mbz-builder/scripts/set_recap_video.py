#!/usr/bin/env python3
"""Ersetzt den 'Videozusammenfassung'-Platzhalter (die NotebookLM-Leerstelle im
Kurs-Recap) durch das fertige Video – als Datei-Ressource (heruntergeladenes
MP4/Audio) ODER als URL (NotebookLM-Teilen-Link).

So wird aus dem manuellen NotebookLM-Ergebnis ein Ein-Schritt-Einbau:
    python set_recap_video.py course.json --url  https://notebooklm.google.com/notebook/…
    python set_recap_video.py course.json --file "C:/…/recap.mp4"
Danach normal bauen (build_simulation? -> make_materials -> build_mbz).

Findet den Platzhalter über den Aktivitätsnamen (enthält 'video' bzw.
'zusammenfassung', Typ label/page/url/resource) und ersetzt ihn an Ort und
Stelle. Schreibt zurück in dieselbe Datei (oder -o)."""
import argparse, json, os, re, sys


def is_placeholder(a):
    name = (a.get("name") or "").lower()
    if a.get("type") not in ("label", "page", "url", "resource"):
        return False
    return ("video" in name) or ("zusammenfassung" in name and "video" in
            ((a.get("intro", "") + a.get("content", "")).lower() + name))


def main():
    ap = argparse.ArgumentParser(description="Recap-Video (NotebookLM) in den Kurs einbauen.")
    ap.add_argument("course_json")
    ap.add_argument("--url", help="Öffentlicher Link zum Video/zur Audioübersicht")
    ap.add_argument("--file", help="Pfad zur heruntergeladenen MP4/Audio-Datei")
    ap.add_argument("--name", default="Videozusammenfassung")
    ap.add_argument("-o", "--output")
    args = ap.parse_args()
    if not args.url and not args.file:
        sys.exit("Bitte --url ODER --file angeben.")
    if args.file and not os.path.exists(args.file):
        sys.exit(f"Datei nicht gefunden: {args.file}")

    spec = json.load(open(args.course_json, encoding="utf-8"))
    if args.url:
        new = {"type": "url", "name": args.name,
               "intro": "<p>🎬 Kurze Videozusammenfassung der wichtigsten Punkte (NotebookLM).</p>",
               "externalurl": args.url, "completion": 1}
    else:
        new = {"type": "resource", "name": args.name,
               "intro": "<p>🎬 Kurze Videozusammenfassung der wichtigsten Punkte (NotebookLM).</p>",
               "file": args.file, "completion": 1}

    replaced = 0
    for sec in spec.get("sections", []):
        for i, a in enumerate(sec.get("activities", [])):
            if is_placeholder(a):
                sec["activities"][i] = new
                replaced += 1
    if not replaced:
        sys.exit("Kein 'Videozusammenfassung'-Platzhalter gefunden. Nichts geändert.")

    out = args.output or args.course_json
    json.dump(spec, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    kind = "URL" if args.url else "Datei"
    print(f"{replaced} Platzhalter durch {kind}-Video ersetzt -> {out}")
    print("Jetzt neu bauen: make_materials -> build_mbz -> validate -> preview")


if __name__ == "__main__":
    main()
