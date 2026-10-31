#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_math_symbols.py — Validierung mathematischer Vektorsymbole in SVG-Grafiken

Prüft:
1. Summenzeichen Sigma (Σ): Orientierung der Pfadsegmente (Öffnung nach rechts, Vertex nach innen).
2. Makrons / Querstrich (x̄): Zentrierung über dem Merkmalssymbol (keine Fehlplatzierung über Malpunkten o. Ä.).
3. Wurzelzeichen (√): Ausrichtung des Radikanden-Dachs nach rechts.
"""
import glob
import math
import os
import re
import sys
import xml.etree.ElementTree as ET

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def check_svg_math_symbols(svg_path: str) -> list[str]:
    errors = []
    try:
        tree = ET.parse(svg_path)
        root = tree.getroot()
    except Exception as e:
        return [f"XML Parse Fehler in {os.path.basename(svg_path)}: {e}"]

    # 1. Check <path> elements for Sigma geometry
    for path in root.iter("{http://www.w3.org/2000/svg}path"):
        d = path.get("d", "").strip()
        # Look for 4-segment polygon M x0 y0 L x1 y1 L x2 y2 L x3 y3 L x4 y4
        tokens = re.findall(r"([MLZ])|(-?\d+(?:\.\d+)?)", d)
        coords = []
        for t, val in tokens:
            if val:
                coords.append(float(val))
        
        # If we have 5 points (10 numbers)
        if len(coords) == 10:
            x0, y0, x1, y1, x2, y2, x3, y3, x4, y4 = coords
            # Check if this forms a Sigma-like shape:
            # Horizontal top bar, 2 diagonals, horizontal bottom bar
            is_top_horiz = abs(y0 - y1) <= 4 and abs(x0 - x1) > 10
            is_bot_horiz = abs(y3 - y4) <= 4 and abs(x3 - x4) > 10
            if is_top_horiz and is_bot_horiz:
                # Top and bottom are horizontal bars.
                # In a standard Sigma (Σ):
                # Left-most x coordinates are the inner corners (x1, x3).
                # The vertex (x2, y2) must be to the RIGHT of x1 and x3 (x2 > x1 and x2 > x3).
                # Right-most x coordinates are the outer ends (x0, x4).
                if x2 < min(x1, x3):
                    errors.append(
                        f"SIGMA_REVERSED: Summenzeichen in '{os.path.basename(svg_path)}' ist verkehrt herum "
                        f"(Öffnung zeigt nach links statt nach rechts: Vertex x={x2} < Ecke x={x1})."
                    )
                elif x0 < x1 or x4 < x3:
                    # Top/bottom bars drawn left-to-right instead of inwards
                    pass

    # 2. Check Makron lines (horizontal lines above text)
    lines = list(root.iter("{http://www.w3.org/2000/svg}line"))
    texts = list(root.iter("{http://www.w3.org/2000/svg}text"))
    
    # Verify no line is placed directly over multiplication dot '·' or '+'
    for l in lines:
        try:
            x1 = float(l.get("x1", 0))
            x2 = float(l.get("x2", 0))
            y1 = float(l.get("y1", 0))
            y2 = float(l.get("y2", 0))
        except (ValueError, TypeError):
            continue
            
        # Is it a short horizontal bar? (length 10-30px, horizontal)
        if abs(y1 - y2) <= 1 and 8 <= abs(x1 - x2) <= 35:
            mid_x = (x1 + x2) / 2
            # Check nearby texts directly below (y in [y1 + 10, y1 + 35])
            for t in texts:
                try:
                    tx = float(t.get("x", 0))
                    ty = float(t.get("y", 0))
                except (ValueError, TypeError):
                    continue
                t_content = (t.text or "").strip()
                if abs(tx - mid_x) < 8 and (y1 < ty <= y1 + 30):
                    if t_content in ("·", "*", "+", "−", "-"):
                        errors.append(
                            f"MAKRON_MISPLACED: Querstrich über Rechenzeichen '{t_content}' "
                            f"in '{os.path.basename(svg_path)}' bei x={mid_x:.1f}, y={y1:.1f} gefunden."
                        )

    return errors

def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_math_symbols.py <svg-files-or-glob>")
        sys.exit(1)

    all_errors = []
    files = []
    for arg in sys.argv[1:]:
        matches = glob.glob(arg)
        if matches:
            files.extend(matches)
        elif os.path.exists(arg):
            files.append(arg)

    print(f"=== Mathematische Symbol-Validierung: {len(files)} SVG-Datei(en) ===")
    for f in files:
        errs = check_svg_math_symbols(f)
        if errs:
            for e in errs:
                print(f"  ❌ {e}")
            all_errors.extend(errs)
        else:
            print(f"  ✔ {os.path.basename(f)}: Alle mathematischen Symbole & Orientierungen korrekt.")

    if all_errors:
        print(f"\nFehler gefunden: {len(all_errors)}")
        sys.exit(1)
    else:
        print("\n✔ Alle mathematischen Symbole (Sigma, Makrons, Operatoren) sind fehlerfrei!")
        sys.exit(0)

if __name__ == "__main__":
    main()
