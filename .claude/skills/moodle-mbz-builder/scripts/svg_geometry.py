#!/usr/bin/env python3
"""Shared SVG geometry helpers for the moodle-mbz-builder tooling.

The core problem this solves: when a diagram is hand-authored with absolute
coordinates, text can silently overflow the ``viewBox`` (→ clipped edges) or
collide with a neighbour (→ hidden content), because nothing measures how wide
a string actually renders. We CAN measure it: ``reportlab``'s
``pdfmetrics.stringWidth`` gives the exact width for a font, and svglib (the
renderer used everywhere in this skill) maps Arial/Helvetica/sans-serif onto
Helvetica, for which reportlab ships built-in metrics. So the measured width
matches the rendered width closely.

This module parses an SVG, resolves inherited presentation attributes
(font-size, font-family, font-weight, font-style, text-anchor — these are
frequently set on a parent ``<g>``), and returns a bounding box in user units
for every drawable element, plus the viewBox. ``validate_svg.py`` uses it to
lint; ``autofit_svg.py`` uses it to grow the viewBox to fit.

Supported elements: text (incl. concatenated tspan content), rect, circle,
ellipse, line, polyline, polygon, and a best-effort path (numeric coords of the
``d`` attribute). ``translate(...)`` transforms are applied; other transforms
are ignored with the element flagged so callers can warn.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

try:
    from reportlab.pdfbase.pdfmetrics import stringWidth
except Exception as e:  # noqa: BLE001
    # Raise ImportError (an Exception), NOT SystemExit: callers that embed the
    # SVG check (build_mbz.py) catch Exception to skip gracefully, while a
    # deliberate --strict-svg abort uses SystemExit. Keeping these distinct means
    # a colleague without reportlab still gets a working build (check skipped),
    # not an aborted one.
    raise ImportError(
        "svg_geometry needs reportlab for text measurement "
        "(python -m pip install reportlab)"
    ) from e

SVG_NS = "http://www.w3.org/2000/svg"

# presentation attributes that inherit down the tree and that we care about
_INHERIT = ("font-size", "font-family", "font-weight", "font-style",
            "text-anchor", "fill")


@dataclass
class Box:
    """Axis-aligned bounding box + provenance for reporting."""
    x0: float
    y0: float
    x1: float
    y1: float
    tag: str
    label: str = ""            # short human description (e.g. text content)
    line: int = 0              # source line number, when available
    extra: dict = field(default_factory=dict)

    @property
    def w(self) -> float:
        return self.x1 - self.x0

    @property
    def h(self) -> float:
        return self.y1 - self.y0

    def overlaps(self, other: "Box", eps: float = 2.0) -> tuple[float, float]:
        """Return (overlap_w, overlap_h); both > eps means a real overlap."""
        ow = min(self.x1, other.x1) - max(self.x0, other.x0)
        oh = min(self.y1, other.y1) - max(self.y0, other.y0)
        return ow, oh


def _localname(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


def _num(v, default=0.0):
    if v is None:
        return default
    m = re.match(r"\s*(-?\d*\.?\d+)", str(v))
    return float(m.group(1)) if m else default


def font_name(family: str, weight: str, style: str) -> str:
    """Map CSS-ish font props onto a reportlab base-14 Helvetica variant,
    mirroring how svglib resolves them."""
    fam = (family or "").lower()
    weight = (weight or "").lower()
    style = (style or "").lower()
    bold = "bold" in weight or (weight.isdigit() and int(weight) >= 600)
    italic = "italic" in style or "oblique" in style
    if "times" in fam or "serif" in fam and "sans" not in fam:
        base = "Times"
        if bold and italic:
            return "Times-BoldItalic"
        if bold:
            return "Times-Bold"
        if italic:
            return "Times-Italic"
        return "Times-Roman"
    if "courier" in fam or "mono" in fam:
        base = "Courier"
    else:
        base = "Helvetica"
    if bold and italic:
        return f"{base}-BoldOblique"
    if bold:
        return f"{base}-Bold"
    if italic:
        return f"{base}-Oblique"
    return base


def _text_content(el: ET.Element) -> str:
    """Concatenate the element's own text and all descendant tspan text,
    matching what a renderer draws for the element."""
    parts = []
    if el.text:
        parts.append(el.text)
    for child in el:
        if _localname(child.tag) == "tspan":
            if child.text:
                parts.append(child.text)
        if child.tail:
            parts.append(child.tail)
    return "".join(parts)


def _path_coords(d: str) -> tuple[list, list]:
    """Best-effort Koordinaten eines path-``d``: pro Befehl nur die ECHTEN
    Koordinaten einsammeln. Naives Zahlen-Paaren zaehlt bei ``A`` die Radien
    und Flags als Punkte (ein ``A 62 62 0 0 1 725 175`` erzeugt sonst einen
    Phantom-Punkt bei y=725 und blaeht die viewBox auf)."""
    xs, ys = [], []
    for cmd, body in re.findall(r"([MmLlHhVvCcSsQqTtAaZz])([^A-Za-z]*)", d):
        nums = [float(v) for v in re.findall(r"-?\d*\.?\d+(?:e-?\d+)?", body)]
        u = cmd.upper()
        if u == "A":
            # Gruppen aus 7 Parametern: rx ry rot large-arc sweep x y
            for i in range(6, len(nums), 7):
                xs.append(nums[i - 1]); ys.append(nums[i])
        elif u == "H":
            xs.extend(nums)
        elif u == "V":
            ys.extend(nums)
        elif u != "Z":
            xs.extend(nums[0::2]); ys.extend(nums[1::2])
    return xs, ys


def _parse_translate(transform: str) -> tuple[float, float]:
    if not transform:
        return 0.0, 0.0
    m = re.search(r"translate\(\s*(-?\d*\.?\d+)[ ,]+(-?\d*\.?\d+)?", transform)
    if not m:
        return 0.0, 0.0
    return float(m.group(1)), float(m.group(2) or 0.0)


def get_viewbox(root: ET.Element):
    vb = root.get("viewBox")
    if vb:
        p = re.split(r"[ ,]+", vb.strip())
        if len(p) == 4:
            x, y, w, h = (float(v) for v in p)
            return x, y, w, h
    # fall back to width/height
    w = _num(root.get("width"), 0.0)
    h = _num(root.get("height"), 0.0)
    return 0.0, 0.0, w, h


def collect_boxes(root: ET.Element):
    """Walk the tree and return a list[Box] for every drawable element,
    resolving inherited style and translate() transforms."""
    boxes: list[Box] = []

    def walk(el: ET.Element, inh: dict, tx: float, ty: float):
        style = dict(inh)
        for k in _INHERIT:
            if el.get(k) is not None:
                style[k] = el.get(k)
        dx, dy = _parse_translate(el.get("transform", ""))
        tx, ty = tx + dx, ty + dy
        name = _localname(el.tag)

        if name == "text":
            txt = _text_content(el)
            if txt.strip():
                size = _num(style.get("font-size"), 12.0)
                fn = font_name(style.get("font-family", ""),
                               style.get("font-weight", ""),
                               style.get("font-style", ""))
                try:
                    w = stringWidth(txt, fn, size)
                except Exception:  # noqa: BLE001 - unknown glyph etc.
                    w = size * 0.5 * len(txt)
                x = _num(el.get("x")) + tx
                y = _num(el.get("y")) + ty
                anchor = style.get("text-anchor", "start")
                if anchor == "middle":
                    x0, x1 = x - w / 2, x + w / 2
                elif anchor == "end":
                    x0, x1 = x - w, x
                else:
                    x0, x1 = x, x + w
                # baseline y: ascent ~0.8, descent ~0.2 of the font size
                boxes.append(Box(x0, y - size * 0.8, x1, y + size * 0.2,
                                 "text", txt.strip()[:60],
                                 extra={"styled_tspan": _has_styled_tspan(el),
                                        "anchor": anchor}))
        elif name == "rect":
            x = _num(el.get("x")) + tx
            y = _num(el.get("y")) + ty
            boxes.append(Box(x, y, x + _num(el.get("width")),
                             y + _num(el.get("height")), "rect"))
        elif name == "circle":
            cx, cy, r = _num(el.get("cx")) + tx, _num(el.get("cy")) + ty, _num(el.get("r"))
            boxes.append(Box(cx - r, cy - r, cx + r, cy + r, "circle"))
        elif name == "ellipse":
            cx, cy = _num(el.get("cx")) + tx, _num(el.get("cy")) + ty
            rx, ry = _num(el.get("rx")), _num(el.get("ry"))
            boxes.append(Box(cx - rx, cy - ry, cx + rx, cy + ry, "ellipse"))
        elif name == "line":
            x1, y1 = _num(el.get("x1")) + tx, _num(el.get("y1")) + ty
            x2, y2 = _num(el.get("x2")) + tx, _num(el.get("y2")) + ty
            boxes.append(Box(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2),
                             "line", extra={"seg": (x1, y1, x2, y2)}))
        elif name in ("polyline", "polygon"):
            pts = [float(v) for v in re.findall(r"-?\d*\.?\d+", el.get("points", ""))]
            xs, ys = pts[0::2], pts[1::2]
            if xs and ys:
                boxes.append(Box(min(xs) + tx, min(ys) + ty,
                                 max(xs) + tx, max(ys) + ty, name))
        elif name == "path":
            xs, ys = _path_coords(el.get("d", ""))
            if xs and ys:
                boxes.append(Box(min(xs) + tx, min(ys) + ty,
                                 max(xs) + tx, max(ys) + ty, "path"))

        for child in el:
            if _localname(child.tag) != "tspan":
                walk(child, style, tx, ty)

    walk(root, {}, 0.0, 0.0)
    return boxes


def _has_styled_tspan(el: ET.Element) -> bool:
    """True if a child tspan carries its own styling — svglib does not advance
    the x cursor across tspans, so styled inline fragments render on top of the
    following text (a known overlap trap)."""
    for child in el:
        if _localname(child.tag) == "tspan":
            if any(child.get(a) for a in
                   ("font-weight", "font-style", "font-size", "fill", "dx", "dy")):
                if child.get("x") is None:  # no explicit x => overlaps
                    return True
    return False


def fromstring(raw: str) -> ET.Element:
    """Parse SVG source text → root element."""
    return ET.fromstring(raw)


def load(path: str):
    """Parse an SVG file → (ElementTree root, raw_text)."""
    with open(path, "r", encoding="utf-8") as fh:
        raw = fh.read()
    root = ET.fromstring(raw)
    return root, raw


def content_bounds(boxes):
    """Union bbox of all boxes, or None if empty."""
    if not boxes:
        return None
    return (min(b.x0 for b in boxes), min(b.y0 for b in boxes),
            max(b.x1 for b in boxes), max(b.y1 for b in boxes))
