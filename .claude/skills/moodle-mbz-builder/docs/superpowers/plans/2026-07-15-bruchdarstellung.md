# Bruchdarstellung (V2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Real fractions in calculations — `\(\frac{a}{b}\)` rendered natively by Moodle's MathJax filter, a stacked CSS fraction in the HTML preview, and an `a/b` fallback in the PDF material. Units stay plain slash.

**Architecture:** One shared, pure text helper `scripts/fraction_render.py` (`to_slash`, `to_css`), wired into `make_materials.py` (PDF → slash) and `preview_mbz.py` (preview → CSS). Moodle needs no code change (MathJax filter). The editor widget is intentionally untouched (shows LaTeX source to protect its edit round-trip).

**Tech Stack:** Python 3.11 `re`, `pytest`, plus the local Moodle-Lab (`moodle-testinstanz`) for the restore spike.

## Global Constraints

- Scope: isolated `\(\frac{a}{b}\)` / `\(\dfrac{a}{b}\)` tokens, non-nested num/den. Surrounding equation stays plain text.
- Units are NEVER wrapped in `\frac` (m/s, km/h, gravitational-constant units stay text/slash).
- Target Moodle must have the MathJax filter enabled (4.x default) — documented, not enforced.
- Branch `feature/bruchdarstellung`. Skill root: `C:/Users/User/.claude/skills/moodle-mbz-builder`.

---

### Task 1: `fraction_render.py` helper + tests

**Files:**
- Create: `scripts/fraction_render.py`
- Test: `tests/test_fraction_render.py`

**Interfaces:**
- `to_slash(text: str) -> str` — each `\(\frac{a}{b}\)` → `a/b`.
- `to_css(text: str) -> str` — each `\(\frac{a}{b}\)` → inline-stacked `<span>` fraction.

- [ ] **Step 1: Write failing tests**

Create `tests/test_fraction_render.py`:

```python
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from fraction_render import to_slash, to_css


def test_slash_basic():
    assert to_slash(r"R = \(\frac{U}{I}\) = 6 Ω") == "R = U/I = 6 Ω"


def test_slash_dfrac():
    assert to_slash(r"\(\dfrac{3}{4}\)") == "3/4"


def test_slash_leaves_units():
    assert to_slash("Tempo 90 km/h und 1/min") == "Tempo 90 km/h und 1/min"


def test_slash_two_fractions():
    assert to_slash(r"\(\frac{a}{b}\) und \(\frac{c}{d}\)") == "a/b und c/d"


def test_css_stacks_with_bar():
    out = to_css(r"\(\frac{U}{I}\)")
    assert "border-bottom" in out and ">U</span>" in out and ">I</span>" in out
    assert "frac" not in out


def test_css_leaves_units():
    assert to_css("90 km/h") == "90 km/h"
```

- [ ] **Step 2: Run — expect ImportError/fail**

Run: `cd "C:/Users/User/.claude/skills/moodle-mbz-builder" && python -m pytest tests/test_fraction_render.py -v`
Expected: collection error (module missing).

- [ ] **Step 3: Implement**

Create `scripts/fraction_render.py`:

```python
#!/usr/bin/env python3
"""Render MathJax inline fractions \\(\\frac{a}{b}\\) for the non-Moodle surfaces.

Moodle renders \\(\\frac{...}{...}\\) natively via its MathJax filter. The HTML
preview and the PDF material can't run MathJax, so:
  * to_css   -> a real stacked fraction as an inline-styled <span> (browser)
  * to_slash -> "a/b" (ReportLab-safe, for the PDF material)

Scope: isolated \\(\\frac{a}{b}\\) / \\(\\dfrac{a}{b}\\) tokens with simple,
non-nested numerator/denominator. The surrounding equation stays plain text.
"""
import re

# \( ...\frac{NUM}{DEN}... \) with NUM/DEN free of nested braces
_FRAC_RX = re.compile(r"\\\(\s*\\d?frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}\s*\\\)")

_CSS_TMPL = (
    '<span style="display:inline-block;vertical-align:middle;text-align:center;'
    'margin:0 .15em">'
    '<span style="display:block;border-bottom:1px solid;padding:0 .3em">{num}</span>'
    '<span style="display:block;padding:0 .3em">{den}</span></span>')


def to_slash(text):
    """Each \\(\\frac{a}{b}\\) -> 'a/b' (ReportLab-safe)."""
    if not text:
        return text
    return _FRAC_RX.sub(
        lambda m: f"{m.group(1).strip()}/{m.group(2).strip()}", text)


def to_css(text):
    """Each \\(\\frac{a}{b}\\) -> an inline-stacked <span> fraction."""
    if not text:
        return text
    return _FRAC_RX.sub(
        lambda m: _CSS_TMPL.format(num=m.group(1).strip(), den=m.group(2).strip()),
        text)
```

- [ ] **Step 4: Run — expect pass**

Run: `cd "C:/Users/User/.claude/skills/moodle-mbz-builder" && python -m pytest tests/test_fraction_render.py -v`
Expected: 6 PASS.

- [ ] **Step 5: Commit**

```bash
cd "C:/Users/User/.claude/skills/moodle-mbz-builder"
git add scripts/fraction_render.py tests/test_fraction_render.py
git commit -m "feat(fractions): to_slash/to_css helper for MathJax \\frac rendering

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: PDF fallback in make_materials

**Files:** Modify `scripts/make_materials.py`.

**Interfaces:** Consumes `to_slash` (Task 1).

- [ ] **Step 1: Import the helper**

In `scripts/make_materials.py`, near the top-level imports (after `from html.parser import HTMLParser as _HTMLParser`), add:

```python
from fraction_render import to_slash
```

- [ ] **Step 2: Apply to_slash to the page content before parsing**

In `make_pdf(...)`, the content is parsed via `render(_parse_html(page.get("content", "")))`. Change that line to:

```python
    render(_parse_html(to_slash(page.get("content", ""))))
```

- [ ] **Step 3: Verify — build a mini course PDF and check the slash**

```bash
cd "C:/Users/User/.claude/skills/moodle-mbz-builder"
python - <<'PY'
import sys, os, json, tempfile
sys.path.insert(0, "scripts")
import make_materials as M
page = {"type": "page", "name": "Probe", "material": True,
        "content": r"<p>Widerstand: R = \(\frac{U}{I}\) = 6 Ω</p>"}
d = tempfile.mkdtemp()
out = os.path.join(d, "probe.pdf")
M.make_pdf(page, ".", out)
import fitz
txt = fitz.open(out)[0].get_text()
print("PDF-Text enthält 'U/I':", "U/I" in txt)
print("PDF-Text enthält '\\frac':", "frac" in txt)
PY
```

Expected: `PDF-Text enthält 'U/I': True` and `... '\frac': False`.

- [ ] **Step 4: Commit**

```bash
cd "C:/Users/User/.claude/skills/moodle-mbz-builder"
git add scripts/make_materials.py
git commit -m "feat(fractions): PDF material renders \\frac as a/b fallback

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: CSS fraction in the HTML preview

**Files:** Modify `scripts/preview_mbz.py`.

**Interfaces:** Consumes `to_css` (Task 1).

- [ ] **Step 1: Import the helper**

In `scripts/preview_mbz.py`, add near the other imports:

```python
from fraction_render import to_css
```

- [ ] **Step 2: Apply to_css to the final preview HTML**

In `build_html(spec)`, the function ends with
`return TEMPLATE.format(title=title, meta=html.escape(meta), sections="".join(secs))`.
Change it to:

```python
    return to_css(TEMPLATE.format(title=title, meta=html.escape(meta),
                                  sections="".join(secs)))
```

- [ ] **Step 3: Verify — build a preview and check the stacked span**

```bash
cd "C:/Users/User/.claude/skills/moodle-mbz-builder"
python - <<'PY'
import sys
sys.path.insert(0, "scripts")
import preview_mbz as P
spec = {"course": {"fullname": "Probe"}, "sections": [
    {"name": "S1", "activities": [
        {"type": "page", "name": "P", "content": r"<p>R = \(\frac{U}{I}\)</p>"}]}]}
html = P.build_html(spec)
print("Vorschau enthält border-bottom (Bruchstrich):", "border-bottom" in html)
print("Vorschau enthält rohes \\frac:", "frac" in html)
PY
```

Expected: `... border-bottom ...: True` and `... rohes \frac: False`.

- [ ] **Step 4: Commit**

```bash
cd "C:/Users/User/.claude/skills/moodle-mbz-builder"
git add scripts/preview_mbz.py
git commit -m "feat(fractions): HTML preview renders \\frac as a stacked CSS fraction

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Authoring rule

**Files:** Modify `references/course-design.md`.

- [ ] **Step 1: Extend the "Rechenbeispiele & Aufgaben" section**

In `references/course-design.md`, in the "Rechenbeispiele & Aufgaben" section, append after the V6 bullet:

```markdown
- **Brüche in Rechnungen — echt setzen:** Brüche als MathJax schreiben:
  `\(\frac{Zähler}{Nenner}\)` — Moodle rendert daraus einen echten Bruch
  (`\(\frac{3}{4}\)` erscheint als echtes ¾), die Vorschau zeigt ihn gestapelt,
  das PDF fällt auf `Zähler/Nenner` zurück. Nur der Bruch selbst ist MathJax; die
  umgebende Gleichung (`R = \(\frac{U}{I}\) = 6 Ω`) ist normaler Text.
- **Einheiten NICHT als Bruch:** m/s, km/h und besonders lange/zusammengesetzte
  Einheiten (z. B. die der Gravitationskonstante) bleiben normaler Text/Slash —
  nie in `\frac` zwingen.
- **Voraussetzung Zielsystem:** der MathJax-Filter muss im Ziel-Moodle aktiv sein
  (4.x-Standard); sonst zeigt Moodle den LaTeX-Quelltext.
```

- [ ] **Step 2: Commit**

```bash
cd "C:/Users/User/.claude/skills/moodle-mbz-builder"
git add references/course-design.md
git commit -m "docs(fractions): authoring rule — \\frac for calculations, units stay text

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Acceptance — full suite + Moodle-Lab restore spike

**Files:** none changed (verification).

- [ ] **Step 1: Full suite**

Run: `cd "C:/Users/User/.claude/skills/moodle-mbz-builder" && python -m pytest tests/ -q`
Expected: all PASS.

- [ ] **Step 2: Build a probe .mbz with a fraction**

```bash
cd "C:/Users/User/.claude/skills/moodle-mbz-builder"
D=$(python -c "import tempfile;print(tempfile.mkdtemp())")
cat > "$D/course.json" <<'JSON'
{"course":{"fullname":"Bruch-Probe","shortname":"BRUCHPROBE","format":"topics"},
 "sections":[{"name":"1 Rechnung","activities":[
   {"type":"page","name":"Bruch","content":"<h3>Ohm</h3><p>R = \\(\\frac{U}{I}\\) = \\(\\frac{12\\,V}{2\\,A}\\) = 6 Ω</p>"}]}]}
JSON
python scripts/build_mbz.py "$D/course.json" -o "$D/bruchprobe.mbz" --wwwroot https://moodle.example.edu
python scripts/validate_mbz.py "$D/bruchprobe.mbz"; echo "validate exit=$?"
echo "MBZ: $D/bruchprobe.mbz"
```

Expected: build ok; `validate exit=0`. Confirm the page.xml keeps the `\(\frac…\)` source (Moodle will MathJax-render it):

```bash
python - "$D/bruchprobe.mbz" <<'PY'
import sys, tarfile, re
tar = tarfile.open(sys.argv[1], "r:gz")
for n in tar.getnames():
    if re.match(r"activities/page_\d+/page\.xml$", n):
        data = tar.extractfile(n).read().decode("utf-8")
        print("page.xml enthält \\frac:", "frac" in data)
PY
```

Expected: `page.xml enthält \frac: True` (source preserved for Moodle's filter).

- [ ] **Step 3: Live restore into the Moodle-Lab (if available)**

```bash
cd "C:/Users/User/.claude/skills/moodle-mbz-builder"
python scripts/check_delivery.py "$D" --allow-video-placeholder --allow-no-widget || true
```

Or, if the `moodle-testinstanz` runner is present, restore directly:

```bash
RUN=~/.claude/skills/moodle-testinstanz/scripts/run_restore.py
[ -f "$RUN" ] && python "$RUN" "$D/bruchprobe.mbz" --json || echo "Lab/Skill nicht vorhanden — Restore-Spike übersprungen"
```

Expected: restore returns 0 (course imports). Note in the report whether a live
Moodle render of the fraction was visually confirmed or only restore-verified.

- [ ] **Step 4: Report**

Summarize: helper + 3 wirings, tests green, probe builds/restores, source `\frac`
preserved for Moodle's MathJax filter, preview shows stacked bar, PDF shows `a/b`.

---

## Self-Review notes

- Spec coverage: helper → Task 1; PDF slash → Task 2; preview CSS → Task 3;
  authoring rule → Task 4; lab spike → Task 5. Editor widget intentionally
  untouched (spec §2). Units stay slash (Task 4 rule; helper only touches `\frac`).
- No placeholders: every code step shows complete code; every run step shows the
  command + expected output.
- Type consistency: `to_slash`/`to_css`/`_FRAC_RX`/`_CSS_TMPL` identical across tasks.
