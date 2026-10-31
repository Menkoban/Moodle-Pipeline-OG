# -*- coding: utf-8 -*-
"""retrieval.py — wiederverwendbare Beschaffungs-Logik für curriculare/
normative Quellen (Spec §2.4). Extrahiert aus Skill 1 (fetch_rlp.py); dessen
CLI bleibt als dünner Wrapper bestehen.

Kern-Garantien:
  * NUR offizielle Quellen (Domain-Whitelist) — Verlage/Foren/Blogs verboten
  * Cache-first: einmal beschaffte Dokumente werden wiederverwendet
  * Cache-MDs tragen einen <!-- rlp-meta -->-Header (Quelle, Datum, Stand)
  * Kein Weiterarbeiten mit unbrauchbarer Extraktion (Scan ohne Textlayer)
"""
from __future__ import annotations

import datetime
import re
import sys
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline_common import slugify  # noqa: E402

OFFICIAL_DOMAINS = (
    "kmk.org",
    "nibis.de",           # deckt cuvo.nibis.de, schucu-bbs.nibis.de ab
    "mk.niedersachsen.de",
    "niedersachsen.de",
    "bibb.de",
    "gesetze-im-internet.de",
)

MIN_TEXT_CHARS = 1000  # darunter: vermutlich Scan ohne Textlayer
META_RE = re.compile(r"<!-- rlp-meta\n(.*?)\n-->", re.DOTALL)
USER_AGENT = "Mozilla/5.0 (unterrichtsplanung-pipeline)"  # cuvo blockt Nicht-Browser-UAs


def is_official(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in OFFICIAL_DOMAINS)


def download(url: str, dest: Path) -> None:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=60) as resp:
        data = resp.read()
    if not data.startswith(b"%PDF"):
        raise ValueError("Antwort ist kein PDF (Magic-Bytes fehlen)")
    dest.write_bytes(data)


def extract_text(pdf_path: Path) -> str:
    try:
        import pdfplumber
        with pdfplumber.open(str(pdf_path)) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
        return "\n\n".join(pages)
    except ImportError:
        from pypdf import PdfReader  # Fallback
        reader = PdfReader(str(pdf_path))
        return "\n\n".join((p.extract_text() or "") for p in reader.pages)


def detect_stand(text: str) -> str:
    m = re.search(r"Beschluss\s+der\s+(?:Kultusministerkonferenz|KMK)\s+vom\s+"
                  r"(\d{1,2}\.\d{1,2}\.(\d{4}))", text)
    if m:
        return m.group(2)
    m = re.search(r"Stand[:\s]+(\d{1,2}\.\d{1,2}\.)?(\d{4})", text)
    return m.group(2) if m else "unbekannt"


def detect_beschluss(text: str) -> str:
    m = re.search(r"Beschluss\s+der\s+(?:Kultusministerkonferenz|KMK)\s+vom\s+"
                  r"(\d{1,2}\.\d{1,2}\.\d{4})", text)
    return m.group(1) if m else ""


def isolate_lernfeld(text: str, nr: int) -> str:
    """Block 'Lernfeld <nr> … bis vor das nächste Lernfeld'; längstes Match,
    um Treffer in Übersichtstabellen zu überspringen."""
    starts = [m.start() for m in re.finditer(
        rf"(?im)^\s*Lernfeld\s+{nr}\s*[:\n]", text)]
    if not starts:
        starts = [m.start() for m in re.finditer(rf"(?i)Lernfeld\s+{nr}\b", text)]
    if not starts:
        return ""
    blocks = []
    for s in starts:
        nxt = re.search(rf"(?im)^\s*Lernfeld\s+{nr + 1}\s*[:\n]", text[s + 10:])
        end = s + 10 + nxt.start() if nxt else min(len(text), s + 12000)
        blocks.append(text[s:end].strip())
    return max(blocks, key=len)


def build_meta_header(meta: dict) -> str:
    lines = "\n".join(f"{k}: {v}" for k, v in meta.items())
    return f"<!-- rlp-meta\n{lines}\n-->\n\n"


def parse_meta_header(text: str) -> dict:
    m = META_RE.search(text)
    if not m:
        return {}
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta


def cache_lookup(cache_dir: Path, slug: str):
    hits = sorted(Path(cache_dir).glob(f"rlp-{slug}-*.md"))
    return hits[-1] if hits else None


def fetch_document(beruf: str, url: str, cache_dir: Path,
                   stand: str = "") -> dict:
    """Offizielle PDF laden, extrahieren, in cache_dir ablegen (PDF + MD mit
    Meta-Header). Wirft ValueError bei nicht-offizieller Quelle oder
    unbrauchbarer Extraktion."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    if not is_official(url):
        raise ValueError(f"Quelle nicht offiziell: {url} "
                         f"(erlaubt: {', '.join(OFFICIAL_DOMAINS)})")
    slug = slugify(beruf)
    tmp_pdf = cache_dir / f"rlp-{slug}-download.pdf"
    download(url, tmp_pdf)
    text = extract_text(tmp_pdf)
    if len(text.strip()) < MIN_TEXT_CHARS:
        raise ValueError("Extraktion unbrauchbar — vermutlich gescanntes PDF "
                         f"ohne Textlayer ({len(text.strip())} Zeichen)")
    stand = stand or detect_stand(text)
    pdf_path = cache_dir / f"rlp-{slug}-{stand}.pdf"
    tmp_pdf.replace(pdf_path)
    md_path = cache_dir / f"rlp-{slug}-{stand}.md"
    header = build_meta_header({
        "beruf": beruf, "quelle_url": url,
        "abgerufen_am": datetime.date.today().isoformat(),
        "stand": stand, "beschluss_vom": detect_beschluss(text)})
    md_path.write_text(header + text, encoding="utf-8")
    return {"pdf": pdf_path, "md": md_path, "stand": stand,
            "beschluss_vom": detect_beschluss(text), "text": text}
