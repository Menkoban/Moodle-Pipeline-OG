# -*- coding: utf-8 -*-
"""pipeline_common.py — geteilte Helfer der Unterrichtsplanungs-Pipeline.

Single Source of Truth für Ablage-Konvention, Namensbildung und den
Daten-Kontrakt (schema_version), damit Skill 1, Skill 2 … nicht driften.

Die Pipeline-Skills liegen zusammen unter `skills/`; dieses Modul liegt in
`skills/shared/`. Ein build_docx-Skript bindet es so ein:

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "shared"))
    from pipeline_common import safe_name, find_desktop, fallakte_ordner, SCHEMA_VERSION

Bei separater Installation nach ~/.claude/skills/ muss `shared`
mitinstalliert werden (Geschwister der Skill-Ordner bleiben).
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

# --- Daten-Kontrakt ---------------------------------------------------------
SCHEMA_VERSION = "1.0"          # Major.Minor; Skill 2 prüft die Major-Version
SCHEMA_MAJOR = int(SCHEMA_VERSION.split(".")[0])
PIPELINE_VERSION = "1.0"        # erscheint in jeder docx-Fusszeile
PROJEKT_TITEL = "Agentische Unterrichtsplanungs-Pipeline (BBS Niedersachsen)"

FALLAKTE_WURZEL = "Unterrichtsplanung"

# Zweck-Unterordner im Lernfeld-Ordner (D-18); 00-Gesamtentwurf liegt direkt im LF-Ordner
UO_PLANUNG = "01 Planung (Word)"     # die 17 Begutachtungs-Dokumente
UO_MATERIAL = "02 Material"          # Arbeitsblaetter, Hilfen, Boegen
UO_QUELLEN = "03 Quellen"            # RLP-PDF + Lernfeld-Auszug
UO_DATEN = "04 Pipeline-Daten"       # json + md der Kette (maschinenlesbar)


def check_schema_version(meta: dict, erwartete_major: int = SCHEMA_MAJOR):
    """Gibt (status, detail) zurück: status ∈ {'ok','warn','error'}."""
    v = str((meta or {}).get("schema_version", "")).strip()
    if not v:
        return ("warn", "schema_version fehlt – wird als %s behandelt" % SCHEMA_VERSION)
    major = v.split(".")[0]
    if major.isdigit() and int(major) == erwartete_major:
        return ("ok", v)
    return ("error", "inkompatible schema_version %r (erwartet %d.x)" % (v, erwartete_major))


# --- Namensbildung ----------------------------------------------------------
def slugify(text: str, maxlen: int = 60) -> str:
    """ASCII-Slug (a-z0-9-), z. B. für technische Dateinamen."""
    text = unicodedata.normalize("NFKD", text or "")
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-")
    return re.sub(r"-{2,}", "-", text)[:maxlen].rstrip("-").lower() or "analyse"


def safe_name(text: str, maxlen: int = 120) -> str:
    """Lesbarer, Windows-tauglicher Ordner-/Dateiname (Umlaute bleiben)."""
    text = (text or "").replace("/", "-")
    text = re.sub(r'[<>:"\\|?*]', "", text)        # unter Windows verbotene Zeichen
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"-{2,}", "-", text)             # doppelte Bindestriche (z. B. aus "/-in")
    return (text.strip().strip(". ")[:maxlen].strip().strip(". ") or "Analyse")


# --- Ablage -----------------------------------------------------------------
def find_desktop() -> Path:
    home = Path.home()
    candidates = sorted(home.glob("OneDrive*/Desktop")) + [home / "Desktop"]
    for c in candidates:
        if c.is_dir():
            return c
    return home


def fallakte_ordner(beruf: str, lernfeld_nr, lernfeld_titel: str,
                    desktop: Path | None = None) -> Path:
    """Gemeinsamer Lernfeld-Ordner aller Pipeline-Stufen:
    <Desktop>\\Curriculare Analyse\\<Beruf>\\<LF NN - Titel>\\
    Alle Skills schreiben ihre Artefakte in DENSELBEN Ordner (wachsende Fallakte)."""
    desk = desktop or find_desktop()
    try:
        nr = int(lernfeld_nr)
    except (TypeError, ValueError):
        nr = 0
    return (desk / FALLAKTE_WURZEL
            / safe_name(beruf, 100)
            / safe_name(f"LF {nr:02d} - {lernfeld_titel}", 120))
