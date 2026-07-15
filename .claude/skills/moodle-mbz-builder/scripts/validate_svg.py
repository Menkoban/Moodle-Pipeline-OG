#!/usr/bin/env python3
"""Lint the diagrams of a moodle-mbz-builder course for the two defects that
hand-authored SVGs silently produce: content clipped at the viewBox edge, and
labels overlapping each other. It measures real text widths (see
``svg_geometry``), so it catches these deterministically instead of relying on
eyeballing a rendered PNG.

Checks per SVG:
  * OVERFLOW (error) — an element's bounding box lies outside the viewBox, so it
    is clipped. Reports the element and the viewBox that would contain it.
  * OVERLAP (warn)   — two text labels overlap enough to hide each other.
  * LINE/PATH (warn) — a line or curved path (arc, Q/C — e.g. rotation arrows)
    runs through a text label; leader lines/paths ending AT the text are exempt.
  * SHAPE (warn)     — a filled polygon (arrowhead, marker) covers a text label.
  * BOXFIT (warn)    — text runs outside its containing box.
  * TSPAN  (error)   — a styled inline <tspan> without its own x; svglib renders
    it on top of the following text (the "eibfaidhe genau EIN Weg" trap). Use
    separate <text> elements instead.

Inputs may be .svg files, directories (scanned recursively), or a course JSON
(every activity/page `images` entry is checked).

Usage:
    python validate_svg.py assets/*.svg
    python validate_svg.py assets/            # a directory
    python validate_svg.py course.json        # all referenced diagrams
    python validate_svg.py assets/ --strict   # warnings also fail (exit 1)

Exit code 0 = clean (no errors; warnings allowed unless --strict), 1 = defects.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import sys

import svg_geometry as G

EPS = 1.0            # viewBox tolerance in user units
OVERLAP_EPS = 2.5    # min overlap (both axes) to count as hiding content


def _pt_in_box(px, py, b, pad):
    return b.x0 - pad <= px <= b.x1 + pad and b.y0 - pad <= py <= b.y1 + pad


def _seg_hits_box(seg, b, pad=1.0):
    """Liang-Barsky: does the segment intersect the (padded) box interior?"""
    x1, y1, x2, y2 = seg
    xmin, ymin, xmax, ymax = b.x0 - pad, b.y0 - pad, b.x1 + pad, b.y1 + pad
    dx, dy = x2 - x1, y2 - y1
    p = (-dx, dx, -dy, dy)
    q = (x1 - xmin, xmax - x1, y1 - ymin, ymax - y1)
    u1, u2 = 0.0, 1.0
    for pi, qi in zip(p, q):
        if pi == 0:
            if qi < 0:
                return False
        else:
            t = qi / pi
            if pi < 0:
                u1 = max(u1, t)
            else:
                u2 = min(u2, t)
    return u1 <= u2


def _risky_glyphs(text):
    """Characters that svglib's base-14 Helvetica renders as a missing-glyph
    box. High precision: flags combining diacritics (used as negation bars) and
    the misc-symbols/emoji planes (⚠, ✅, ⛔, …). Deliberately does NOT flag
    arrows (→ ↑, U+2190–U+21FF) or the middle dot ·, which do rasterise."""
    bad = set()
    for ch in text:
        o = ord(ch)
        if 0x0300 <= o <= 0x036F:
            bad.add("combining mark")
        elif 0x2600 <= o <= 0x27BF or o >= 0x1F000:
            bad.add(f"U+{o:04X}")
    return bad


# --------------------------------------------------------------------------- #
# Typografie-Checks (deutsche Fach-Konventionen in Diagramm-Beschriftungen)
# --------------------------------------------------------------------------- #
import re

# Einheiten mit nachgestellter 2/3 statt hochgestelltem ²/³ (cm2, mm^2, N/cm2 …)
_RE_UNIT_SUP = re.compile(r"(?<![\w²³])((?:[A-Za-z]+/)?[cdk]?m)\s*\^?\s*([23])(?![\d\w])")
# beliebige Caret-Hochstellung ("^2") — in SVG-Text immer falsch
_RE_CARET = re.compile(r"\^")
# "min-1" / "s-1" — ⁻ (U+207B) ist NICHT WinAnsi-sicher, daher 1/min empfehlen
_RE_PER_UNIT = re.compile(r"\b(min|s)-1\b")
# x oder × als Malzeichen zwischen zwei Operanden ("F = p x A", "4 x 8 mm")
_RE_MAL = re.compile(r"(?<=[\w²³\)\]])\s+[x×]\s+(?=[\w\(])")
# Dezimalpunkt statt Komma (3.14 → 3,14)
_RE_DEZIMAL = re.compile(r"\d\.\d")
# Formelzeichen mit Ziffern-Index in einer Zeile (A1, d2, F1 …) — die Ziffer
# gehört TIEFGESTELLT (separates kleineres <text>-Element mit y-Versatz;
# Unicode-Subskripte ₁₂ sind NICHT WinAnsi-sicher und daher tabu in SVGs)
_RE_INDEX = re.compile(r"(?<![A-Za-z0-9_])([AdFUIRp])([0-9])(?![A-Za-z0-9_])")

# ae/oe/ue-Transliterationen: präzise Stamm-Liste statt generischem Muster
# (generisches "ue" träfe legitime Wörter wie "Steuerung", "neue", "aktuell").
_TRANSLIT_STEMS = [
    "fuer", "ueber", "uebung", "gruen", "drueck", "fluess", "waende",
    "behaelt", "flaech", "groess", "oeffn", "waehl", "laeng", "staerk",
    "hoehe", "hoeher", "waerm", "kuehl", "schluessel", "loesung", "loecher",
    "zusaetz", "erklaer", "ausfuell", "pruef", "muess", "fuell", "fuehr",
    "rueck", "stueck", "staend", "verstaend", "spaet", "frueh", "aender",
    "haeuf", "laeuft", "raeder", "gehaeuse", "koerper", "schuetz",
    "betraegt", "traegt", "erhoeh", "geraet", "qualitaet", "aktivitaet",
    "gelaende", "waehrend", "naechst", "taeglich", "gemaess", "saeule",
    "buendig", "duese", "oel",
]
_RE_TRANSLIT = re.compile(
    r"[A-Za-zäöüÄÖÜß]*(?:" + "|".join(_TRANSLIT_STEMS) + r")[A-Za-zäöüÄÖÜß]*",
    re.IGNORECASE)
# ss statt ß nur bei eindeutigen Wörtern (kein "Fluss"/"Messung"-Fehlalarm)
_RE_SS = re.compile(r"\b(gross\w*|weiss|heisst|schliess\w*|massnahme\w*|strasse\w*)\b",
                    re.IGNORECASE)

MIN_FONT_SIZE = 10.0   # kleinere Beschriftungen sind gedruckt kaum lesbar
CENTER_TOL = 10.0      # "fast zentriert": mittig verankert, aber daneben
ALIGN_TOL = 4.0        # "fast bündig": gestapelte Texte, um 1–4 px versetzt

# rein numerisches Label (Skalenwert): "0", "-5", "3,14", "10.5"
_NUMERIC_RX = re.compile(r"^-?\d+(?:[.,]\d+)?$")


def _typo_issues(label):
    """Konventions-Verstöße in einem Text-Label (deutsche Fachdiagramme)."""
    out = []
    for m in _RE_UNIT_SUP.finditer(label):
        sup = "²" if m.group(2) == "2" else "³"
        out.append(f"EINHEIT '{m.group(0)}' -> '{m.group(1)}{sup}' "
                   f"(hochgestellt; ² und ³ rendern in PDF/PPTX)")
    if "²" not in label and "³" not in label and _RE_CARET.search(label):
        out.append("EINHEIT Caret-Hochstellung '^' -> echtes ²/³ verwenden")
    for m in _RE_PER_UNIT.finditer(label):
        out.append(f"EINHEIT '{m.group(0)}' -> '1/{m.group(1)}' "
                   f"(hochgestelltes Minus ist nicht WinAnsi-sicher)")
    if label.strip() in ("x", "×"):
        out.append("MALZEICHEN einzelnes 'x' -> Malpunkt '·' verwenden")
    elif _RE_MAL.search(label):
        out.append(f"MALZEICHEN 'x' als Mal-Operator in '{label}' -> '·' verwenden")
    if _RE_DEZIMAL.search(label):
        out.append(f"DEZIMAL Punkt als Dezimaltrenner in '{label}' -> "
                   f"deutsches Komma (3,14)")
    for m in _RE_TRANSLIT.finditer(label):
        out.append(f"UMLAUT Transliteration '{m.group(0)}' -> echte Umlaute "
                   f"(ä/ö/ü/ß rendern in PDF/PPTX einwandfrei)")
    for m in _RE_SS.finditer(label):
        out.append(f"UMLAUT 'ss' statt 'ß' in '{m.group(0)}' -> ß verwenden")
    for m in _RE_INDEX.finditer(label):
        out.append(f"INDEX '{m.group(0)}' -> Ziffer tiefstellen (separates "
                   f"kleineres <text>-Element mit y-Versatz; kein Unicode-₁)")
    return out


def _hex_lum(color):
    """Relative Luminanz eines #rrggbb/#rgb-Farbwerts, sonst None."""
    if not color or not color.startswith("#"):
        return None
    h = color[1:]
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return None
    try:
        r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    except ValueError:
        return None
    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def _iter_svg_paths(inputs):
    """Expand inputs (globs, dirs, .svg, course .json) into a list of svg paths."""
    out = []
    for inp in inputs:
        matches = glob.glob(inp)
        if not matches and os.path.exists(inp):
            matches = [inp]
        for p in matches or [inp]:
            if os.path.isdir(p):
                for r, _d, fs in os.walk(p):
                    out += [os.path.join(r, f) for f in fs if f.lower().endswith(".svg")]
            elif p.lower().endswith(".json"):
                out += _svgs_from_course(p)
            elif p.lower().endswith(".svg"):
                out.append(p)
    # de-dupe, keep order
    seen, uniq = set(), []
    for p in out:
        ap = os.path.abspath(p)
        if ap not in seen and os.path.exists(p):
            seen.add(ap)
            uniq.append(p)
    return uniq


def _svgs_from_course(json_path):
    with open(json_path, encoding="utf-8") as fh:
        data = json.load(fh)
    paths = []
    for sec in data.get("sections", []):
        sec_imgs = sec.get("images") or ([sec["image"]] if sec.get("image") else [])
        for img in sec_imgs:
            if str(img).lower().endswith(".svg"):
                paths.append(img)
        for act in sec.get("activities", []):
            for img in act.get("images", []) or []:
                if str(img).lower().endswith(".svg"):
                    paths.append(img)
    return paths


def lint_file(path):
    """Return (errors, warns) as lists of message strings for one SVG."""
    errors, warns = [], []
    try:
        root, _raw = G.load(path)
    except Exception as e:  # noqa: BLE001
        return ([f"parse error: {e}"], [])

    is_chart = (root.get("data-diagram-type") == "chart")
    vx, vy, vw, vh = G.get_viewbox(root)
    vx1, vy1 = vx + vw, vy + vh
    boxes = G.collect_boxes(root)

    # 1) overflow beyond the viewBox
    need = [vx, vy, vx1, vy1]  # min x, min y, max x, max y that must be covered
    for b in boxes:
        out = []
        if b.x0 < vx - EPS:
            out.append(f"left by {vx - b.x0:.0f}")
        if b.x1 > vx1 + EPS:
            out.append(f"right by {b.x1 - vx1:.0f}")
        if b.y0 < vy - EPS:
            out.append(f"top by {vy - b.y0:.0f}")
        if b.y1 > vy1 + EPS:
            out.append(f"bottom by {b.y1 - vy1:.0f}")
        if out:
            need[0] = min(need[0], b.x0)
            need[1] = min(need[1], b.y0)
            need[2] = max(need[2], b.x1)
            need[3] = max(need[3], b.y1)
            desc = f"<{b.tag}" + (f" '{b.label}'" if b.label else "") + ">"
            errors.append(f"OVERFLOW {desc} clipped: {', '.join(out)}")

    if need != [vx, vy, vx1, vy1]:
        m = 8
        errors.append(
            f"  -> fix: enlarge viewBox to "
            f"\"{need[0]-m:.0f} {need[1]-m:.0f} {need[2]-need[0]+2*m:.0f} "
            f"{need[3]-need[1]+2*m:.0f}\" (or run autofit_svg.py)")

    # 2) styled inline tspans (svglib overlap trap)
    for b in boxes:
        if b.tag == "text" and b.extra.get("styled_tspan"):
            errors.append(
                f"TSPAN styled inline <tspan> in text '{b.label}' - svglib will "
                f"overlap it; split into separate <text> elements")

    # 3) glyphs the base-14 Helvetica cannot rasterise -> tofu boxes in PDF/PPTX
    for b in boxes:
        if b.tag != "text":
            continue
        risky = _risky_glyphs(b.label)
        if risky:
            warns.append(
                f"GLYPH text '{b.label}' contains {', '.join(sorted(risky))} - "
                f"renders as a box in PDF/PPTX; draw it (e.g. a line for a "
                f"negation bar) or drop the symbol")

    # 4) lines AND curved paths crossing through a text label (an intended
    #    leader line/path ends AT the text, so one endpoint is near it — those
    #    are excluded). Paths are checked segment-wise on their sampled points,
    #    so arcs and Q/C-curves (rotation arrows!) are covered too.
    texts = [b for b in boxes if b.tag == "text"]
    for ln in boxes:
        if ln.tag == "line":
            seg = ln.extra.get("seg")
            segs = [seg] if seg else []
            kind = "LINE"
        elif ln.tag == "path":
            pts = ln.extra.get("pts") or []
            segs = [(pts[k][0], pts[k][1], pts[k + 1][0], pts[k + 1][1])
                    for k in range(len(pts) - 1)]
            kind = "PATH"
        else:
            continue
        if not segs:
            continue
        first, last = (segs[0][0], segs[0][1]), (segs[-1][2], segs[-1][3])
        for t in texts:
            if not t.label:
                continue
            ends_here = (_pt_in_box(first[0], first[1], t, 6)
                         or _pt_in_box(last[0], last[1], t, 6))
            if ends_here:
                continue
            if any(_seg_hits_box(s, t, pad=0.5) for s in segs):
                warns.append(f"{kind} crosses text '{t.label}'")

    # 4b) filled shapes (polygons — arrowheads, markers) covering a text label.
    #     No leader exemption: a filled shape on top of text always hides it.
    for sh in boxes:
        if sh.tag not in ("polygon", "polyline"):
            continue
        for t in texts:
            if not t.label:
                continue
            ow, oh = sh.overlaps(t)
            if ow > OVERLAP_EPS and oh > OVERLAP_EPS:
                warns.append(f"SHAPE <{sh.tag}> covers text '{t.label}' "
                             f"(~{ow:.0f}x{oh:.0f}px)")

    # 5) text overflowing its containing (non-background) box: the text starts
    #    inside a coloured box (e.g. a Merke bar) but runs past its edge. autofit
    #    grows the viewBox, not the box, so this slips past the overflow check.
    vb_area = max(vw * vh, 1.0)
    rects = [b for b in boxes if b.tag == "rect" and (b.w * b.h) < 0.9 * vb_area]
    for t in texts:
        if not t.label:
            continue
        anchor = t.extra.get("anchor", "start")
        ax = (t.x0 + t.x1) / 2 if anchor == "middle" else (t.x1 if anchor == "end" else t.x0)
        ay = (t.y0 + t.y1) / 2
        containers = [r for r in rects if r.x0 <= ax <= r.x1 and r.y0 <= ay <= r.y1]
        if not containers:
            continue
        c = min(containers, key=lambda r: r.w * r.h)  # most specific box
        if t.x1 > c.x1 + 2 or t.x0 < c.x0 - 2:
            warns.append(
                f"BOXFIT text '{t.label}' runs outside its box "
                f"(text {t.x0:.0f}-{t.x1:.0f}, box {c.x0:.0f}-{c.x1:.0f}) "
                f"- widen the box, shorten, or wrap to two lines")

    # 6) text-text overlaps
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            ow, oh = texts[i].overlaps(texts[j])
            if ow > OVERLAP_EPS and oh > OVERLAP_EPS:
                warns.append(
                    f"OVERLAP '{texts[i].label}' <-> '{texts[j].label}' "
                    f"(~{ow:.0f}x{oh:.0f}px)")

    # 7) Typografie: Einheiten (² ³), Malpunkt ·, echte Umlaute, Dezimalkomma
    for t in texts:
        for msg in _typo_issues(t.label):
            warns.append(msg)

    # 8) Lesbarkeit: zu kleine Schrift (Ausnahme: tiefgestellte Index-Ziffern
    #    wie die "1" in F1 — bewusst ~0.72 der Grundgröße)
    for t in texts:
        size = t.extra.get("size")
        if size and size < MIN_FONT_SIZE and not re.fullmatch(r"\d{1,2}", t.label):
            warns.append(f"FONTSIZE text '{t.label}' hat font-size {size:g} "
                         f"(< {MIN_FONT_SIZE:g}) - gedruckt kaum lesbar")

    # 9) Bündigkeit: fast-zentrierte und fast-bündige Beschriftungen
    center_x = vx + vw / 2.0
    for t in texts:
        if t.extra.get("anchor") == "middle" and t.extra.get("ax") is not None:
            off = abs(t.extra["ax"] - center_x)
            if 0.5 < off <= CENTER_TOL and t.w > 0.4 * vw:
                warns.append(
                    f"BUENDIG text '{t.label}' ist mittig verankert, aber "
                    f"{off:.0f}px neben der viewBox-Mitte ({center_x:g}) - "
                    f"x={t.extra['ax']:g} angleichen")
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            a, b = texts[i], texts[j]
            if a.extra.get("anchor") != b.extra.get("anchor"):
                continue
            # nur zeilenartige Texte vergleichen — Einzel-Segmente
            # (z. B. Index-Ziffern segmentierter Formelzeilen) ausnehmen
            if a.w < 30 or b.w < 30:
                continue
            ax_, bx_ = a.extra.get("ax"), b.extra.get("ax")
            if ax_ is None or bx_ is None:
                continue
            dx_ = abs(ax_ - bx_)
            dy_ = abs(((a.y0 + a.y1) / 2) - ((b.y0 + b.y1) / 2))
            if 0.5 < dx_ <= ALIGN_TOL and dy_ > 10:
                warns.append(
                    f"BUENDIG '{a.label}' und '{b.label}' sind um {dx_:.0f}px "
                    f"versetzt (x={ax_:g} vs. {bx_:g}) - vermutlich bündig gemeint")

    # 10) Kontrast: Text auf farbigem Kasten/Kreis mit zu wenig Leuchtdichte-Abstand
    fills = [b for b in boxes
             if b.tag in ("rect", "circle") and b.extra.get("fill")]
    for t in texts:
        tl = _hex_lum(t.extra.get("fill") or "#000000")
        if tl is None:
            continue
        ax_ = t.extra.get("ax")
        ay_ = (t.y0 + t.y1) / 2
        if ax_ is None:
            continue
        containers = [r for r in fills
                      if r.x0 <= ax_ <= r.x1 and r.y0 <= ay_ <= r.y1
                      and (r.w * r.h) < 0.9 * vb_area]
        if not containers:
            continue
        bg = _hex_lum(min(containers, key=lambda r: r.w * r.h).extra.get("fill"))
        if bg is None:
            continue
        ratio = (max(tl, bg) + 0.05) / (min(tl, bg) + 0.05)
        if ratio < 2.5:
            warns.append(f"KONTRAST text '{t.label}' hebt sich kaum vom "
                         f"Kasten ab (Kontrast {ratio:.1f}:1, < 2.5:1)")

    # 11) V1/V3: Chart-Achsen + Skala (nur markierte Charts)
    if is_chart:
        warns += _chart_axis_warnings(boxes, vx, vy, vw, vh)

    # 12) V4a: geschlossene Figuren (alle Diagramme)
    warns += _figure_closure_warnings(boxes)

    return errors, warns


def _segments(boxes):
    """All straight segments (x1,y1,x2,y2) from line/polyline/polygon/path boxes."""
    segs = []
    for b in boxes:
        if b.tag == "line":
            seg = b.extra.get("seg")
            if seg:
                segs.append(seg)
        elif b.tag in ("path", "polyline", "polygon"):
            pts = b.extra.get("pts") or []
            for k in range(len(pts) - 1):
                segs.append((pts[k][0], pts[k][1], pts[k + 1][0], pts[k + 1][1]))
    return segs


def _find_axes(boxes, vx, vy, vw, vh):
    """Longest near-horizontal segment in the lower half = x-axis; longest
    near-vertical segment in the left part = y-axis. Returns (x_axis, y_axis),
    each (x1,y1,x2,y2) or None."""
    x_axis = y_axis = None
    x_best = y_best = 0.0
    for (x1, y1, x2, y2) in _segments(boxes):
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        if abs(dy) <= 2 and min(y1, y2) >= vy + 0.5 * vh and length >= 0.4 * vw:
            if length > x_best:
                x_best, x_axis = length, (x1, y1, x2, y2)
        if abs(dx) <= 2 and min(x1, x2) <= vx + 0.4 * vw and length >= 0.4 * vh:
            if length > y_best:
                y_best, y_axis = length, (x1, y1, x2, y2)
    return x_axis, y_axis


def _chart_axis_warnings(boxes, vx, vy, vw, vh):
    """V1 (axis titles) — only called for diagrams marked
    data-diagram-type="chart". V3 (scale) is added in a later task."""
    warns = []
    texts = [b for b in boxes if b.tag == "text" and b.label]
    x_axis, y_axis = _find_axes(boxes, vx, vy, vw, vh)

    def is_num(t):
        return bool(_NUMERIC_RX.match(t.label.strip()))

    def cx(t):
        return (t.x0 + t.x1) / 2.0

    def cy(t):
        return (t.y0 + t.y1) / 2.0

    if x_axis is None:
        warns.append("ACHSE keine x-Achsenlinie erkennbar (Chart markiert)")
    else:
        ax_y = (x_axis[1] + x_axis[3]) / 2.0
        if not any((not is_num(t)) and cy(t) > ax_y for t in texts):
            warns.append("ACHSE x-Achse ohne Beschriftung (Achsentitel fehlt)")

    if y_axis is None:
        warns.append("ACHSE keine y-Achsenlinie erkennbar (Chart markiert)")
    else:
        # lenient: y-titles are often rotated (position unreliable) -> any
        # non-numeric text in the left third counts as a title.
        if not any((not is_num(t)) and cx(t) < vx + vw / 3.0 for t in texts):
            warns.append("ACHSE y-Achse ohne Beschriftung (Achsentitel fehlt)")

    return warns


def _figure_closure_warnings(boxes):
    """V4a — an open path/polyline outline whose start and end nearly meet is
    likely an unclosed figure. Conservative: only 2-12px gaps on a 2D figure
    whose endpoints nearly return to the start (so open curves/leaders, whose
    endpoints are far apart, are never flagged). polygons are inherently closed
    and carry path_closed=True."""
    warns = []
    for b in boxes:
        if b.tag not in ("path", "polyline"):
            continue
        if b.extra.get("path_closed"):
            continue
        pts = b.extra.get("pts") or []
        if len(pts) < 3:
            continue
        gap = math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1])
        if not (2.0 < gap <= 12.0):
            continue
        if b.w <= 10 or b.h <= 10:            # a flat line, not a figure
            continue
        if gap >= 0.15 * math.hypot(b.w, b.h):  # endpoints don't return to start
            continue
        warns.append(f"FIGUR nicht geschlossen (Luecke ~{gap:.0f}px) - Pfad "
                     f"mit Z schliessen oder Endpunkte treffen lassen")
    return warns


def check_course_svgs(spec, base_dir=".", strict=False, out=None):
    """Lint every SVG referenced by a loaded course spec. Prints a short summary
    and per-file findings to `out` (default stderr). Returns (n_errors, n_warns).

    Intended to be called automatically from build_mbz.py / make_materials.py so
    every build checks its diagrams without anyone remembering to run this tool.
    Raises SystemExit(1) if strict and any error is found.
    """
    if out is None:
        out = sys.stderr
    try:
        out.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    svgs = []
    for sec in spec.get("sections", []):
        sec_imgs = sec.get("images") or ([sec["image"]] if sec.get("image") else [])
        for img in list(sec_imgs) + [i for act in sec.get("activities", [])
                                     for i in (act.get("images") or [])]:
            p = img if isinstance(img, str) else (img or {}).get("file")
            if not p or not str(p).lower().endswith(".svg"):
                continue
            cand = p if os.path.isabs(p) else os.path.join(base_dir, p)
            svgs.append(cand if os.path.exists(cand) else p)
    svgs = [p for p in svgs if os.path.exists(p)]
    if not svgs:
        return 0, 0

    n_err = n_warn = 0
    for p in svgs:
        errors, warns = lint_file(p)
        e = sum(1 for x in errors if not x.startswith("  "))
        n_err += e
        n_warn += len(warns)
        if errors or warns:
            print(f"SVG check: {os.path.basename(p)}", file=out)
            for x in errors:
                print("  " + x.strip(), file=out)
            for w in warns:
                print(f"  warn: {w}", file=out)
    if n_err or n_warn:
        print(f"SVG check: {n_err} error(s), {n_warn} warning(s) across "
              f"{len(svgs)} diagram(s). Run autofit_svg.py / validate_svg.py "
              f"to fix.", file=out)
        if n_err and strict:
            raise SystemExit("Aborting: SVG defects (--strict-svg).")
    else:
        print(f"SVG check: {len(svgs)} diagram(s) OK.", file=out)
    return n_err, n_warn


def main(argv=None):
    ap = argparse.ArgumentParser(description="Lint SVG diagrams for clipping and overlaps.")
    ap.add_argument("inputs", nargs="+", help=".svg files, a directory, or a course .json")
    ap.add_argument("--strict", action="store_true", help="treat warnings as failures")
    args = ap.parse_args(argv)

    # labels may contain non-cp1252 chars (umlauts, en-dashes); keep Windows
    # consoles from crashing on output.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

    paths = _iter_svg_paths(args.inputs)
    if not paths:
        print("No SVG files found.")
        return 1

    total_err = total_warn = 0
    for p in paths:
        errors, warns = lint_file(p)
        total_err += sum(1 for e in errors if not e.startswith("  "))
        total_warn += len(warns)
        if errors or warns:
            print(f"\n{p}")
            for e in errors:
                print(("  " + e) if not e.startswith("  ") else ("  " + e.strip()))
            for w in warns:
                print(f"  warn: {w}")
        else:
            print(f"{p}: OK")

    print(f"\n{len(paths)} file(s): {total_err} error(s), {total_warn} warning(s).")
    if total_err or (args.strict and total_warn):
        print("FAIL: defects found.")
        return 1
    print("OK: no clipping or hiding defects.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
