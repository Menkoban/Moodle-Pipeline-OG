# Diagramm-Validatoren (V1/V3/V4a) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three diagram checks to the moodle-mbz-builder SVG linter — axis labels (V1) and scale (V3) on explicitly-marked charts, and unclosed-figure detection (V4a) on all diagrams.

**Architecture:** Extend the existing `scripts/validate_svg.py` linter (no new script) with warn-level checks that run everywhere the SVG check already runs, plus a one-line `path_closed` flag in `scripts/svg_geometry.py`. Charts opt in via a root attribute `data-diagram-type="chart"`; only marked charts get axis/scale checks, so schematics never false-alarm. Overshoot detection (V4b) is deferred to a follow-up (it false-positives on tick marks).

**Tech Stack:** Python 3.11, `xml.etree.ElementTree`, `reportlab` (text metrics via `svg_geometry`), `pytest`.

## Global Constraints

- All new checks are **warn-level** (`warns.append(...)`), never `errors`.
- `validate_svg.py --strict` is a **pipeline gate** (SKILL.md Schritt 2) → any warn fails it. Therefore the **hard acceptance criterion**: **0 new warnings** on the existing good SVG corpus (`assets/*.svg` + all `Moodle-Kurse/*/assets/*.svg`).
- Chart marker is the **exact** string attribute on the root `<svg>`: `data-diagram-type="chart"`.
- New message keywords, existing style (leading uppercase): `ACHSE`, `SKALA`, `FIGUR`.
- Windows paths with spaces must be **quoted** (e.g. `"C:/Users/User/OneDrive - HSOS/Desktop/Moodle-Kurse"`).
- Tests follow the repo pattern: `sys.path.insert(0, .../scripts)`, then `from validate_svg import lint_file` / `import svg_geometry as G`.
- Skill repo root for all paths below: `C:/Users/User/.claude/skills/moodle-mbz-builder`. Work on branch `feature/diagramm-validatoren`.

---

### Task 1: `path_closed` flag in svg_geometry

**Files:**
- Modify: `scripts/svg_geometry.py` (the `path` and `polyline`/`polygon` branches of `collect_boxes`)
- Test: `tests/test_svg_geometry_closed.py` (create)

**Interfaces:**
- Consumes: `G.fromstring(raw)`, `G.collect_boxes(root)`, `Box.extra` dict.
- Produces: for every `path`, `polyline`, `polygon` Box, `extra["path_closed"]: bool` — True if the shape is closed (a `Z`/`z` in a path `d`, a `polygon`, or first sample point ≈ last within 0.5 px).

- [ ] **Step 1: Write the failing test**

Create `tests/test_svg_geometry_closed.py`:

```python
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import svg_geometry as G


def _boxes(body):
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
           + body + "</svg>")
    return G.collect_boxes(G.fromstring(svg))


def test_path_with_z_is_closed():
    boxes = _boxes('<path d="M 10 10 L 90 10 L 90 90 Z" fill="none" stroke="#000"/>')
    paths = [b for b in boxes if b.tag == "path"]
    assert paths and paths[0].extra.get("path_closed") is True


def test_open_path_is_not_closed():
    boxes = _boxes('<path d="M 10 10 L 90 10 L 90 84" fill="none" stroke="#000"/>')
    paths = [b for b in boxes if b.tag == "path"]
    assert paths and paths[0].extra.get("path_closed") is False


def test_polygon_is_closed():
    boxes = _boxes('<polygon points="10,10 90,10 50,90" fill="none" stroke="#000"/>')
    polys = [b for b in boxes if b.tag == "polygon"]
    assert polys and polys[0].extra.get("path_closed") is True


def test_open_polyline_is_not_closed():
    boxes = _boxes('<polyline points="10,10 90,10 90,84" fill="none" stroke="#000"/>')
    pls = [b for b in boxes if b.tag == "polyline"]
    assert pls and pls[0].extra.get("path_closed") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "C:/Users/User/.claude/skills/moodle-mbz-builder" && python -m pytest tests/test_svg_geometry_closed.py -v`
Expected: FAIL — `path_closed` is `None` (key missing), assertions fail.

- [ ] **Step 3: Implement — add `path_closed` to both branches**

In `scripts/svg_geometry.py`, the `polyline`/`polygon` branch currently reads:

```python
        elif name in ("polyline", "polygon"):
            pts = [float(v) for v in re.findall(r"-?\d*\.?\d+", el.get("points", ""))]
            xs, ys = pts[0::2], pts[1::2]
            if xs and ys:
                shifted = [(x + tx, y + ty) for x, y in zip(xs, ys)]
                if name == "polygon" and len(shifted) > 1:
                    shifted.append(shifted[0])
                boxes.append(Box(min(xs) + tx, min(ys) + ty,
                                 max(xs) + tx, max(ys) + ty, name,
                                 extra={"pts": shifted}))
```

Replace its `boxes.append(...)` with a version that adds `path_closed`:

```python
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
```

The `path` branch currently reads:

```python
        elif name == "path":
            pts = _path_points(el.get("d", ""))
            if pts:
                shifted = [(x + tx, y + ty) for x, y in pts]
                xs = [p[0] for p in shifted]
                ys = [p[1] for p in shifted]
                boxes.append(Box(min(xs), min(ys), max(xs), max(ys), "path",
                                 extra={"pts": shifted}))
```

Replace it with:

```python
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
                                 extra={"pts": shifted, "path_closed": closed}))
```

(`math` and `re` are already imported at the top of `svg_geometry.py`.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "C:/Users/User/.claude/skills/moodle-mbz-builder" && python -m pytest tests/test_svg_geometry_closed.py tests/test_svg_geometry_paths.py -v`
Expected: all PASS (new file green, existing geometry tests still green).

- [ ] **Step 5: Commit**

```bash
cd "C:/Users/User/.claude/skills/moodle-mbz-builder"
git add scripts/svg_geometry.py tests/test_svg_geometry_closed.py
git commit -m "feat(svg): path_closed flag on path/polyline/polygon boxes

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: V4a — unclosed-figure check (all diagrams)

**Files:**
- Modify: `scripts/validate_svg.py` (add `import math`; add `_figure_closure_warnings`; call it in `lint_file`)
- Test: `tests/test_validate_svg_charts.py` (create — shared with Tasks 3–4)

**Interfaces:**
- Consumes: `Box.extra["pts"]`, `Box.extra["path_closed"]` (Task 1), `Box.w`, `Box.h`, `lint_file(path) -> (errors, warns)`.
- Produces: `_figure_closure_warnings(boxes) -> list[str]`; adds `FIGUR …` strings to `warns` from `lint_file`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_validate_svg_charts.py`:

```python
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from validate_svg import lint_file


def _write(tmp_path, body, chart=False):
    marker = ' data-diagram-type="chart"' if chart else ""
    p = tmp_path / "t.svg"
    p.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" '
        'font-family="Helvetica"' + marker + ">" + body + "</svg>",
        encoding="utf-8")
    return str(p)


# ---- V4a: unclosed figures -------------------------------------------------

def test_open_box_path_is_flagged(tmp_path):
    # Rectangle drawn as an open path with a ~6px gap back to the start.
    p = _write(tmp_path,
               '<path d="M 40 40 L 200 40 L 200 200 L 40 200 L 40 46" '
               'fill="none" stroke="#000"/>')
    errors, warns = lint_file(p)
    assert any("FIGUR" in w for w in warns), warns


def test_closed_box_path_is_clean(tmp_path):
    p = _write(tmp_path,
               '<path d="M 40 40 L 200 40 L 200 200 L 40 200 Z" '
               'fill="none" stroke="#000"/>')
    errors, warns = lint_file(p)
    assert not any("FIGUR" in w for w in warns), warns


def test_open_function_graph_is_not_flagged(tmp_path):
    # A plotted curve: endpoints far apart -> not an unclosed figure.
    p = _write(tmp_path,
               '<polyline points="40,200 100,120 160,150 220,80 300,110" '
               'fill="none" stroke="#000"/>')
    errors, warns = lint_file(p)
    assert not any("FIGUR" in w for w in warns), warns
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "C:/Users/User/.claude/skills/moodle-mbz-builder" && python -m pytest tests/test_validate_svg_charts.py -v`
Expected: `test_open_box_path_is_flagged` FAILS (no `FIGUR` warn yet); the two "clean" tests pass trivially.

- [ ] **Step 3: Implement V4a**

In `scripts/validate_svg.py`, add `import math` to the import block (after `import json`):

```python
import argparse
import glob
import json
import math
import os
import sys
```

Add this helper near the bottom, **before** `def check_course_svgs(`:

```python
def _figure_closure_warnings(boxes):
    """V4a — an open path/polyline outline whose start and end nearly meet is
    likely an unclosed figure. Conservative: only 2–12px gaps on a 2D figure
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
```

In `lint_file`, immediately before `return errors, warns` (right after the section-10 contrast block), add:

```python
    # 11) V4a: geschlossene Figuren (alle Diagramme)
    warns += _figure_closure_warnings(boxes)

    return errors, warns
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "C:/Users/User/.claude/skills/moodle-mbz-builder" && python -m pytest tests/test_validate_svg_charts.py tests/test_validate_svg_paths.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
cd "C:/Users/User/.claude/skills/moodle-mbz-builder"
git add scripts/validate_svg.py tests/test_validate_svg_charts.py
git commit -m "feat(svg): V4a warn for unclosed path/polyline figures

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Chart marker + V1 axis-label check

**Files:**
- Modify: `scripts/validate_svg.py` (read marker in `lint_file`; add `_segments`, `_find_axes`, `_chart_axis_warnings` with V1; call it)
- Test: `tests/test_validate_svg_charts.py` (extend)

**Interfaces:**
- Consumes: `G.load` root element, `Box.extra["seg"]` (line), `Box.extra["pts"]` (path/polyline/polygon), viewBox `(vx, vy, vw, vh)`.
- Produces:
  - `_segments(boxes) -> list[tuple[float,float,float,float]]` — all straight segments.
  - `_find_axes(boxes, vx, vy, vw, vh) -> (x_axis|None, y_axis|None)` where each axis is `(x1,y1,x2,y2)`.
  - `_chart_axis_warnings(boxes, vx, vy, vw, vh) -> list[str]` — `ACHSE …` / (Task 4) `SKALA …` strings.
  - `is_chart` local in `lint_file` gating the call.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_validate_svg_charts.py`:

```python
# ---- shared chart fixtures for V1/V3 ---------------------------------------

# A well-formed marked chart: L-shaped axes (path), x/y scale numbers, x/y titles.
_GOOD_CHART = (
    '<path d="M 60 20 L 60 260 L 380 260" fill="none" stroke="#000"/>'
    '<text x="60" y="275" font-size="12">0</text>'
    '<text x="200" y="275" font-size="12">5</text>'
    '<text x="340" y="275" font-size="12">10</text>'
    '<text x="45" y="262" font-size="12" text-anchor="end">0</text>'
    '<text x="45" y="140" font-size="12" text-anchor="end">50</text>'
    '<text x="45" y="34" font-size="12" text-anchor="end">100</text>'
    '<text x="210" y="292" font-size="12">t in s</text>'
    '<text x="16" y="140" font-size="12">U in V</text>'
)


def test_good_chart_is_clean(tmp_path):
    p = _write(tmp_path, _GOOD_CHART, chart=True)
    errors, warns = lint_file(p)
    assert not any(w.startswith(("ACHSE", "SKALA")) for w in warns), warns


def test_chart_missing_x_title_flags_achse(tmp_path):
    body = _GOOD_CHART.replace(
        '<text x="210" y="292" font-size="12">t in s</text>', "")
    p = _write(tmp_path, body, chart=True)
    errors, warns = lint_file(p)
    assert any(w.startswith("ACHSE") and "x-Achse" in w for w in warns), warns
    assert not any(w.startswith("ACHSE") and "y-Achse" in w for w in warns), warns


def test_unmarked_chartlike_svg_has_no_axis_warnings(tmp_path):
    # Same drawing WITHOUT the marker and without titles: must not trip V1/V3.
    body = (
        '<path d="M 60 20 L 60 260 L 380 260" fill="none" stroke="#000"/>'
        '<text x="60" y="275" font-size="12">0</text>'
        '<text x="200" y="275" font-size="12">5</text>'
    )
    p = _write(tmp_path, body, chart=False)
    errors, warns = lint_file(p)
    assert not any(w.startswith(("ACHSE", "SKALA")) for w in warns), warns
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "C:/Users/User/.claude/skills/moodle-mbz-builder" && python -m pytest tests/test_validate_svg_charts.py -v`
Expected: `test_chart_missing_x_title_flags_achse` FAILS (no `ACHSE` warn); `test_good_chart_is_clean` and `test_unmarked_chartlike_svg_has_no_axis_warnings` pass trivially (no checks yet).

- [ ] **Step 3: Implement marker read + axis detection + V1**

In `scripts/validate_svg.py`, add near the other module-level regexes (after `MIN_FONT_SIZE`/`CENTER_TOL`/`ALIGN_TOL` definitions):

```python
_NUMERIC_RX = re.compile(r"^-?\d+(?:[.,]\d+)?$")
```

Add these helpers **before** `def _figure_closure_warnings(`:

```python
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
```

In `lint_file`, read the marker right after the viewBox is known. The current start of `lint_file` is:

```python
    vx, vy, vw, vh = G.get_viewbox(root)
    vx1, vy1 = vx + vw, vy + vh
    boxes = G.collect_boxes(root)
```

Change it to:

```python
    is_chart = (root.get("data-diagram-type") == "chart")
    vx, vy, vw, vh = G.get_viewbox(root)
    vx1, vy1 = vx + vw, vy + vh
    boxes = G.collect_boxes(root)
```

Then extend the block added in Task 2 so the chart checks run first:

```python
    # 11) V1/V3: Chart-Achsen + Skala (nur markierte Charts)
    if is_chart:
        warns += _chart_axis_warnings(boxes, vx, vy, vw, vh)

    # 12) V4a: geschlossene Figuren (alle Diagramme)
    warns += _figure_closure_warnings(boxes)

    return errors, warns
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "C:/Users/User/.claude/skills/moodle-mbz-builder" && python -m pytest tests/test_validate_svg_charts.py -v`
Expected: all PASS (good chart clean, missing-x-title flagged on x only, unmarked svg silent).

- [ ] **Step 5: Commit**

```bash
cd "C:/Users/User/.claude/skills/moodle-mbz-builder"
git add scripts/validate_svg.py tests/test_validate_svg_charts.py
git commit -m "feat(svg): V1 axis-label check for marked charts (data-diagram-type)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: V3 — axis scale check

**Files:**
- Modify: `scripts/validate_svg.py` (extend `_chart_axis_warnings` with numeric-value counting)
- Test: `tests/test_validate_svg_charts.py` (extend)

**Interfaces:**
- Consumes: `_chart_axis_warnings`, `_find_axes`, `is_num`, `cx`, `cy` (Task 3).
- Produces: `SKALA <x|y>-Achse ohne Skalierung (< 2 numerische Werte)` warns.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_validate_svg_charts.py`:

```python
def test_chart_missing_y_scale_flags_skala(tmp_path):
    # Drop two of the three y-axis numbers -> only one numeric value left.
    body = (_GOOD_CHART
            .replace('<text x="45" y="140" font-size="12" text-anchor="end">50</text>', "")
            .replace('<text x="45" y="34" font-size="12" text-anchor="end">100</text>', ""))
    p = _write(tmp_path, body, chart=True)
    errors, warns = lint_file(p)
    assert any(w.startswith("SKALA") and "y-Achse" in w for w in warns), warns
    assert not any(w.startswith("SKALA") and "x-Achse" in w for w in warns), warns
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "C:/Users/User/.claude/skills/moodle-mbz-builder" && python -m pytest tests/test_validate_svg_charts.py::test_chart_missing_y_scale_flags_skala -v`
Expected: FAIL — no `SKALA` warn yet.

- [ ] **Step 3: Implement V3**

In `_chart_axis_warnings`, inside the `else` branch for `x_axis` (after the x-title check), add the scale count:

```python
    else:
        ax_y = (x_axis[1] + x_axis[3]) / 2.0
        if not any((not is_num(t)) and cy(t) > ax_y for t in texts):
            warns.append("ACHSE x-Achse ohne Beschriftung (Achsentitel fehlt)")
        if sum(1 for t in texts if is_num(t) and cy(t) > ax_y) < 2:
            warns.append("SKALA x-Achse ohne Skalierung (< 2 numerische Werte)")
```

And inside the `else` branch for `y_axis` (after the y-title check), add:

```python
    else:
        ax_x = (y_axis[0] + y_axis[2]) / 2.0
        if not any((not is_num(t)) and cx(t) < vx + vw / 3.0 for t in texts):
            warns.append("ACHSE y-Achse ohne Beschriftung (Achsentitel fehlt)")
        if sum(1 for t in texts if is_num(t) and cx(t) < ax_x) < 2:
            warns.append("SKALA y-Achse ohne Skalierung (< 2 numerische Werte)")
```

(Note: the y-branch now needs `ax_x = (y_axis[0] + y_axis[2]) / 2.0` — add it as shown. The x-branch already computes `ax_y`.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "C:/Users/User/.claude/skills/moodle-mbz-builder" && python -m pytest tests/test_validate_svg_charts.py -v`
Expected: all PASS — including `test_good_chart_is_clean` (3 x-values, 3 y-values → no SKALA) and the new y-scale test (1 y-value → SKALA y only).

- [ ] **Step 5: Commit**

```bash
cd "C:/Users/User/.claude/skills/moodle-mbz-builder"
git add scripts/validate_svg.py tests/test_validate_svg_charts.py
git commit -m "feat(svg): V3 axis-scale check (>=2 numeric values per axis)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Documentation — authoring rules + docstring

**Files:**
- Modify: `references/course-design.md` (SVG-Autorenregeln section)
- Modify: `scripts/validate_svg.py` (module docstring "Checks per SVG" list)

**Interfaces:** none (docs only).

- [ ] **Step 1: Update the validate_svg docstring**

In `scripts/validate_svg.py`, the module docstring lists the checks (`* OVERFLOW …`, `* OVERLAP …`, …). Add these three lines to that list, after the `* TSPAN` entry:

```
  * ACHSE  (warn) — a diagram marked data-diagram-type="chart" is missing an
    axis line, or an axis title (a non-numeric label) on the x or y axis.
  * SKALA  (warn) — such a chart has fewer than 2 numeric scale values on an axis.
  * FIGUR  (warn) — an open path/polyline outline whose start and end nearly
    meet (2–12px gap on a 2D figure) — likely an unclosed figure; close with Z.
```

- [ ] **Step 2: Add the authoring rules**

Open `references/course-design.md`, find the "SVG-Autorenregeln" section (referenced from SKILL.md). Append this block at the end of that section:

```markdown
### Koordinaten-Diagramme (Charts) — Achsen, Skala, geschlossene Figuren

- **Chart markieren:** Ein Diagramm mit Koordinatenachsen (Kennlinie,
  Messkurve, Balken über einer Werteachse) bekommt am Wurzel-`<svg>` das
  Attribut `data-diagram-type="chart"`. Nur so prüft `validate_svg.py` die
  Achsen — Schaltpläne, Anatomiebilder und Piktogramme bleiben unberührt.
- **Achsentitel (Pflicht bei Charts):** jede Achse braucht einen beschrifteten
  Titel mit Größe/Einheit (z. B. „t in s", „U / V", „Kraft F") — nicht nur
  Zahlen. Fehlt er → Warnung `ACHSE`.
- **Skalierung (Pflicht bei Charts):** jede Achse braucht mindestens zwei
  numerische Skalenwerte entlang der Achse (Teilstriche zusätzlich empfohlen).
  Weniger als zwei → Warnung `SKALA`.
- **Figuren schließen (alle Diagramme):** geschlossene Formen als `polygon`
  oder als `path` mit abschließendem `Z` zeichnen, nicht als offene Linienkette
  mit einer kleinen Lücke. Eine Restlücke von 2–12 px → Warnung `FIGUR`.

Alle drei sind warn-Level und blocken damit das `validate_svg.py --strict`-Gate.
```

(If the exact "SVG-Autorenregeln" heading text differs, append under the nearest SVG/diagram authoring section — keep the block intact.)

- [ ] **Step 3: Commit**

```bash
cd "C:/Users/User/.claude/skills/moodle-mbz-builder"
git add scripts/validate_svg.py references/course-design.md
git commit -m "docs(svg): authoring rules for chart axes/scale/closed figures

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Acceptance — corpus regression + marker survives autofit

**Files:** none changed (verification task; may adjust tolerances in `validate_svg.py` if a false positive surfaces).

**Interfaces:** exercises `validate_svg.py` main() and `autofit_svg.py` end-to-end.

- [ ] **Step 1: Full test suite green**

Run: `cd "C:/Users/User/.claude/skills/moodle-mbz-builder" && python -m pytest -v`
Expected: all tests PASS (new + existing).

- [ ] **Step 2: Corpus scan — 0 new warnings from the new checks**

Run (skill assets — always present):

```bash
cd "C:/Users/User/.claude/skills/moodle-mbz-builder"
python scripts/validate_svg.py assets/ 2>&1 | grep -E "ACHSE|SKALA|FIGUR" || echo "CLEAN: no new warnings"
```

Then the user's course library (skip gracefully if the folder is absent):

```bash
python scripts/validate_svg.py "C:/Users/User/OneDrive - HSOS/Desktop/Moodle-Kurse" 2>&1 | grep -E "ACHSE|SKALA|FIGUR" || echo "CLEAN: no new warnings"
```

Expected: `CLEAN: no new warnings` for both (existing charts are unmarked → no ACHSE/SKALA; no good figure should trip FIGUR).
If a **FIGUR** line appears on a genuinely-good diagram: inspect it; if it's a legit open shape, tighten the gap band or the `0.15·diagonal` ratio in `_figure_closure_warnings` and re-run. Re-run Step 1 after any change.

- [ ] **Step 3: Marker survives autofit**

```bash
cd "C:/Users/User/.claude/skills/moodle-mbz-builder"
cp assets/bohrmaschine_aufbau.svg /tmp/marker_probe.svg 2>/dev/null || cp assets/bohrer_anatomie.svg /tmp/marker_probe.svg
# inject the marker on the root <svg>, run autofit, confirm it is still there
python - <<'PY'
import re, pathlib
p = pathlib.Path("/tmp/marker_probe.svg")
s = p.read_text(encoding="utf-8")
s = re.sub(r"<svg\b", '<svg data-diagram-type="chart"', s, count=1)
p.write_text(s, encoding="utf-8")
PY
python scripts/autofit_svg.py /tmp/marker_probe.svg
grep -c 'data-diagram-type="chart"' /tmp/marker_probe.svg
```

Expected: `grep -c` prints `1` — autofit preserved the marker.
If it prints `0`: autofit strips unknown root attributes — fix `autofit_svg.py` to preserve them, add a regression test, then re-run. (Record this as a finding if it occurs.)

- [ ] **Step 4: Final commit (only if tolerances were adjusted)**

```bash
cd "C:/Users/User/.claude/skills/moodle-mbz-builder"
git add -A
git commit -m "test(svg): corpus acceptance for chart/figure checks (0 new warns)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

(If nothing changed in Steps 2–3, skip this commit.)

---

## Deferred (follow-up, not in this plan)

- **V4b — Überstände/Durchstriche (overshoot):** a segment endpoint poking past
  a corner. Deferred because a naive detector false-positives on **tick marks**
  (a tick endpoint sits on the axis line's interior — exactly the "loose end
  near another segment" pattern) and other legitimate T-junctions. Needs a model
  that excludes ticks/axis touches before it can be gate-safe. Own small spec +
  plan later.
- **Optional retrofit:** add `data-diagram-type="chart"` to existing coordinate
  charts in `assets/` and `Moodle-Kurse/*/assets/` and fix any resulting
  ACHSE/SKALA findings. Separate pass; not part of acceptance.

## Self-Review notes

- Spec coverage: V1 → Task 3; V3 → Task 4; V4a → Task 2; marker → Task 3;
  svg_geometry support → Task 1; docs → Task 5; acceptance (0 new warns) +
  autofit-survival → Task 6. V4b explicitly deferred (spec allowed).
- No placeholders: every code step shows complete code; every run step shows the
  exact command + expected result.
- Type consistency: helper names (`_segments`, `_find_axes`,
  `_chart_axis_warnings`, `_figure_closure_warnings`), the `is_chart` local, and
  `extra["path_closed"]` are used identically across Tasks 1–4.
