#!/usr/bin/env python3
"""Material Ingestion Engine for Moodle MBZ Builder & Grill-Me.

Parses existing educational documents and media files (PDF, DOCX, PNG, JPG, MP4, MP3),
extracts text, headings, tables, embedded images, diagrams and audio/video metadata,
and structures them into candidate sections, Infoblätter, glossary entries and activities
ready for Moodle course generation and Grill-Me intake.

Usage:
    python ingest_material.py <file_or_dir> [-o output.json] [--media-dir assets/]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Optional imports for document parsing
try:
    import docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    try:
        import pypdf
        HAS_PYPDF = True
        HAS_FITZ = False
    except ImportError:
        HAS_PYPDF = False
        HAS_FITZ = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def extract_text_from_docx(file_path: str, media_dir: Optional[str] = None) -> Dict[str, Any]:
    """Extrahiert Absätze, Überschriften, Tabellen und Bilder aus einer .docx-Datei."""
    if not HAS_DOCX:
        return {"error": "python-docx nicht installiert", "file": file_path}

    try:
        doc = docx.Document(file_path)
    except Exception as e:
        return {"error": f"Fehler beim Öffnen der DOCX: {e}", "file": file_path, "type": "docx"}

    result = {
        "file": file_path,
        "type": "docx",
        "title": Path(file_path).stem,
        "headings": [],
        "paragraphs": [],
        "tables": [],
        "bullet_points": [],
        "extracted_images": [],
        "raw_text": ""
    }

    raw_lines = []
    current_heading = ""

    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            continue
        raw_lines.append(text)
        style_name = p.style.name.lower() if p.style else ""

        if "heading 1" in style_name or "überschrift 1" in style_name:
            current_heading = text
            result["headings"].append({"level": 1, "text": text})
        elif "heading 2" in style_name or "überschrift 2" in style_name:
            result["headings"].append({"level": 2, "text": text, "parent": current_heading})
        elif "heading 3" in style_name or "überschrift 3" in style_name:
            result["headings"].append({"level": 3, "text": text, "parent": current_heading})
        elif "list" in style_name or text.startswith(("-", "•", "*", "1.", "2.", "3.")):
            result["bullet_points"].append(text)
        else:
            result["paragraphs"].append({
                "heading": current_heading,
                "text": text
            })

    # Extract tables
    for t in doc.tables:
        table_data = []
        for row in t.rows:
            row_data = [cell.text.strip() for cell in row.cells]
            table_data.append(row_data)
        if table_data:
            result["tables"].append(table_data)

    # Extract embedded images if media_dir is provided
    if media_dir:
        os.makedirs(media_dir, exist_ok=True)
        img_idx = 1
        for rel in doc.part.rels.values():
            if "image" in rel.target_ref:
                try:
                    img_data = rel.target_part.blob
                    img_ext = Path(rel.target_ref).suffix or ".png"
                    img_name = f"{Path(file_path).stem}_img_{img_idx}{img_ext}"
                    img_out = os.path.join(media_dir, img_name)
                    with open(img_out, "wb") as f_img:
                        f_img.write(img_data)
                    result["extracted_images"].append(img_out)
                    img_idx += 1
                except Exception:
                    pass

    result["raw_text"] = "\n\n".join(raw_lines)
    return result


def extract_text_from_pdf(file_path: str, media_dir: Optional[str] = None) -> Dict[str, Any]:
    """Extrahiert Text, Seiten und Bilder aus einer PDF-Datei."""
    result = {
        "file": file_path,
        "type": "pdf",
        "title": Path(file_path).stem,
        "pages": [],
        "extracted_images": [],
        "raw_text": "",
        "bullet_points": [],
        "headings": []
    }

    if HAS_FITZ:
        try:
            doc = fitz.open(file_path)
        except Exception as e:
            return {"error": f"Fehler beim Öffnen der PDF: {e}", "file": file_path, "type": "pdf"}
        all_text = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            all_text.append(text)
            result["pages"].append({
                "page_number": page_num + 1,
                "text": text.strip()
            })

            # Extract images if media_dir is provided
            if media_dir:
                os.makedirs(media_dir, exist_ok=True)
                for img_idx, img in enumerate(page.get_images(full=True)):
                    try:
                        xref = img[0]
                        base_img = doc.extract_image(xref)
                        img_bytes = base_img["image"]
                        img_ext = base_img["ext"]
                        img_name = f"{Path(file_path).stem}_p{page_num+1}_img_{img_idx+1}.{img_ext}"
                        img_out = os.path.join(media_dir, img_name)
                        with open(img_out, "wb") as f_img:
                            f_img.write(img_bytes)
                        result["extracted_images"].append(img_out)
                    except Exception:
                        pass

        result["raw_text"] = "\n\n--- PAGE BREAK ---\n\n".join(all_text)

    elif HAS_PYPDF:
        import pypdf
        reader = pypdf.PdfReader(file_path)
        all_text = []
        for page_num, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            all_text.append(text)
            result["pages"].append({
                "page_number": page_num + 1,
                "text": text.strip()
            })
        result["raw_text"] = "\n\n--- PAGE BREAK ---\n\n".join(all_text)
    else:
        return {"error": "Weder PyMuPDF (fitz) noch pypdf installiert", "file": file_path}

    # Extract rough headings and bullet points from lines
    lines = [l.strip() for l in result["raw_text"].split("\n") if l.strip()]
    for l in lines:
        if l.startswith(("-", "•", "*", "–", "→")):
            result["bullet_points"].append(l)
        elif len(l) < 60 and not l.endswith((".", ":", ";", ",")) and not l.isdigit():
            # Potential heading candidate
            result["headings"].append({"level": 2, "text": l})

    return result


def extract_image_metadata(file_path: str) -> Dict[str, Any]:
    """Liest Bildmetadaten ein (Dimensionen, Format, Farbraum)."""
    result = {
        "file": file_path,
        "type": "image",
        "filename": os.path.basename(file_path),
        "extension": Path(file_path).suffix.lower(),
        "width": 0,
        "height": 0,
        "aspect_ratio": "unknown",
        "role_recommendation": "diagram"
    }

    if HAS_PIL and result["extension"] in [".png", ".jpg", ".jpeg", ".webp", ".gif"]:
        try:
            with Image.open(file_path) as img:
                w, h = img.size
                result["width"] = w
                result["height"] = h
                ratio = w / h if h > 0 else 1.0
                if 1.6 <= ratio <= 1.9:
                    result["aspect_ratio"] = "16:9"
                    result["role_recommendation"] = "kachel_cover"
                elif 1.2 <= ratio <= 1.5:
                    result["aspect_ratio"] = "4:3"
                    result["role_recommendation"] = "infoblatt_diagramm"
                else:
                    result["aspect_ratio"] = f"{ratio:.2f}"
                    result["role_recommendation"] = "hotspot_base_or_diagram"
        except Exception:
            pass

    return result


def extract_media_metadata(file_path: str) -> Dict[str, Any]:
    """Liest Audio/Video-Dateimetadaten ein."""
    ext = Path(file_path).suffix.lower()
    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    media_type = "video" if ext in [".mp4", ".webm", ".mov"] else "audio"

    return {
        "file": file_path,
        "filename": os.path.basename(file_path),
        "type": media_type,
        "extension": ext,
        "size_mb": round(size_mb, 2),
        "moodle_wiring": "resource" if size_mb > 50 else "embedded_html5",
        "suggested_activity": {
            "type": "page" if media_type == "video" else "resource",
            "name": f"{'Video' if media_type == 'video' else 'Audio'}: {Path(file_path).stem.replace('_', ' ').title()}",
            "file": file_path
        }
    }


def structure_curriculum_and_content(extracted_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Führt extrahierte Dokumente zu einem vorläufigen didaktischen Roh-Steckbrief zusammen."""
    combined_text = "\n\n".join([d.get("raw_text", "") for d in extracted_docs if "raw_text" in d])
    
    # 1. Erkennung von Fachbegriffen & Glossar-Kandidaten
    glossary_candidates = []
    matches = re.findall(r"(?:^|\n)([A-ZÄÖÜ][A-Za-z0-9\s\-]{3,30}):\s+([^\n]{15,200})", combined_text)
    for term, definition in matches[:15]:
        glossary_candidates.append({
            "concept": term.strip(),
            "definition": definition.strip()
        })

    # 2. Erkennung von Berechnungen & Formeln
    formula_candidates = []
    form_matches = re.findall(r"([A-Za-z]\s*=\s*[^;\n]{3,40})", combined_text)
    for f in form_matches[:8]:
        formula_candidates.append(f.strip())

    # 3. Normen & Vorschriften (DIN, ISO, EN, VDE, DGUV, TRGS, §)
    norm_matches = re.findall(r"(DIN\s+[A-Z0-9\s\-]+|ISO\s+[0-9]+|DIN\s+EN\s+ISO\s+[0-9\-]+|VDE\s+[0-9]+|DGUV\s+[A-Za-z0-9\s]+|§\s*\d+\s*[A-Za-z]+)", combined_text)
    norm_candidates = list(set([n.strip() for n in norm_matches]))

    # 4. Gliederung in Themen-Phasen
    all_headings = []
    for d in extracted_docs:
        for h in d.get("headings", []):
            if h.get("text") and len(h.get("text")) > 3:
                all_headings.append(h.get("text"))

    return {
        "source_files": [d.get("file") for d in extracted_docs],
        "extracted_glossary": glossary_candidates,
        "extracted_formulas": formula_candidates,
        "extracted_norms": norm_candidates,
        "raw_heading_outline": all_headings[:10],
        "total_word_count": len(combined_text.split())
    }


def ingest_materials(paths: List[str], media_dir: Optional[str] = "assets") -> Dict[str, Any]:
    """Haupt-Einstiegspunkt: Verarbeitet eine Liste von Dateien oder Verzeichnissen."""
    all_files = []
    for p in paths:
        if os.path.isdir(p):
            for root, _, files in os.walk(p):
                for f in files:
                    all_files.append(os.path.join(root, f))
        elif os.path.exists(p):
            all_files.append(p)

    docs = []
    images = []
    media = []

    for f in all_files:
        ext = Path(f).suffix.lower()
        if ext == ".docx":
            docs.append(extract_text_from_docx(f, media_dir))
        elif ext == ".pdf":
            docs.append(extract_text_from_pdf(f, media_dir))
        elif ext in [".png", ".jpg", ".jpeg", ".webp", ".svg"]:
            images.append(extract_image_metadata(f))
        elif ext in [".mp4", ".mp3", ".webm", ".mov", ".wav"]:
            media.append(extract_media_metadata(f))

    synthesis = structure_curriculum_and_content(docs)

    return {
        "status": "success",
        "documents": docs,
        "images": images,
        "media": media,
        "synthesis": synthesis
    }


def main():
    parser = argparse.ArgumentParser(description="Unterrichtsmaterialien (PDF, DOCX, Bilder, Audio/Video) für Moodle einlesen.")
    parser.add_argument("inputs", nargs="*", help="Dateien oder Ordner mit Unterrichtsmaterialien (Default: auto-scan _inbox/)")
    parser.add_argument("-o", "--output", default="ingested_materials.json", help="Ausgabedatei für strukturiertes JSON")
    parser.add_argument("--media-dir", default="assets", help="Zielverzeichnis für extrahierte Bilder/Medien")

    args = parser.parse_args()
    inputs = args.inputs
    if not inputs:
        # Default inbox locations
        candidates = [
            "_inbox",
            r"C:\Users\User\OneDrive - HSOS\Desktop\Moodle-Kurse\_inbox",
            "quellen"
        ]
        inputs = [c for c in candidates if os.path.isdir(c) and os.listdir(c)]
        if not inputs:
            print("Hinweis: Keine Eingabedateien angegeben und _inbox/ ist leer. Bitte Dateien in '_inbox/' ablegen oder Pfad übergeben.")
            sys.exit(0)

    data = ingest_materials(inputs, args.media_dir)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"OK: {len(data['documents'])} Dokument(e), {len(data['images'])} Bild(er), {len(data['media'])} Mediendatei(en) eingelesen -> {args.output}")


if __name__ == "__main__":
    main()
