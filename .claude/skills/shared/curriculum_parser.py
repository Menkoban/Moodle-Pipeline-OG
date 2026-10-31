# -*- coding: utf-8 -*-
"""curriculum_parser.py — Semantischer Parser für KMK-Rahmenlehrpläne und CuVo-Vorgaben.

Extrahiert aus rohem RLP-Text oder isolierten Lernfeldblöcken:
  - Lernfeld-Metadaten (Nummer, Titel, Zeitrichtwert in Ustd., Ausbildungsjahr)
  - Phasen der vollständigen Handlung (Informieren, Planen, Entscheiden, Ausführen, Kontrollieren, Bewerten)
  - Inhaltsdimensionen & Mindestinhalte (Fachbegriffe, Verfahren, Werkstoffe, Klammerausdrücke, Inhalte-Listen)
  - Normen (DIN, ISO, EN, VDE, DGUV, TRGS, BGB/HGB)
  - Formeln und physikalische/technische Größen
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


NORM_PATTERNS = [
    r"\bDIN\s+(?:EN\s+)?(?:ISO\s+)?\d+(?:-\d+)?\b",
    r"\bDIN\s+VDE\s+\d+(?:-\d+)?\b",
    r"\bISO\s+\d+(?:-\d+)?\b",
    r"\bEN\s+\d+(?:-\d+)?\b",
    r"\bDGUV\s+(?:Vorschrift\s+\d+|Regel\s+\d+[\w-]*|Information\s+\d+[\w-]*)\b",
    r"\bTRGS\s+\d+\b",
    r"\b(?:VDI|VDE|DVGW|BGI|BGR)\s+\d+\b",
    r"\b5\s+Sicherheitsregeln\b",
]

ACTION_PHASE_KEYWORDS = {
    "informieren": [
        "informieren", "analysieren", "erfassen", "entnehmen", "beschaffen",
        "auftrag", "kundenauftrag", "kundenwunsch", "datenblatt", "schaltplan", "kundengespräch",
        "ausgangslage", "anforderung", "technische unterlagen", "recherchieren", "dokumentation",
        "anordnungspläne", "technische zeichnungen", "auswerten", "vorbereiten", "bereiten"
    ],
    "planen": [
        "planen", "erstellen", "konzipieren", "arbeitsablauf", "zeitplan",
        "materialliste", "messplan", "kriterien", "strukturieren", "vorbereiten",
        "dimensionieren", "auslegen", "schaltungsentwurf", "wirkungskette",
        "arbeitschritte", "arbeitsschritte", "skizzen", "stücklisten", "fertigungspläne"
    ],
    "entscheiden": [
        "entscheiden", "auswählen", "begründen", "abwägen", "alternative",
        "verfahren", "komponenten", "werkzeug", "material", "festlegen",
        "variantenvergleich", "wirtschaftlich", "vor- und nachteile", "unterscheiden",
        "auswahl", "geeignete"
    ],
    "ausfuehren": [
        "durchführen", "ausführen", "verdrahten", "montieren", "fertigen",
        "programmieren", "installieren", "messen", "prüfen", "inbetriebnahme",
        "arbeitssicherheit", "unfallverhütung", "schutzmaßnahmen", "anwenden",
        "realisieren", "errichten", "anpassen", "erproben", "herstellen", "bearbeiten",
        "trennen", "umformen", "fügen"
    ],
    "kontrollieren": [
        "kontrollieren", "überprüfen", "prüfen", "messen", "soll-ist-vergleich",
        "funktionsprüfung", "funktionsfähigkeit", "fehlersuche", "protokollieren", "messprotokoll",
        "prüfbericht", "abweichung", "toleranz", "betriebswerte", "prüfmittel", "prüfprotokolle"
    ],
    "bewerten": [
        "bewerten", "reflektieren", "beurteilen", "optimieren", "übergeben",
        "abnahme", "kundengespräch", "dokumentation", "wirtschaftlichkeit",
        "verbesserung", "transfer", "präsentieren", "zukünftiger vorgehensweisen",
        "arbeitsergebnisse", "fertigungskosten"
    ]
}

EXCLUDED_HYPHEN_WORDS = {"und", "oder", "sowie", "bzw", "an", "ab", "auf", "in", "mit", "zu"}


def clean_text(text: str) -> str:
    """Entfernt Zeilenumbrüche innerhalb von Wörtern (Silbentrennung) und normalisiert Whitespace."""
    # 1. Silbentrennung mit Zeilenumbruch: z.B. analysie-\nren -> analysieren
    text = re.sub(r"(\w+)-\n\s*([a-zäöüß]\w+)", r"\1\2", text)
    
    # 2. Silbentrennung mit Leerzeichen (z.B. aus 2-Spalten OCR/PDF-Extraktion: analysie- ren)
    def _join_hyphen(m):
        prefix = m.group(1)
        suffix = m.group(2)
        if suffix.lower() in EXCLUDED_HYPHEN_WORDS:
            return f"{prefix}- {suffix}"
        return f"{prefix}{suffix}"
        
    text = re.sub(r"(\w{3,})-\s+([a-zäöüß]{2,})\b", _join_hyphen, text)
    
    # 3. Seitenzahlen entfernen: z.B. \nSeite 14\n oder \n- 10 -\n
    text = re.sub(r"(?im)^\s*Seite\s+\d+\s*$", "", text)
    text = re.sub(r"(?im)^\s*-\s*\d+\s*-\s*$", "", text)
    return text


def clean_title(title: str) -> str:
    """Bereinigt einen Lernfeldtitel von Metadaten-Spuren."""
    t = clean_text(title)
    t = re.sub(r"(?i)\b\d+\.\s*Ausbildungsjahr\b", "", t)
    t = re.sub(r"(?i)\bAusbildungsjahr[:\s]*[1-4]\b", "", t)
    t = re.sub(r"(?i)\bZeitrichtwert[:\s]*\d+\s*(?:Ustd|Std|Stunden|h)?\.?", "", t)
    t = re.sub(r"\(\s*\d+\s*(?:Ustd|Std|Stunden|h)\.?\s*\)", "", t, flags=re.IGNORECASE)
    t = re.sub(r"(?i)\bZielformulierung[:\s]*", "", t)
    t = re.sub(r"\b(?:EG|AT|FT|BT|ET|[a-d]:)\b", "", t)  # Fachrichtungskürzel in Tabellen
    t = re.sub(r"(?i)\b3\.\s*u\.\b", "", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip(": -.")


def parse_lernfeld_header(block: str) -> Dict[str, Any]:
    """Extrahiert Lernfeld-Nummer, Titel, Zeitrichtwert und Ausbildungsjahr."""
    info: Dict[str, Any] = {
        "nr": None,
        "titel": "",
        "zeitrichtwert_ustd": None,
        "ausbildungsjahr": None
    }
    
    cleaned = clean_text(block)
    
    # 1. Ausbildungsjahr finden
    m_aj = re.search(r"(?i)(?:Ausbildungsjahr|Jahr)[:\s]+([1-4])\b", cleaned)
    if not m_aj:
        m_aj = re.search(r"(?i)([1-4])\.\s*Ausbildungsjahr", cleaned)
    if not m_aj:
        m_aj = re.search(r"(?i)Grundstufe", cleaned)
        if m_aj:
            info["ausbildungsjahr"] = 1
        elif re.search(r"(?i)Fachstufe\s*I\b", cleaned):
            info["ausbildungsjahr"] = 2
        elif re.search(r"(?i)Fachstufe\s*II\b", cleaned):
            info["ausbildungsjahr"] = 3
    else:
        info["ausbildungsjahr"] = int(m_aj.group(1))

    # 2. Zeitrichtwert finden
    m_zrw = re.search(r"(?i)(?:Zeitrichtwert|Umfang|Dauer|Richtwert)[:\s]+(\d+)\s*(?:Ustd|Std|Stunden|h)\.?", cleaned)
    if not m_zrw:
        m_zrw = re.search(r"(?i)\((\d+)\s*(?:Ustd|Std|Stunden|h)\.?\)", cleaned)
    if not m_zrw:
        m_zrw = re.search(r"(?i)(\d+)\s*(?:Unterrichtsstunden|Stunden)\b", cleaned)
    
    if m_zrw:
        info["zeitrichtwert_ustd"] = int(m_zrw.group(1))

    # 3. Lernfeld Nr & Titel
    m_lf = re.search(r"(?im)^\s*Lernfeld\s+(\d+)\s*[:\-\.]?\s*([\s\S]*?)(?=\n\s*(?:Die\s+Schülerinnen|Zielformulierung|Zeitrichtwert|Ausbildungsjahr|\Z))", cleaned)
    if m_lf:
        info["nr"] = int(m_lf.group(1))
        raw_titel = m_lf.group(2).strip()
        info["titel"] = clean_title(raw_titel)

    return info


def extract_action_phases(block: str) -> Dict[str, List[str]]:
    """Segmentiert den Textabsatz in Sätze / Kompetenzbeschreibungen und mappt sie auf die 6 Phasen."""
    cleaned = clean_text(block)
    # Entferne den gesamten Kopfblock bis vor die erste Kompetenzformulierung
    cleaned = re.sub(r"(?im)^\s*Lernfeld\s+\d+[\s\S]*?(?=(?:Die\s+Schülerinnen|Die\s+Schüler\b))", "", cleaned)
    cleaned = re.sub(r"(?i)\b\d+\.\s*Ausbildungsjahr\b", "", cleaned)
    cleaned = re.sub(r"(?i)\bZeitrichtwert[:\s]*\d+\s*(?:Ustd|Std|Stunden|h)?\.?", "", cleaned)
    cleaned = re.sub(r"(?i)\bZielformulierung[:\s]*", "", cleaned)

    # Trenne Inhalte-Block ab, falls vorhanden
    m_inh = re.search(r"(?im)^\s*Inhalte\s*:\s*([\s\S]*)$", cleaned)
    fliesztext = cleaned[:m_inh.start()] if m_inh else cleaned

    sentences = re.split(r"(?<=[.!?])\s+", fliesztext)
    phases: Dict[str, List[str]] = {
        "informieren": [],
        "planen": [],
        "entscheiden": [],
        "ausfuehren": [],
        "kontrollieren": [],
        "bewerten": []
    }
    
    for s in sentences:
        s_clean = re.sub(r"\s+", " ", s).strip()
        if len(s_clean) < 15:
            continue
        s_lower = s_clean.lower()
        
        scores: Dict[str, int] = {}
        for phase, keywords in ACTION_PHASE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in s_lower)
            if score > 0:
                scores[phase] = score
                
        if scores:
            best_phase = max(scores, key=scores.get)
            phases[best_phase].append(s_clean)
            
    return phases


def extract_norms(block: str) -> List[str]:
    """Findet alle Normen und Vorschriften im Text."""
    found = set()
    for pat in NORM_PATTERNS:
        for m in re.finditer(pat, block, re.IGNORECASE):
            found.add(m.group(0).strip())
    return sorted(list(found))


def extract_mindestinhalte(block: str) -> List[str]:
    """Extrahiert Mindestinhalte (in Klammern, kursiv markiert im RLP oder durch Inhalte-Abschnitt)."""
    cleaned = clean_text(block)
    inhalte = set()
    
    # 1. Block "Inhalte:"
    m_inh = re.search(r"(?im)^\s*Inhalte\s*:\s*([\s\S]*)$", cleaned)
    if m_inh:
        inh_text = m_inh.group(1)
        for line in inh_text.splitlines():
            line_s = line.strip()
            # Ignoriere Seitenzahlen / leere Zeilen / Trenner
            if 3 < len(line_s) < 80 and not re.match(r"^[-–—\d\s]+$", line_s):
                item = re.sub(r"^[-•–*]\s*", "", line_s).strip()
                if item and not item.startswith("Lernfeld"):
                    inhalte.add(item)

    # 2. Inhalte in Klammern (KMK-Standard: z.B. (Blockschaltbild, EVA-Prinzip, Sensoren, Aktoren))
    m_klammern = re.finditer(r"\(([^)]+)\)", cleaned)
    for mk in m_klammern:
        content = mk.group(1).strip()
        if ("," in content or len(content.split()) > 1) and not re.match(r"^(?:Zeitrichtwert|Std|Ustd|\d+)", content, re.IGNORECASE):
            for part in content.split(","):
                part_clean = part.strip()
                if 2 < len(part_clean) < 60:
                    inhalte.add(part_clean)

    # 3. Markdown-kursiv (*Inhalt* oder _Inhalt_)
    m_kursiv = re.finditer(r"(?:\*|_)([^*_\n]{3,60})(?:\*|_)", cleaned)
    for m in m_kursiv:
        cand = m.group(1).strip()
        if not re.match(r"^(?:Lernfeld|Zeitrichtwert|Stand|Ausbildungsjahr|Zielformulierung)", cand, re.IGNORECASE):
            inhalte.add(cand)

    return sorted(list(inhalte))


def parse_lernfeld_full(block: str) -> Dict[str, Any]:
    """Vollständige semantische Analyse eines Lernfeld-Blocks."""
    header = parse_lernfeld_header(block)
    phases = extract_action_phases(block)
    norms = extract_norms(block)
    mindestinhalte = extract_mindestinhalte(block)
    
    cleaned = clean_text(block)
    # Entferne Inhalte-Block für die Zielformulierung
    m_inh = re.search(r"(?im)^\s*Inhalte\s*:\s*([\s\S]*)$", cleaned)
    fliesztext = cleaned[:m_inh.start()] if m_inh else cleaned

    m_ziel = re.search(r"(?i)(Die\s+Schülerinnen\s+und\s+Schüler\s+(?:bereiten|besitzen|verfügen|können|analysieren|planen)[\s\S]*?)(?=\n\s*\n|\Z)", fliesztext)
    ziel_raw = m_ziel.group(1).strip() if m_ziel else fliesztext[:500].strip()
    ziel_raw = re.sub(r"\s+", " ", ziel_raw)

    return {
        "lernfeld_nr": header["nr"],
        "lernfeld_titel": header["titel"],
        "zeitrichtwert_ustd": header["zeitrichtwert_ustd"] or 80,
        "ausbildungsjahr": header["ausbildungsjahr"] or 1,
        "zielformulierung_raw": ziel_raw,
        "vollstaendige_handlung": phases,
        "mindestinhalte": mindestinhalte,
        "normen": norms,
        "raw_text": cleaned
    }


def parse_all_lernfelder_from_document(doc_text: str) -> List[Dict[str, Any]]:
    """Findet alle Lernfelder in einem Gesamtdokument (RLP) und parst sie."""
    cleaned = clean_text(doc_text)
    matches = list(re.finditer(r"(?im)^\s*Lernfeld\s+(\d+)\s*[:\-\.]?\s*(.*?)$", cleaned))
    if not matches:
        return []
    
    results = []
    seen_nrs = set()
    for i, m in enumerate(matches):
        nr = int(m.group(1))
        start_idx = m.start()
        if i + 1 < len(matches):
            end_idx = matches[i + 1].start()
            block = cleaned[start_idx:end_idx].strip()
        else:
            m_end = re.search(r"(?im)^\s*(?:Anhang|Liste\s+der\s+Entsprechungen|Entsprechungsliste)\b", cleaned[start_idx:])
            end_idx = start_idx + m_end.start() if m_end else len(cleaned)
            block = cleaned[start_idx:end_idx].strip()
            
        lf_data = parse_lernfeld_full(block)
        if not lf_data["lernfeld_nr"]:
            lf_data["lernfeld_nr"] = nr
            
        if nr in seen_nrs:
            for idx, existing in enumerate(results):
                if existing["lernfeld_nr"] == nr:
                    if len(lf_data["raw_text"]) > len(existing["raw_text"]):
                        results[idx] = lf_data
                    break
        else:
            seen_nrs.add(nr)
            results.append(lf_data)
        
    return sorted(results, key=lambda x: x["lernfeld_nr"] or 0)
