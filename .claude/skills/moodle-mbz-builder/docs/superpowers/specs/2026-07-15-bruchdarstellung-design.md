# Spec — Bruchdarstellung (V2)

**Datum:** 2026-07-15
**Skill:** `moodle-mbz-builder`
**Strang:** 3 von ~6 (siehe [MbZ-Builder-Überarbeitung])
**Status:** Design mit Autor abgestimmt (2026-07-15, Autor delegiert Umsetzung + Bericht danach)

## Kontext & Motivation

In Rechnungen sollen **echte Brüche** stehen (Zähler über Nenner mit
waagerechtem Strich), nicht `U/I`. Der Autor hat aus eigener Erfahrung bestätigt:
der **verlässliche** Weg für echte Mathe-Darstellung in Moodle läuft über den
**MathJax-Filter** (Moodle 4.x, standardmäßig aktiv), nicht über rohes CSS (das
Moodles HTMLPurifier beim Anzeigen strippen kann). Moodle-Editoren (Atto/TinyMCE)
rendern eigenes HTML; unsere Inhalte kommen jedoch per `.mbz`-Restore am Editor
vorbei — der MathJax-Filter rendert beim Anzeigen trotzdem.

## Ziele / Nicht-Ziele

**Ziele**
- Rechnungs-Brüche als **echte** Brüche in Moodle-Seite, Vorschau und Editor;
  im PDF-Material sauberer Rückfall auf `Zähler/Nenner`.
- Einheiten bleiben **normaler Text/Slash** (Grauzone: kurze wie m/s gehen als
  Bruch, lange wie die Einheit der Gravitationskonstante m³·kg⁻¹·s⁻² niemals) —
  Einheiten werden **nicht** in `\frac` gezwungen.

**Nicht-Ziele**
- Kein vollständiger LaTeX-/Gleichungs-Renderer. Unterstützt werden **isolierte
  `\(\frac{a}{b}\)`-Brüche** (einfacher Zähler/Nenner, keine verschachtelten
  Klammern); die umgebende Gleichung ist normaler Text
  (`R = \(\frac{U}{I}\) = 6 Ω`).
- Kein Bündeln von MathJax in die Vorschau (offline/CSP) — die Vorschau rendert
  Brüche per leichtem CSS-Stapel selbst.

## 1 · Quell-Syntax

Rechnungs-Brüche werden als **MathJax-Inline-Mathematik** geschrieben:

```
\(\frac{Zähler}{Nenner}\)      z. B.  \(\frac{U}{I}\) ,  \(\frac{3}{4}\)
```

- `\frac` und `\dfrac` werden erkannt.
- `\(` … `\)` sind Moodles Default-Inline-Delimiter → der MathJax-Filter rendert
  einen echten Bruch. Die Delimiter sind reiner Text und überstehen HTMLPurifier
  (der Filter läuft danach).

## 2 · Surfaces & Transformationen

| Surface | Verhalten | Umsetzung |
|---|---|---|
| **Moodle-Seite/Buch** | MathJax-Filter rendert `\(\frac…\)` nativ | build_mbz lässt den Text unangetastet (kein Code) |
| **Vorschau** (`preview_mbz`) | echter Stapel-Bruch per CSS | `to_css()` auf dem fertigen HTML |
| **Editor-Widget** (`build_editor_widget`) | zeigt die **LaTeX-Quelle** `\(\frac…\)` | **bewusst KEINE** Transformation — der Editor schreibt den Stand nach `course.json` zurück; ein gerenderter Span würde die Quelle beim Speichern zerstören (wie ein Quelltext-Editor) |
| **PDF-Material** (`make_materials`) | Rückfall `Zähler/Nenner` | `to_slash()` vor dem HTML-Parsen |
| **Einheiten** | normaler Text/Slash | nie in `\frac` gewickelt |

## 3 · Shared Helper `scripts/fraction_render.py`

```python
to_slash(text: str) -> str
    # jedes \(\frac{a}{b}\) / \(\dfrac{a}{b}\) -> "a/b" (ReportLab-sicher)
to_css(text: str) -> str
    # jedes \(\frac{a}{b}\) -> inline-gestapelter <span>-Bruch (Zähler über
    # Nenner, border-bottom als Strich) — für Browser-Vorschau/Editor
```

- Ein gemeinsames Regex `\\\(\s*\\d?frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}\s*\\\)`
  (Zähler = Gruppe 1, Nenner = Gruppe 2).
- Beide Funktionen sind rein (Text→Text), damit direkt unit-testbar.

Der CSS-Stapel (für Vorschau/Editor, kein HTMLPurifier im Weg):
```html
<span style="display:inline-block;vertical-align:middle;text-align:center;margin:0 .15em">
  <span style="display:block;border-bottom:1px solid;padding:0 .3em">a</span>
  <span style="display:block;padding:0 .3em">b</span></span>
```

## 4 · Autorenregeln (`references/course-design.md`)

Ergänzung im Abschnitt „Rechenbeispiele & Aufgaben":
- Brüche in Rechnungen als `\(\frac{Zähler}{Nenner}\)` schreiben (Moodle rendert
  echten Bruch); `\(\frac{3}{4}\)` erscheint als echtes ¾.
- Einheiten **nicht** als `\frac`: m/s, km/h als Text/Slash; lange/zusammengesetzte
  Einheiten (Gravitationskonstante …) ausschließlich als Text.
- Voraussetzung Zielsystem: **MathJax-Filter aktiv** (Moodle-4.x-Standard). Falls
  im Ziel deaktiviert, zeigt Moodle den LaTeX-Quelltext — dann Filter aktivieren.

## 5 · Verifikation (Lab-Spike)

Mit dem Skill `moodle-testinstanz`/Moodle-Lab eine Probe-Seite mit `\(\frac{3}{4}\)`
bauen und restaurieren:
- Restore erfolgreich (Inhalt inkl. `\(\frac…\)` erhalten).
- Sichtprüfung (soweit machbar): Moodle rendert den Bruch (MathJax-Filter aktiv).
- `to_css`-Vorschau zeigt den Bruch gestapelt; `to_slash`-PDF zeigt `3/4`.

## 6 · Tests

Neue `tests/test_fraction_render.py`:

| Eingabe | `to_slash` | `to_css` |
|---|---|---|
| `R = \(\frac{U}{I}\) = 6 Ω` | `R = U/I = 6 Ω` | enthält `border-bottom`, `U`, `I`, kein `\frac` |
| `\(\dfrac{3}{4}\)` | `3/4` | gestapelt, kein `\frac` |
| `keine Formel, 1/min` (Einheit) | unverändert | unverändert |
| zwei Brüche in einem Satz | beide ersetzt | beide gestapelt |

Plus Integration: `preview_mbz`/`make_materials` auf einer Mini-`course.json` mit
einem `\frac` erzeugen erwartete Ausgabe (Stapel bzw. Slash).

## Umsetzungsschritte (Grobskizze für den Plan)

1. `scripts/fraction_render.py`: `to_slash`, `to_css` + Unit-Tests.
2. `make_materials.py`: `to_slash` vor `_parse_html` einhängen.
3. `preview_mbz.py`: `to_css` auf dem fertigen Vorschau-HTML.
4. `course-design.md`: Autorenregel Brüche/Einheiten.
5. Lab-Spike (Restore einer `\frac`-Probe) + Sichtprüfung.
   (Editor-Widget bewusst unverändert — zeigt LaTeX-Quelle.)

## Geparkt / Folge

- Übrige Stränge: O3 Simulationen, O4 Didaktik-Profile, O1 Recap, O2 Speed.
