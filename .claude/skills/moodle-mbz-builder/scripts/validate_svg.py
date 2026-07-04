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

    return errors, warns


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
        for act in sec.get("activities", []):
            for img in act.get("images", []) or []:
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
