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

import math
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


def _arc_points(p0, rx, ry, rot_deg, laf, swf, p1, n=12):
    """Sample-Punkte eines elliptischen Bogens (W3C endpoint->center)."""
    x1, y1 = p0
    x2, y2 = p1
    if rx == 0 or ry == 0 or (x1, y1) == (x2, y2):
        return [p1]
    rx, ry = abs(rx), abs(ry)
    phi = math.radians(rot_deg)
    cp, sp = math.cos(phi), math.sin(phi)
    dx, dy = (x1 - x2) / 2.0, (y1 - y2) / 2.0
    x1p = cp * dx + sp * dy
    y1p = -sp * dx + cp * dy
    lam = x1p ** 2 / rx ** 2 + y1p ** 2 / ry ** 2
    if lam > 1:
        s = math.sqrt(lam)
        rx *= s
        ry *= s
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    num = rx * rx * ry * ry - den
    co = math.sqrt(max(num, 0.0) / den) if den else 0.0
    if laf == swf:
        co = -co
    cxp = co * rx * y1p / ry
    cyp = -co * ry * x1p / rx
    cx = cp * cxp - sp * cyp + (x1 + x2) / 2.0
    cy = sp * cxp + cp * cyp + (y1 + y2) / 2.0

    def ang(ux, uy, vx, vy):
        d = math.hypot(ux, uy) * math.hypot(vx, vy)
        a = math.acos(max(-1.0, min(1.0, (ux * vx + uy * vy) / d))) if d else 0.0
        return -a if ux * vy - uy * vx < 0 else a

    th1 = ang(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    dth = ang((x1p - cxp) / rx, (y1p - cyp) / ry,
              (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not swf and dth > 0:
        dth -= 2 * math.pi
    elif swf and dth < 0:
        dth += 2 * math.pi
    out = []
    for k in range(1, n + 1):
        t = th1 + dth * k / n
        out.append((cx + rx * math.cos(t) * cp - ry * math.sin(t) * sp,
                    cy + rx * math.cos(t) * sp + ry * math.sin(t) * cp))
    out[-1] = (x2, y2)
    return out


def _path_points(d: str) -> list:
    """Geordnete Sample-Punkte eines path-``d`` (M/L/H/V/C/S/Q/T/A). Kurven
    werden abgetastet, damit BBox UND Kreuzungs-Checks die echte Geometrie
    sehen. Naives Zahlen-Paaren zaehlte bei ``A`` Radien und Flags als Punkte
    (Phantom-Punkt bei y=725) und sah Kurvenbaeuche gar nicht."""
    pts = []
    cur = (0.0, 0.0)

    def absol(rel, x, y):
        return (cur[0] + x, cur[1] + y) if rel else (x, y)

    for cmd, body in re.findall(r"([MmLlHhVvCcSsQqTtAaZz])([^A-Za-z]*)", d):
        nums = [float(v) for v in re.findall(r"-?\d*\.?\d+(?:e-?\d+)?", body)]
        u, rel = cmd.upper(), cmd.islower()
        if u in ("M", "L", "T"):
            for i in range(0, len(nums) - 1, 2):
                cur = absol(rel, nums[i], nums[i + 1])
                pts.append(cur)
        elif u == "H":
            for v in nums:
                cur = ((cur[0] + v) if rel else v, cur[1])
                pts.append(cur)
        elif u == "V":
            for v in nums:
                cur = (cur[0], (cur[1] + v) if rel else v)
                pts.append(cur)
        elif u == "Q":
            for i in range(0, len(nums) - 3, 4):
                c = absol(rel, nums[i], nums[i + 1])
                e = absol(rel, nums[i + 2], nums[i + 3])
                p0 = cur
                for k in range(1, 9):
                    t = k / 8.0
                    mt = 1 - t
                    pts.append((mt * mt * p0[0] + 2 * mt * t * c[0] + t * t * e[0],
                                mt * mt * p0[1] + 2 * mt * t * c[1] + t * t * e[1]))
                cur = e
        elif u in ("C", "S"):
            step = 6 if u == "C" else 4
            for i in range(0, len(nums) - step + 1, step):
                if u == "C":
                    c1 = absol(rel, nums[i], nums[i + 1])
                    c2 = absol(rel, nums[i + 2], nums[i + 3])
                    e = absol(rel, nums[i + 4], nums[i + 5])
                else:
                    c1 = cur
                    c2 = absol(rel, nums[i], nums[i + 1])
                    e = absol(rel, nums[i + 2], nums[i + 3])
                p0 = cur
                for k in range(1, 9):
                    t = k / 8.0
                    mt = 1 - t
                    pts.append((mt ** 3 * p0[0] + 3 * mt * mt * t * c1[0]
                                + 3 * mt * t * t * c2[0] + t ** 3 * e[0],
                                mt ** 3 * p0[1] + 3 * mt * mt * t * c1[1]
                                + 3 * mt * t * t * c2[1] + t ** 3 * e[1]))
                cur = e
        elif u == "A":
            for i in range(0, len(nums) - 6, 7):
                e = absol(rel, nums[i + 5], nums[i + 6])
                pts.extend(_arc_points(cur, nums[i], nums[i + 1], nums[i + 2],
                                       nums[i + 3], nums[i + 4], e))
                cur = e
    return pts


def _path_coords(d: str) -> tuple[list, list]:
    """xs/ys der gesampelten Pfad-Punkte (siehe ``_path_points``)."""
    pts = _path_points(d)
    return [p[0] for p in pts], [p[1] for p in pts]


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
                                        "anchor": anchor, "size": size,
                                        "ax": x, "fill": el.get("fill")}))
        elif name == "rect":
            x = _num(el.get("x")) + tx
            y = _num(el.get("y")) + ty
            boxes.append(Box(x, y, x + _num(el.get("width")),
                             y + _num(el.get("height")), "rect",
                             extra={"fill": el.get("fill")}))
        elif name == "circle":
            cx, cy, r = _num(el.get("cx")) + tx, _num(el.get("cy")) + ty, _num(el.get("r"))
            boxes.append(Box(cx - r, cy - r, cx + r, cy + r, "circle",
                             extra={"fill": el.get("fill")}))
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
                shifted = [(x + tx, y + ty) for x, y in zip(xs, ys)]
                if name == "polygon" and len(shifted) > 1:
                    shifted.append(shifted[0])
                closed = (name == "polygon") or (
                    len(shifted) > 2 and math.hypot(
                        shifted[0][0] - shifted[-1][0],
                        shifted[0][1] - shifted[-1][1]) <= 0.5)
                boxes.append(Box(min(xs) + tx, min(ys) + ty,
                                 max(xs) + tx, max(ys) + ty, name,
                                 extra={"pts": shifted, "path_closed": closed}))
        elif name == "path":
            d = el.get("d", "")
            pts = _path_points(d)
            if pts:
                shifted = [(x + tx, y + ty) for x, y in pts]
                xs = [p[0] for p in shifted]
                ys = [p[1] for p in shifted]
                closed = bool(re.search(r"[Zz]", d)) or (
                    len(shifted) > 2 and math.hypot(
                        shifted[0][0] - shifted[-1][0],
                        shifted[0][1] - shifted[-1][1]) <= 0.5)
                boxes.append(Box(min(xs), min(ys), max(xs), max(ys), "path",
                                 extra={"pts": shifted, "path_closed": closed,
                                        "fill": el.get("fill")}))

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
