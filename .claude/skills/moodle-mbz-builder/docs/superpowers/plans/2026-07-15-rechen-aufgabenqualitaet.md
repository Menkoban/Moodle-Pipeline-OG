# Rechen- & Aufgabenqualität (V5/V6/V7) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce worked-example structure, real-situation tasks, and units-everywhere in generated courses via authoring rules, a `quality_check` extension, and a conservative non-fatal heuristic in the mbz validator.

**Architecture:** Add an advisory text helper `_calc_unit_warnings` + `_readable_text` to `scripts/validate_mbz.py` and call it from `_deep_checks` over page/book content (warnings only, never fatal). Add authoring guidance to `references/course-design.md` and three checks to the `quality_check` action in `SKILL.md`.

**Tech Stack:** Python 3.11, `re`, `html` (stdlib), `xml.etree.ElementTree`, `pytest`.

## Global Constraints

- The heuristic is **advisory**: results go into `validate_mbz`'s `warns` list, **never** `problems`. `validate_mbz` exit code must stay 0 on warnings.
- Heuristic scope: **page + book** content only (formular fields are empty by design → no results to check).
- Division stays a slash (`U/I`) in this strand — true fraction bar is **Strand 3** (V2).
- Message keyword, existing style: `EINHEIT`.
- Tests follow the repo pattern: `sys.path.insert(0, .../scripts)`, then `from validate_mbz import _calc_unit_warnings, _readable_text`.
- Skill repo root: `C:/Users/User/.claude/skills/moodle-mbz-builder`. Branch `feature/rechen-aufgabenqualitaet`.

---

### Task 1: Heuristic helper `_calc_unit_warnings` + `_readable_text`

**Files:**
- Modify: `scripts/validate_mbz.py` (add `import html`; add unit regexes, `_readable_text`, `_calc_unit_warnings`)
- Test: `tests/test_validate_calc_units.py` (create)

**Interfaces:**
- Produces:
  - `_readable_text(raw: str) -> str` — unescape XML entities, strip HTML tags, collapse whitespace.
  - `_calc_unit_warnings(text: str) -> list[str]` — advisory snippets of results `= <number>` lacking a unit, only in a calc context (text has `=` and a unit token), skipping dimensionless quantities. Empty list = clean.

- [ ] **Step 1: Write the failing test**

Create `tests/test_validate_calc_units.py`:

```python
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from validate_mbz import _calc_unit_warnings, _readable_text


def test_result_with_unit_is_clean():
    assert _calc_unit_warnings("R = 3 V / 0,02 A = 150 Ω") == []


def test_result_without_unit_in_calc_context_is_flagged():
    hits = _calc_unit_warnings("U = 5 V; R = 150")
    assert any("150" in s for s in hits), hits


def test_non_calc_context_not_flagged():
    # no unit token anywhere -> not a calculation, don't flag a bare count
    assert _calc_unit_warnings("Anzahl der Bauteile = 150") == []


def test_plain_prose_not_flagged():
    assert _calc_unit_warnings("Der Motor dreht sich schnell und gleichmaessig.") == []


def test_dimensionless_efficiency_not_flagged():
    # efficiency η is unitless; must not be flagged even next to a unit'd result
    assert _calc_unit_warnings("P = 100 W; η = 0,85") == []


def test_readable_text_unescapes_and_strips():
    raw = "&lt;p&gt;&lt;b&gt;Ergebnis:&lt;/b&gt; U = 5 V; R = 150&lt;/p&gt;"
    txt = _readable_text(raw)
    assert "R = 150" in txt and "<" not in txt
    assert any("150" in s for s in _calc_unit_warnings(txt))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "C:/Users/User/.claude/skills/moodle-mbz-builder" && python -m pytest tests/test_validate_calc_units.py -v`
Expected: ImportError / collection error — `_calc_unit_warnings` and `_readable_text` don't exist yet.

- [ ] **Step 3: Implement the helpers**

In `scripts/validate_mbz.py`, extend the import block:

```python
from __future__ import annotations

import html
import re
import sys
import tarfile
import xml.etree.ElementTree as ET
```

Add this block right after the imports (before `def main`):

```python
# --- Rechnungs-Heuristik: Ergebnis ohne Einheit (beratend, nie fatal) ------- #
# Einheiten-Token (längste Alternativen zuerst, damit "kV" vor "V" greift).
_UNIT = (r"(?:kV|mV|µV|V|mA|µA|kA|A|kΩ|MΩ|Ω|kW|MW|VA|var|W|kN|Nm|N|hPa|kPa|MPa|Pa|"
         r"mbar|bar|mm|cm|dm|km|µm|nm|m|ms|µs|ns|min|h|s|°C|K|°|kg|mg|µg|g|t|"
         r"kHz|MHz|GHz|Hz|mF|µF|nF|pF|F|mH|µH|H|kWh|Wh|kJ|MJ|J|ml|l|%)")
_UNIT_TOKEN_RX = re.compile(r"(?<![A-Za-zµ°])" + _UNIT + r"(?![A-Za-zµ])")
_RESULT_RX = re.compile(r"=\s*[-+]?\d+(?:[.,]\d+)?")
_RESULT_UNIT_RX = re.compile(r"=\s*[-+]?\d+(?:[.,]\d+)?\s*" + _UNIT + r"(?![A-Za-zµ])")
# dimensionslose Größen (kein Fehlalarm): Wirkungsgrad, Reibzahl, Übersetzung …
_DIMLESS = {"η", "μ", "µ", "ε", "φ", "λ", "i", "z", "cos", "sin", "tan", "cosφ"}


def _readable_text(raw: str) -> str:
    """XML-escapetes HTML -> lesbarer Klartext: entschärfen, Tags strippen,
    Leerraum zusammenfassen."""
    txt = html.unescape(raw)              # &lt;p&gt; -> <p>, &amp; -> &
    txt = re.sub(r"<[^>]+>", " ", txt)    # HTML-Tags entfernen
    return re.sub(r"\s+", " ", txt).strip()


def _calc_unit_warnings(text: str) -> list[str]:
    """Beratend: in einem Rechenkontext (Text mit '=' UND einem Einheiten-Token)
    ein Ergebnis '= <Zahl>' melden, dem KEINE Einheit folgt. Dimensionslose
    Größen (η, i, cos φ …) werden übersprungen. Nie fatal."""
    if "=" not in text or not _UNIT_TOKEN_RX.search(text):
        return []
    out, seen = [], set()
    for m in _RESULT_RX.finditer(text):
        if _RESULT_UNIT_RX.match(text, m.start()):
            continue  # Einheit folgt direkt -> ok
        lhs = text[max(0, m.start() - 12):m.start()].strip()
        sym = re.split(r"[\s(]+", lhs)[-1] if lhs else ""
        if sym in _DIMLESS:
            continue  # dimensionslose Größe
        snip = text[m.start():m.end()].strip()
        if snip not in seen:
            seen.add(snip)
            out.append(snip)
    return out[:5]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "C:/Users/User/.claude/skills/moodle-mbz-builder" && python -m pytest tests/test_validate_calc_units.py -v`
Expected: all 6 PASS.

- [ ] **Step 5: Commit**

```bash
cd "C:/Users/User/.claude/skills/moodle-mbz-builder"
git add scripts/validate_mbz.py tests/test_validate_calc_units.py
git commit -m "feat(validate): advisory heuristic for calculations missing units

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Wire the heuristic into `_deep_checks`

**Files:**
- Modify: `scripts/validate_mbz.py` (add section 13 in `_deep_checks`)

**Interfaces:**
- Consumes: `contents` dict (archive path -> XML text), `warns` list, `_readable_text`, `_calc_unit_warnings` (Task 1).
- Produces: `EINHEIT:` warnings appended to `warns` for page/book activities.

- [ ] **Step 1: Implement section 13**

In `scripts/validate_mbz.py`, `_deep_checks(...)`, append this block at the **end** of the function (after section 12, the `INDEX:` block):

```python
    # ---- 13. Rechnungen ohne Einheit (beratend) -------------------------- #
    for path, data in contents.items():
        if not re.match(r"activities/(page|book)_\d+/\w+\.xml$", path):
            continue
        for block in re.findall(r"<content>(.*?)</content>", data, re.S):
            snips = _calc_unit_warnings(_readable_text(block))
            if snips:
                warns.append(
                    f"EINHEIT: mögliche Rechnung(en) ohne Einheit in "
                    f"{path.split('/')[1]}: " + ", ".join(f"'{s}'" for s in snips)
                    + " (Einheit ergänzen?)")
```

- [ ] **Step 2: Integration check on an existing course**

Pick any built course from the library and confirm the validator still runs and exits 0 (warnings allowed):

```bash
cd "C:/Users/User/.claude/skills/moodle-mbz-builder"
MBZ=$(ls -1 "C:/Users/User/OneDrive - HSOS/Desktop/Moodle-Kurse"/*/*.mbz 2>/dev/null | head -1)
echo "probe: $MBZ"
python scripts/validate_mbz.py "$MBZ"; echo "exit=$?"
```

Expected: prints the usual `info:`/`warn:` lines (possibly incl. `EINHEIT:` advisories) and `exit=0` (or `exit=1` only if that course has a pre-existing structural problem unrelated to this change — verify the failure, if any, is not an `EINHEIT` line since those are warnings).

- [ ] **Step 3: Run the full suite**

Run: `cd "C:/Users/User/.claude/skills/moodle-mbz-builder" && python -m pytest tests/ -q`
Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
cd "C:/Users/User/.claude/skills/moodle-mbz-builder"
git add scripts/validate_mbz.py
git commit -m "feat(validate): flag page/book calculations missing units (advisory)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Authoring rules + quality_check checks

**Files:**
- Modify: `references/course-design.md` (new "Rechenbeispiele & Aufgaben" section)
- Modify: `SKILL.md` (quality_check action: add checks f/g/h)

**Interfaces:** none (docs/prompt).

- [ ] **Step 1: Add the authoring section to course-design.md**

Open `references/course-design.md`. After the "Typografie-Konventionen in SVG-Text" section (find the next `###` or `##` heading and insert before it), add:

```markdown
### Rechenbeispiele & Aufgaben (Pflicht — geg/ges, Einheiten, echte Situation)

**Rechenbeispiel-Bauplan (kopierbares Muster).** Jede vorgerechnete Aufgabe
folgt Schritt für Schritt diesem Muster — nur ReportLab-sicheres HTML
(`<b>`, `<sub>`, `<sup>`), damit es in Moodle-Seite, Vorschau UND PDF ankommt:

    <div class="rechenbeispiel">
      <h4>Rechenbeispiel: <Titel></h4>
      <p><b>Situation:</b> <realer betrieblicher Kontext + konkrete Frage></p>
      <p><b>Gegeben:</b> <Größe = Wert Einheit; …></p>
      <p><b>Gesucht:</b> <Größe in Einheit></p>
      <p><b>Formel:</b> <symbolische Formel></p>
      <p><b>Einsetzen:</b> <Werte mit Einheiten eingesetzt></p>
      <p><b>Ergebnis:</b> <Wert Einheit></p>
    </div>

- **V5 — nachvollziehbar:** immer geg/ges → Formel (symbolisch) → Einsetzen →
  Ergebnis; optional eine Plausibilitätszeile. Keine Rechnung „vom Himmel".
- **V7 — Einheiten in JEDER Zeile:** jede physikalische Größe trägt ihre Einheit
  (gegeben, eingesetzt, Ergebnis). Keine nackten Zahlen. Konventionen wie bei
  SVG-Text (echte ²/³, Malpunkt ·, `1/min`). Division vorerst als Slash `U/I`.
- **V6 — echte Aufgaben aus der Handlungssituation:** jede Aufgabe/Rechnung
  ist in den realen betrieblichen Kontext des Kurses eingebettet (Bedarf, Zweck:
  „In der Steuerung …, damit …") — NIE ein nacktes „Berechne R".

`validate_mbz.py` meldet beratend eine Ergebniszeile ohne Einheit (`EINHEIT:`).
```

- [ ] **Step 2: Extend quality_check in SKILL.md**

In `SKILL.md`, find the `quality_check` action bullet (it lists checks `(a)`–`(e)` ending with "Feedback-Vollständigkeit in Quizzes"). Extend that sentence's list by appending:

```
  (f) Rechenbeispiele folgen dem Bauplan (Gegeben/Gesucht → Formel → Einsetzen
  → Ergebnis), (g) jede Rechengröße/jedes Ergebnis trägt eine Einheit, (h)
  Aufgaben sind in die Handlungssituation eingebettet (kein nacktes „rechne aus").
```

(Insert `(f)`/`(g)`/`(h)` into the existing `quality_check` list so it reads as one continuous enumeration; keep the surrounding sentence structure.)

- [ ] **Step 3: Commit**

```bash
cd "C:/Users/User/.claude/skills/moodle-mbz-builder"
git add references/course-design.md SKILL.md
git commit -m "docs: worked-example blueprint + units/real-task rules + quality_check

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Acceptance — full suite + corpus sample

**Files:** none changed (verification; may tighten `_UNIT`/`_DIMLESS` if the sample shows obvious false positives).

- [ ] **Step 1: Full test suite green**

Run: `cd "C:/Users/User/.claude/skills/moodle-mbz-builder" && python -m pytest tests/ -q`
Expected: all PASS.

- [ ] **Step 2: Corpus sample — inspect EINHEIT advisories**

```bash
cd "C:/Users/User/.claude/skills/moodle-mbz-builder"
for f in "C:/Users/User/OneDrive - HSOS/Desktop/Moodle-Kurse"/*/*.mbz; do
  [ -e "$f" ] || continue
  echo "=== $(basename "$f") ==="
  python scripts/validate_mbz.py "$f" 2>&1 | grep "EINHEIT:" || echo "  (keine)"
done
```

Inspect the `EINHEIT:` lines. Each should point at a genuinely unit-less result in a
calculation. Because the check is **advisory** (never fatal), occasional edge
cases are tolerable — but if a well-made worked example is flagged wrongly
(e.g. a dimensionless quantity not in `_DIMLESS`, or a unit not in `_UNIT`),
that is a calibration miss.

- [ ] **Step 3: Calibrate if the sample shows obvious false positives**

If a legitimate result is flagged: add the missing unit to `_UNIT` or the
missing dimensionless symbol to `_DIMLESS` in `scripts/validate_mbz.py`, add a
regression test to `tests/test_validate_calc_units.py` covering that case, and
re-run Steps 1–2. If the advisories look right, no change needed.

- [ ] **Step 4: Commit (only if calibrated in Step 3)**

```bash
cd "C:/Users/User/.claude/skills/moodle-mbz-builder"
git add scripts/validate_mbz.py tests/test_validate_calc_units.py
git commit -m "test(validate): calibrate unit heuristic against course corpus

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

(If nothing was changed in Step 3, skip this commit.)

---

## Deferred (own strands)

- **V2 Bruchdarstellung → Strand 3.** Rendering-Entscheidung: echter waagerechter
  Bruch (nur Browser, PDF fällt zurück) vs. diagonaler Unicode-Bruch (U+2044,
  überall) vs. Slash beibehalten. `make_materials.py` (ReportLab) rendert weder
  MathJax noch CSS-Brüche — das ist der Kern der Entscheidung.
- O3 Simulationen, O4 Didaktik-Profile, O1 Recap, O2 Speed.

## Self-Review notes

- Spec coverage: V5 Bauplan → Task 3 (Muster) + `quality_check` (f); V6 echte
  Aufgaben → Task 3 (Regel) + `quality_check` (h); V7 Einheiten → Task 3 (Regel)
  + `quality_check` (g) + Heuristik (Tasks 1–2). Heuristik-Heimat validate_mbz
  (nicht-fatal) → Tasks 1–2. Akzeptanz/Korpus → Task 4.
- Abweichung von der Spec (bewusst): Heuristik scannt **page + book**, nicht
  formular (leere Felder → keine Ergebnisse); dimensionslose Größen ausgenommen.
- No placeholders: jeder Code-Schritt zeigt vollständigen Code; jeder Lauf-Schritt
  zeigt Befehl + erwartetes Ergebnis. Die `<…>`-Slots im HTML-Muster sind
  bewusste Ausfüll-Platzhalter der Vorlage, kein fehlender Plan-Inhalt.
- Type consistency: `_readable_text`, `_calc_unit_warnings`, `_UNIT`,
  `_UNIT_TOKEN_RX`, `_RESULT_RX`, `_RESULT_UNIT_RX`, `_DIMLESS` identisch über
  Tasks 1–2.