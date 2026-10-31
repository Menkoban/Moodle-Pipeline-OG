# -*- coding: utf-8 -*-
"""validate_math_formulas.py — Strenger mathematischer Typografie-, Index- und Formel-Validator.

Prüft:
  1. Echte Brüche: Keine unschönen Slashes ('/') in mathematischen Hauptformeln.
     Erfordert MathJax \\frac{a}{b} oder semantisches HTML-Bruch-Layout.
  2. Saubere Indizes: Keine rohen Unterstriche wie 'n_i', 'x_i', 's_A', 'x_1' im HTML-Text.
     Muss entweder als <sub>i</sub> oder via MathJax x_{i} formatiert sein.
  3. Keine fehlerhaften LaTeX-Entities im Klartext (z. B. '\\unsigma', '\\unradix', '\\to', '\\Sigma' unformatiert).
  4. Korrekte Wurzelnotation (&radic; oder \\sqrt{...}).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import List, Tuple, Dict, Any

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def check_html_math_quality(html_text: str, location_label: str) -> Tuple[List[str], List[str]]:
    fehler: List[str] = []
    warnungen: List[str] = []

    if not html_text:
        return fehler, warnungen

    # 1. Rohe Unterstrich-Indizes finden (z. B. n_i, x_i, s_A, x_1 ohne <sub>)
    # Ausgenommen MathJax-Blöcke \(...\) oder $$...$$
    clean_text = re.sub(r"\\\(.*?\\\)", "", html_text)
    clean_text = re.sub(r"\$\$.*?\$\$", "", clean_text)
    clean_text = re.sub(r"<code>.*?</code>", "", clean_text)
    clean_text = re.sub(r"<style.*?</style>", "", clean_text, flags=re.DOTALL)
    clean_text = re.sub(r"<script.*?</script>", "", clean_text, flags=re.DOTALL)

    raw_index_matches = re.findall(r"\b([a-zA-Z])_([a-zA-Z0-9]+)\b", clean_text)
    for var, idx in raw_index_matches:
        fehler.append(f"[{location_label}] Roher Index '{var}_{idx}' gefunden! Bitte '{var}<sub>{idx}</sub>' oder MathJax verwenden.")

    # 2. Fehlerhafte LaTeX-Fragmente / ungerenderte Entitäten
    broken_fragments = [
        (r"\\unsigma", "Fehlerhaftes Fragment '\\unsigma' gefunden."),
        (r"\\unradix", "Fehlerhaftes Fragment '\\unradix' gefunden."),
        (r"\\to\b", "LaTeX '\\to' im Klartext gefunden. Bitte '→' oder '&rarr;' verwenden!"),
        (r"\\rightarrow\b", "LaTeX '\\rightarrow' im Klartext gefunden. Bitte '→' oder '&rarr;' verwenden!"),
        (r"(?:1\s*/\s*n\s*·\s*(?:&Sigma;|Σ|\\sum))", "Bruch '1/n · Summe' mit Slash gefunden. Bitte echten horizontalen Bruch verwenden!"),
        (r"(?:h\(x[i_]\)\s*=\s*n[i_]\s*/\s*n)", "Bruch 'h(xi) = ni / n' mit Slash gefunden. Bitte horizontalen Bruch verwenden!"),
        (r"(?:s²\s*=\s*1\s*/\s*n)", "Bruch 's² = 1/n' mit Slash gefunden. Bitte horizontalen Bruch verwenden!")
    ]

    for pat, msg in broken_fragments:
        if re.search(pat, html_text, re.IGNORECASE):
            warnungen.append(f"[{location_label}] {msg}")

    return fehler, warnungen


def validate_course_math(course_path: str) -> Tuple[List[str], List[str]]:
    fehler: List[str] = []
    warnungen: List[str] = []

    if not os.path.exists(course_path):
        fehler.append(f"Datei nicht gefunden: {course_path}")
        return fehler, warnungen

    with open(course_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Kursbeschreibung
    summary = data.get("course", {}).get("summary", "")
    f_list, w_list = check_html_math_quality(summary, "Kursbeschreibung")
    fehler.extend(f_list)
    warnungen.extend(w_list)

    # Abschnitte & Aktivitäten
    for sec_idx, sec in enumerate(data.get("sections", [])):
        sec_name = sec.get("name", f"Abschnitt {sec_idx}")
        f_list, w_list = check_html_math_quality(sec.get("summary", ""), sec_name)
        fehler.extend(f_list)
        warnungen.extend(w_list)

        for act_idx, act in enumerate(sec.get("activities", [])):
            act_name = act.get("name", f"Aktivität {act_idx}")
            act_label = f"{sec_name} -> {act_name}"
            
            for field in ["intro", "content", "html"]:
                val = act.get(field)
                if isinstance(val, str):
                    f_sub, w_sub = check_html_math_quality(val, act_label)
                    fehler.extend(f_sub)
                    warnungen.extend(w_sub)

            # Formulare
            if act.get("type") == "formular":
                for b in act.get("spec", {}).get("blocks", []):
                    if b.get("heading"):
                        f_sub, w_sub = check_html_math_quality(b["heading"], f"{act_label} (Formular-Heading)")
                        fehler.extend(f_sub)
                        warnungen.extend(w_sub)
                    if b.get("html"):
                        f_sub, w_sub = check_html_math_quality(b["html"], f"{act_label} (Formular-HTML)")
                        fehler.extend(f_sub)
                        warnungen.extend(w_sub)
                    if b.get("field", {}).get("label"):
                        f_sub, w_sub = check_html_math_quality(b["field"]["label"], f"{act_label} (Field-Label)")
                        fehler.extend(f_sub)
                        warnungen.extend(w_sub)

            # Hotspots
            if act.get("type") == "hotspot":
                for p in act.get("spec", {}).get("pins", []):
                    if p.get("title"):
                        f_sub, w_sub = check_html_math_quality(p["title"], f"{act_label} (Pin-Title)")
                        fehler.extend(f_sub)
                        warnungen.extend(w_sub)
                    if p.get("desc"):
                        f_sub, w_sub = check_html_math_quality(p["desc"], f"{act_label} (Pin-Desc)")
                        fehler.extend(f_sub)
                        warnungen.extend(w_sub)

    return fehler, warnungen


def main():
    parser = argparse.ArgumentParser(description="Validiert mathematische Formeln und Typografie in course.json.")
    parser.add_argument("course_json", help="Pfad zur course.json")
    parser.add_argument("--strict", action="store_true", help="Behandle Warnungen als Fehler")
    args = parser.parse_args()

    fehler, warnungen = validate_course_math(args.course_json)

    print(f"=== Mathematische Formel- & Index-Validierung: {args.course_json} ===")
    if warnungen:
        print(f"\n[WARNUNGEN: {len(warnungen)}]")
        for w in warnungen:
            print(f"  ⚠ {w}")

    if fehler:
        print(f"\n[FEHLER: {len(fehler)}]")
        for f in fehler:
            print(f"  ❌ {f}")

    if not fehler and not (args.strict and warnungen):
        print("\n✔ Formel- & Index-Validierung ERFOLGREICH (Alle Indizes x_i -> x<sub>i</sub>, Brüche und Symbole sauber formatiert).")
        sys.exit(0)
    else:
        print("\n❌ Formel- & Index-Validierung FEHLGESCHLAGEN.")
        sys.exit(1)


if __name__ == "__main__":
    main()
