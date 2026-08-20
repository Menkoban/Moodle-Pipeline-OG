#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch_curriculum.py — Curriculares Live-Retrieval & Extraktions-CLI für moodle-kurs-grill-me.

Holt, validiert, extrahiert und strukturiert offizielle KMK-Rahmenlehrpläne
und CuVo-Vorgaben für die berufliche Moodle-Kurserstellung.

Nutzung:
  # 1. Im Cache prüfen & alle Lernfelder auflisten:
  python fetch_curriculum.py --beruf "Elektroniker für Betriebstechnik" --check-cache

  # 2. Spezifisches Lernfeld abrufen (aus Cache oder URL):
  python fetch_curriculum.py --beruf "Elektroniker" --url "https://www.kmk.org/fileadmin/Dateien/pdf/Bildung/BeruflicheBildung/rlp/Elektroniker-20-12-18-mEL.pdf" --lernfeld 3

  # 3. Lokales Nutzer-PDF einbinden:
  python fetch_curriculum.py --beruf "Metallbauer" --pdf "C:/pfad/rlp_metall.pdf" --lernfeld 2

  # 4. JSON-Export für den Grillmaster-Steckbrief:
  python fetch_curriculum.py --beruf "Fachinformatiker" --lernfeld 1 --json-out curriculum_data.json
"""
import argparse
import datetime
import json
import os
import sys
from pathlib import Path

# Einbindung der geteilten Module
SHARED_DIR = Path(__file__).resolve().parent.parent.parent / "shared"
sys.path.insert(0, str(SHARED_DIR))

from pipeline_common import slugify  # noqa: E402
from retrieval import (OFFICIAL_DOMAINS, build_meta_header, cache_lookup,  # noqa: E402
                       detect_beschluss, detect_stand, extract_text,
                       fetch_document, isolate_lernfeld, parse_meta_header)
from curriculum_parser import (parse_lernfeld_full,  # noqa: E402
                               parse_all_lernfelder_from_document)

# Zentraler Cache-Pfad
CACHE_DIR = SHARED_DIR / "cache"

# Windows UTF-8 Konsolenfix
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")


def _out(obj: dict, code: int) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False))
    sys.exit(code)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--beruf", required=True, help="Name des Ausbildungsberufs")
    parser.add_argument("--lernfeld", type=int, default=None, help="Lernfeld-Nummer (z.B. 1, 3)")
    parser.add_argument("--url", help="PDF-URL einer offiziellen Quelle (kmk.org, nibis.de, etc.)")
    parser.add_argument("--pdf", help="Pfad zu lokalem PDF (Nutzer-Upload)")
    parser.add_argument("--stand", help="Stand/Jahr des RLP (optional)")
    parser.add_argument("--check-cache", action="store_true", help="Nur Cache abfragen")
    parser.add_argument("--json-out", help="Optionaler Ausgabepfad für JSON-Datei")
    
    args = parser.parse_args()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    slug = slugify(args.beruf)
    today = datetime.date.today().isoformat()
    
    doc_text = ""
    quelle_url = ""
    stand = args.stand or "unbekannt"
    beschluss_vom = ""
    cache_file = None
    
    # 1. Cache-Prüfung
    cached = cache_lookup(CACHE_DIR, slug)
    
    if args.check_cache or (cached and not args.url and not args.pdf):
        if not cached:
            _out({
                "status": "cache_miss",
                "beruf": args.beruf,
                "beruf_slug": slug,
                "hinweis": "Kein RLP im Cache. Bitte offizielle URL (--url) oder PDF (--pdf) übergeben."
            }, 5)
            
        doc_text = cached.read_text(encoding="utf-8")
        meta = parse_meta_header(doc_text)
        stand = meta.get("stand") or cached.stem.rsplit("-", 1)[-1]
        quelle_url = meta.get("quelle_url", "Cache")
        beschluss_vom = meta.get("beschluss_vom", "")
        cache_file = str(cached)
        
    # 2. Lokales Nutzer-PDF
    elif args.pdf:
        pdf_path = Path(args.pdf)
        if not pdf_path.exists():
            _out({"status": "datei_nicht_gefunden", "pfad": str(pdf_path)}, 3)
            
        try:
            doc_text = extract_text(pdf_path)
        except Exception as e:
            _out({"status": "extraktion_fehlgeschlagen", "fehler": str(e)}, 3)
            
        if len(doc_text.strip()) < 1000:
            _out({
                "status": "extraktion_unbrauchbar",
                "hinweis": "PDF enthält weniger als 1000 Zeichen Text. Vermutlich Scan ohne Textlayer."
            }, 3)
            
        stand = args.stand or detect_stand(doc_text)
        beschluss_vom = detect_beschluss(doc_text)
        quelle_url = f"Nutzer-Upload: {pdf_path.name}"
        
        # Im Cache sichern
        md_path = CACHE_DIR / f"rlp-{slug}-{stand}.md"
        meta_hdr = build_meta_header({
            "beruf": args.beruf,
            "quelle_url": quelle_url,
            "abgerufen_am": today,
            "stand": stand,
            "beschluss_vom": beschluss_vom
        })
        md_path.write_text(meta_hdr + doc_text, encoding="utf-8")
        cache_file = str(md_path)

    # 3. Offizieller Download
    elif args.url:
        try:
            res = fetch_document(args.beruf, args.url, CACHE_DIR, stand=args.stand or "")
            doc_text = res["text"]
            stand = res["stand"]
            beschluss_vom = res["beschluss_vom"]
            quelle_url = args.url
            cache_file = str(res["md"])
        except ValueError as e:
            _out({
                "status": "quelle_nicht_zulaessig_oder_unbrauchbar",
                "fehler": str(e),
                "erlaubte_domains": list(OFFICIAL_DOMAINS)
            }, 2)
        except Exception as e:
            _out({"status": "download_fehlgeschlagen", "url": args.url, "fehler": str(e)}, 3)
            
    else:
        _out({
            "status": "keine_quelle",
            "hinweis": "Bitte --url, --pdf oder --check-cache angeben."
        }, 2)

    # 4. Semantische Extraktion
    alle_lf = parse_all_lernfelder_from_document(doc_text)
    
    # Übersicht der Lernfelder für schnelles Matching
    lf_overview = [
        {
            "nr": lf["lernfeld_nr"],
            "titel": lf["lernfeld_titel"],
            "zeitrichtwert_ustd": lf["zeitrichtwert_ustd"],
            "ausbildungsjahr": lf["ausbildungsjahr"]
        }
        for lf in alle_lf
    ]
    
    ziel_lf = None
    if args.lernfeld is not None:
        # Suche spezifisches Lernfeld
        for lf in alle_lf:
            if lf["lernfeld_nr"] == args.lernfeld:
                ziel_lf = lf
                break
                
        if not ziel_lf:
            # Fallback: Versuche direkte Isolation
            isolated_block = isolate_lernfeld(doc_text, args.lernfeld)
            if isolated_block:
                ziel_lf = parse_lernfeld_full(isolated_block)
                ziel_lf["lernfeld_nr"] = args.lernfeld
            else:
                _out({
                    "status": "lernfeld_nicht_gefunden",
                    "gesuchtes_lernfeld": args.lernfeld,
                    "verfuegbare_lernfelder": lf_overview,
                    "cache_datei": cache_file
                }, 4)
                
    response_data = {
        "status": "ok",
        "beruf": args.beruf,
        "stand": stand,
        "beschluss_vom": beschluss_vom,
        "quelle_url": quelle_url,
        "abgerufen_am": today,
        "cache_datei": cache_file,
        "anzahl_lernfelder_gesamt": len(alle_lf),
        "lernfelder_uebersicht": lf_overview,
        "ausgewaehltes_lernfeld": ziel_lf
    }
    
    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(response_data, f, indent=2, ensure_ascii=False)
            
    _out(response_data, 0)


if __name__ == "__main__":
    main()
