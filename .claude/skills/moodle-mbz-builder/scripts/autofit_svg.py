#!/usr/bin/env python3
"""Grow an SVG's ``viewBox`` so nothing is ever clipped at the edge.

Clipping happens because the ``viewBox`` is a fixed frame authored up front and
content (especially measured text) may reach past it. This tool computes the
true union bounding box of all elements — using the same text measurement as
``validate_svg.py`` — and rewrites the ``viewBox`` to that box plus a margin.
It also stretches the background ``<rect>`` (if a whitish full-canvas one is
present) to cover the new frame, so the diagram keeps its solid background.

The edit is surgical string replacement (only the ``viewBox`` attribute and the
background rect's x/y/width/height), so comments, formatting and the XML
declaration are preserved.

Note: auto-fit removes *clipping*; it does not resolve label *overlaps* — run
``validate_svg.py`` for those.

Usage:
    python autofit_svg.py assets/diagram.svg              # in place
    python autofit_svg.py assets/ --margin 12             # whole folder
    python autofit_svg.py course.json                     # all referenced svgs
    python autofit_svg.py diagram.svg -o fitted.svg       # single, alt output
    python autofit_svg.py assets/ --dry-run               # report only
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

import svg_geometry as G

_WHITE = {"#fff", "#ffffff", "white"}


def _iter_svg_paths(inputs):
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
                with open(p, encoding="utf-8") as fh:
                    data = json.load(fh)
                for sec in data.get("sections", []):
                    for act in sec.get("activities", []):
                        for img in act.get("images", []) or []:
                            if str(img).lower().endswith(".svg"):
                                out.append(img)
            elif p.lower().endswith(".svg"):
                out.append(p)
    seen, uniq = set(), []
    for p in out:
        ap = os.path.abspath(p)
        if ap not in seen and os.path.exists(p):
            seen.add(ap)
            uniq.append(p)
    return uniq


def _fmt(v: float) -> str:
    return str(int(round(v)))


def _set_attr(tag: str, name: str, value: str) -> str:
    if re.search(rf'\b{name}="[^"]*"', tag):
        return re.sub(rf'\b{name}="[^"]*"', f'{name}="{value}"', tag, count=1)
    return re.sub(r"\s*/?>\s*$",
                  lambda m: f' {name}="{value}"' + m.group(0).lstrip(),
                  tag, count=1)


def fit_svg(raw: str, margin: float):
    """Return (new_raw, message) or (raw, None) if nothing needed changing."""
    root = G.fromstring(raw)
    boxes = G.collect_boxes(root)
    bounds = G.content_bounds(boxes)
    if not bounds:
        return raw, None
    # Hintergrund-Rects (decken praktisch die gesamte Inhaltsflaeche ab) nicht
    # als Inhalt zaehlen: Nach einem Fit spannt das bg-Rect den vollen Rahmen
    # auf, und die viewBox wuerde sonst bei JEDEM Lauf um einen weiteren Rand
    # wachsen (nicht idempotent).
    total = max((bounds[2] - bounds[0]) * (bounds[3] - bounds[1]), 1.0)
    inner = [b for b in boxes
             if not (b.tag == "rect" and (b.x1 - b.x0) * (b.y1 - b.y0) >= 0.98 * total)]
    if inner and len(inner) < len(boxes):
        inner_bounds = G.content_bounds(inner)
        if inner_bounds:
            bounds = inner_bounds
    bx0, by0, bx1, by1 = bounds
    ovx, ovy, ovw, ovh = G.get_viewbox(root)
    old_vb = f"{_fmt(ovx)} {_fmt(ovy)} {_fmt(ovw)} {_fmt(ovh)}"
    # Nur WACHSEN, nie schrumpfen: deckt die alte viewBox den Inhalt samt Rand
    # schon ab, ist nichts zu tun (idempotent). Sonst Union aus alt + noetig.
    eps = 0.5
    if (ovx <= bx0 - margin + eps and ovy <= by0 - margin + eps
            and ovx + ovw >= bx1 + margin - eps and ovy + ovh >= by1 + margin - eps):
        return raw, None
    nx = min(ovx, bx0 - margin)
    ny = min(ovy, by0 - margin)
    nw = max(ovx + ovw, bx1 + margin) - nx
    nh = max(ovy + ovh, by1 + margin) - ny
    new_vb = f"{_fmt(nx)} {_fmt(ny)} {_fmt(nw)} {_fmt(nh)}"
    if new_vb == old_vb:
        return raw, None

    # rewrite viewBox on the <svg ...> opening tag
    svg_open = re.search(r"<svg\b[^>]*>", raw)
    if not svg_open:
        return raw, None
    tag = svg_open.group(0)
    if re.search(r'\bviewBox="[^"]*"', tag):
        new_tag = re.sub(r'\bviewBox="[^"]*"', f'viewBox="{new_vb}"', tag, count=1)
    else:
        new_tag = _set_attr(tag, "viewBox", new_vb)
    raw = raw[:svg_open.start()] + new_tag + raw[svg_open.end():]

    # stretch a whitish full-canvas background rect, if present
    def _rect_repl(m):
        rect = m.group(0)
        fill = (re.search(r'\bfill="([^"]*)"', rect) or [None, ""])[1].lower()
        if fill in _WHITE:
            rect = _set_attr(rect, "x", _fmt(nx))
            rect = _set_attr(rect, "y", _fmt(ny))
            rect = _set_attr(rect, "width", _fmt(nw))
            rect = _set_attr(rect, "height", _fmt(nh))
            _rect_repl.done = True
        return rect

    _rect_repl.done = False
    raw = re.sub(r"<rect\b[^>]*?/?>", _rect_repl, raw, count=1)

    return raw, f"viewBox {old_vb} -> {new_vb}" + (
        "" if _rect_repl.done else " (no background rect adjusted)")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Auto-fit SVG viewBox so nothing is clipped.")
    ap.add_argument("inputs", nargs="+", help=".svg files, a directory, or a course .json")
    ap.add_argument("--margin", type=float, default=10.0, help="padding around content (default 10)")
    ap.add_argument("-o", "--output", help="output path (only with a single input file)")
    ap.add_argument("--dry-run", action="store_true", help="report changes without writing")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

    paths = _iter_svg_paths(args.inputs)
    if not paths:
        print("No SVG files found.")
        return 1
    if args.output and len(paths) != 1:
        print("ERROR: -o/--output only works with a single input SVG.")
        return 1

    changed = 0
    for p in paths:
        with open(p, encoding="utf-8") as fh:
            raw = fh.read()
        try:
            new_raw, msg = fit_svg(raw, args.margin)
        except Exception as e:  # noqa: BLE001
            print(f"{p}: ERROR {e}")
            continue
        if msg is None:
            print(f"{p}: already fits")
            continue
        changed += 1
        dst = args.output or p
        if args.dry_run:
            print(f"{p}: would change {msg}")
        else:
            with open(dst, "w", encoding="utf-8") as fh:
                fh.write(new_raw)
            print(f"{dst}: {msg}")

    print(f"\n{len(paths)} file(s), {changed} changed"
          + (" (dry-run)" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
