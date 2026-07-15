# Pipeline-Speed (Strand O2) — Design & Measurements

**Goal:** make course generation faster/leaner without changing the generated
output. Correctness first. Implement only SAFE, high-confidence speedups whose
output-equivalence can be proven; leave risky ideas as documented proposals.

## Method

- **Benchmark course:** the bundled gold-standard `assets/fewshot_bohrmaschine.json`
  (8 sections, 26 activities, 8 `material` Infoblatt pages, 7 hand-authored SVG
  diagrams). Copied to the repo root as `_o2_profile.json` so its relative
  `assets/*.svg` paths resolve.
- **Stage wall time:** each pipeline stage run as a subprocess (real-world,
  includes interpreter + library import), best of 3 (`_o2_profile.py`).
- **Hot spots:** `cProfile` of the in-process functions of `make_materials` and
  `build_mbz`.
- **Output-equivalence oracle (`_o2_equiv.py`):** the pipeline is inherently
  non-deterministic (reportlab PDF `/CreationDate`, python-pptx core dates, and
  `build_mbz`'s `self.now` timestamps). Pinning the clock (`time.time` frozen +
  `SOURCE_DATE_EPOCH` + `reportlab rl_config.invariant`) makes the whole build
  **byte-deterministic**: two clean runs produce an identical 281-member
  manifest (`member → sha256` over the extracted `.mbz`, excluding the
  size/mtime-bearing `.ARCHIVE_INDEX` and the empty `moodle_backup.log`). Any
  manifest diff after a code change therefore means the change altered generated
  output. This is the CONTENT comparison the strand requires (page XMLs + full
  file set), robust to the gzip/timestamp noise.

## Measured per-stage timings (best of 3, subprocess, this machine)

| Stage           | Before    | After     | Notes |
|-----------------|-----------|-----------|-------|
| autofit_svg     |  744 ms   |  ~790 ms  | ~90% interpreter + svglib/reportlab import; work ≈ 8 ms |
| validate_svg    |  755 ms   |  ~666 ms  | same; lint work ≈ 25 ms for 7 SVGs |
| **make_materials** | **9204 ms** | **2921 ms** | **the hot spot — SVG→PDF/PPTX rasterisation** |
| build_mbz       | 1000 ms   |  ~810 ms  | import + SVG re-lint + XML assembly + gzip |
| validate_mbz    |  455 ms   |  ~414 ms  | |
| preview_mbz     |  389 ms   |  ~334 ms  | inlines SVG as markup (no rasteriser) |
| **TOTAL**       | **12547 ms** | **5937 ms** | **−53%** |

## Top bottleneck (root cause)

`make_materials` was 73% of the pipeline. Its cProfile put ~5.5 s of ~9.9 s in
**reportlab TrueType font extraction** (`TTFontFile.extractInfo`), called 116×.

Root cause in svglib (`fonts.py`): `FontMap.find_font(name, weight, style)`
looks up the *weighted* internal name (`"Arial-Bold"`), misses the family cache,
then falls through to `register_font(name, guessed_file)` **without passing the
weight/style** — so the result is stored under the base name `"Arial"` and the
weighted lookup never caches. Every `svg2rlg` render therefore re-parses the
same Arial `.ttf` from disk. With 7 diagrams each rendered **twice** (vector into
the PDF via `make_pdf`, rasterised for the PPTX via `make_pptx`→`svg_to_png`),
that is 14 renders × ~2 extractions = the 116 re-parses.

## Speedups — ranked by impact / risk

### IMPLEMENTED (safe, output verified byte-identical)

1. **Per-process font-registration memo** (`make_materials._enable_font_cache`).
   Wraps `svglib.fonts.FontMap.register_font` so a repeat call with identical
   arguments returns the first result without re-registering. reportlab keeps the
   TTFont from the first registration — fonts are designed to be registered once
   and reused across documents — so each font file is parsed **once per process**
   instead of once per render. Activated lazily at the top of `make_pdf`,
   `svg_to_png`, `svg_to_pdf` (idempotent, degrades gracefully if svglib absent).
   - **Impact:** `make_materials` 9204 → 2921 ms; pipeline total −53%.
   - **Risk:** none measured. `register_font`'s only side effects (updating
     `_map`/`_family_index`, registering the TTFont) are idempotent and already
     applied on the first call; the memo skips only the redundant re-parse. The
     memo key includes `font_path`, so distinct (regular vs. bold) files still
     each register on first occurrence in the original order.
   - **Verification:** frozen-clock manifest identical before/after
     (`_o2_manifest_base1.txt` == `_o2_manifest_fontcache.txt`, 281 members);
     full pytest green; focused test `tests/test_font_cache.py` asserts zero
     re-extraction on the second render and that the real registration is
     preserved.

### PROPOSALS (left as documented ideas — not implemented)

2. **Cache `svg2rlg` parse per SVG within `make_materials`** (each diagram is
   parsed twice — PDF vector + PPTX raster). *Why not now:* `make_pdf`'s inner
   `image()` **mutates** the Drawing (`d.width *= s; d.scale(s, s)`), so a shared
   cached object would corrupt the PPTX rasterisation unless deep-copied;
   reportlab Drawing copy semantics are fiddly and a mis-copy could silently
   change rendering. Remaining win after the font cache is only ~0.3 s (14
   `svg2rlg` calls now total ~0.6 s). Impact/risk ratio no longer justifies it.

3. **Cross-process SVG-lint cache** — the diagram lint runs 3× per pipeline
   (`validate_svg` standalone, `make_materials`, `build_mbz`), re-parsing the
   same SVGs each time. *Why not now:* measured lint-only cost is ~25 ms/pass for
   7 SVGs; the three passes live in separate processes, so a cache would need an
   on-disk, content-hash-keyed store — added complexity and a (small) correctness
   surface for ~50 ms of avoidable work. Not worth it at this course size; could
   matter for very large courses (many diagrams).

4. **Lower gzip level / merge stages** — `build_mbz`'s zlib compression is ~80 ms
   and is inherent; lowering the level changes the delivered archive encoding
   (content identical, bytes not). Merging `autofit`/`validate`/`build` into one
   process would remove repeated ~600 ms import startup, but the stage boundaries
   are fixed by `SKILL.md` (off-limits) and are separate CLI tools by design.
   Not pursued.

## Residual profile after the fix

`make_materials` is now dominated by **inherent rasterisation** that cannot be
reduced without changing output: `make_pptx`/`svg_to_png` (fitz PNG render at 3×)
and `make_pdf` (reportlab platypus build). `autofit_svg`/`validate_svg` are ~90%
interpreter + library import. The one structural inefficiency (font re-parsing)
is removed.
