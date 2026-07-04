#!/usr/bin/env python3
"""Auto-generate downloadable materials (PDF + PowerPoint) for the "Infoblatt"
pages of a moodle-mbz-builder course and wire them into the course.

A page opts in with `"material": true`. For each such page this tool:
  * renders a print PDF (title bar + the page's embedded diagram + key points),
  * renders an editable PPTX (same content, diagram rasterised),
  * inserts a `resource` (PDF) right after the page, so it is downloadable at
    that spot in the course,
  * collects all PDFs and all PPTX into the hidden "Material für Lehrkräfte"
    section as two `folder`s (a PDF set for printing, a PPTX set for editing).

Key points come from `"material_bullets": [...]` if given, else they are
extracted from the page content (list items, else paragraphs).

It writes a NEW course JSON (default `<course>.materialized.json`) that you then
feed to build_mbz.py. The video summary is intentionally never generated — that
stays a manual NotebookLM placeholder.

Requires: svglib, reportlab, pymupdf (fitz), python-pptx, pillow.
    python -m pip install svglib reportlab pymupdf python-pptx pillow

Usage:
    python make_materials.py course.json [-o course.materialized.json]
    python build_mbz.py course.materialized.json -o course.mbz --wwwroot ...
"""
import argparse, copy, html, json, os, re, sys

GREEN_HEX = "#1d6e56"


def _need():
    try:
        import svglib.svglib, reportlab, fitz, pptx, PIL  # noqa
    except Exception as e:
        sys.exit(f"Missing dependency: {e}\nInstall: python -m pip install "
                 f"svglib reportlab pymupdf python-pptx pillow")


def slugify(name):
    s = re.sub(r"^infoblatt[:\s-]*", "", name.strip(), flags=re.I)
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()
    return s or "material"


def first_image(page):
    for img in page.get("images", []):
        p = img if isinstance(img, str) else img.get("file")
        if p:
            return p
    return None


def extract_bullets(page):
    if page.get("material_bullets"):
        return page["material_bullets"]
    content = page.get("content", "") or ""
    items = re.findall(r"<li[^>]*>(.*?)</li>", content, flags=re.S | re.I)
    if not items:
        items = re.findall(r"<p[^>]*>(.*?)</p>", content, flags=re.S | re.I)
    out = []
    for it in items:
        txt = html.unescape(re.sub(r"<[^>]+>", "", it)).strip()
        txt = re.sub(r"\s+", " ", txt)
        if txt and len(txt) > 1:
            out.append(txt)
    return out[:6]


def title_of(page):
    return re.sub(r"^Infoblatt[:\s-]*", "", page.get("name", "Infoblatt")).strip()


def svg_to_pdf(svgpath, pdfpath):
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPDF
    renderPDF.drawToFile(svg2rlg(svgpath), pdfpath)


def svg_to_png(svgpath, pngpath):
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPDF
    import fitz
    tmp = pngpath + ".tmp.pdf"
    renderPDF.drawToFile(svg2rlg(svgpath), tmp)
    doc = fitz.open(tmp)
    doc[0].get_pixmap(matrix=fitz.Matrix(3, 3), alpha=False).save(pngpath)
    doc.close(); os.remove(tmp)


def make_pdf(title, svgpath, bullets, out):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from svglib.svglib import svg2rlg
    styles = getSampleStyleSheet()
    h = ParagraphStyle("h", parent=styles["Title"], fontSize=18, alignment=0,
                       textColor=colors.HexColor(GREEN_HEX), spaceAfter=4)
    sub = ParagraphStyle("sub", parent=styles["Normal"], fontSize=10,
                         textColor=colors.HexColor("#5f6368"), spaceAfter=10)
    body = ParagraphStyle("body", parent=styles["Normal"], fontSize=11, leading=16)
    doc = SimpleDocTemplate(out, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm,
                            leftMargin=20 * mm, rightMargin=20 * mm)
    story = [Paragraph(html.escape(title), h), Paragraph("Infoblatt", sub)]
    if svgpath and os.path.exists(svgpath):
        d = svg2rlg(svgpath)
        s = (165 * mm) / d.width
        d.width *= s; d.height *= s; d.scale(s, s)
        story += [d, Spacer(1, 8 * mm)]
    if bullets:
        story.append(ListFlowable([ListItem(Paragraph(html.escape(b), body), leftIndent=10)
                                   for b in bullets], bulletType="bullet"))
    doc.build(story)


def make_pptx(title, svgpath, bullets, out, workdir):
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
    from PIL import Image
    prs = Presentation()
    prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5)
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(0.9))
    bar.fill.solid(); bar.fill.fore_color.rgb = RGBColor(0x1d, 0x6e, 0x56); bar.line.fill.background()
    tf = bar.text_frame; tf.margin_left = Inches(0.3); tf.word_wrap = True
    r = tf.paragraphs[0].add_run(); r.text = "Infoblatt  ·  " + title
    r.font.size = Pt(24); r.font.bold = True; r.font.color.rgb = RGBColor(255, 255, 255)
    text_left = 0.5
    if svgpath and os.path.exists(svgpath):
        png = os.path.join(workdir, slugify(title) + ".png")
        svg_to_png(svgpath, png)
        iw, ih = Image.open(png).size; ar = iw / ih
        w = 7.4; hgt = w / ar
        if hgt > 5.4: hgt = 5.4; w = hgt * ar
        slide.shapes.add_picture(png, Inches(0.4), Inches(1.2), width=Inches(w), height=Inches(hgt))
        text_left = 8.1
    box = slide.shapes.add_textbox(Inches(text_left), Inches(1.3), Inches(13.333 - text_left - 0.4), Inches(5.3))
    tf2 = box.text_frame; tf2.word_wrap = True
    for i, b in enumerate(bullets or []):
        para = tf2.paragraphs[0] if i == 0 else tf2.add_paragraph()
        run = para.add_run(); run.text = "•  " + b
        run.font.size = Pt(16); run.font.color.rgb = RGBColor(0x1a, 0x1a, 0x1a)
        para.space_after = Pt(10)
    prs.save(out)


def ensure_teacher_section(spec):
    for s in spec["sections"]:
        if s.get("visible") == 0:
            return s
    sec = {"name": "Material für Lehrkräfte", "visible": 0,
           "summary": "<p>Nur für Lehrkräfte – Druck- und Editiermaterial.</p>",
           "activities": [{"type": "label", "name": "Hinweis",
                           "intro": "<p>🔒 Dieser Abschnitt ist für Lehrkräfte (verborgen).</p>"}]}
    spec["sections"].append(sec)
    return sec


def main():
    _need()
    ap = argparse.ArgumentParser(description="Auto-generate + wire PDF/PPTX materials for Infoblatt pages.")
    ap.add_argument("course_json")
    ap.add_argument("-o", "--output")
    ap.add_argument("--dir", default="materials", help="output subdir for generated files")
    args = ap.parse_args()

    base = os.path.dirname(os.path.abspath(args.course_json))
    matdir = os.path.join(base, args.dir)
    os.makedirs(matdir, exist_ok=True)
    spec = json.load(open(args.course_json, encoding="utf-8"))

    # Check embedded SVG diagrams BEFORE rasterising them into PDF/PPTX, so a
    # clipped/overlapping diagram is caught before it is baked into materials.
    try:
        import validate_svg
        validate_svg.check_course_svgs(spec, base)
    except Exception as e:  # noqa: BLE001
        print(f"NOTE: SVG diagram check skipped ({e}).", file=sys.stderr)

    pdfs, pptxs = [], []
    for sec in spec["sections"]:
        new_acts = []
        for act in sec["activities"]:
            new_acts.append(act)
            if act.get("type") == "page" and act.get("material"):
                title = title_of(act)
                slug = slugify(act.get("name", "infoblatt"))
                svg = first_image(act)
                bullets = extract_bullets(act)
                pdfp = os.path.join(matdir, slug + ".pdf")
                pptxp = os.path.join(matdir, slug + ".pptx")
                make_pdf(title, svg, bullets, pdfp)
                make_pptx(title, svg, bullets, pptxp, matdir)
                pdfs.append(pdfp); pptxs.append(pptxp)
                new_acts.append({"type": "resource", "name": f"{title} – Infoblatt (PDF)",
                                 "intro": "<p>Zum Ausdrucken.</p>", "file": pdfp})
        sec["activities"] = new_acts

    if pdfs:
        teacher = ensure_teacher_section(spec)
        teacher["activities"].append({"type": "folder",
            "name": "Alle Infoblätter als PDF (Druckvorlagen)",
            "intro": "<p>Sammlung aller Infoblätter zum Ausdrucken.</p>", "files": pdfs})
        teacher["activities"].append({"type": "folder",
            "name": "Alle Infoblätter als PowerPoint (bearbeitbar)",
            "intro": "<p>Editierbare PPTX-Versionen zum Anpassen.</p>", "files": pptxs})

    out = args.output or (os.path.splitext(args.course_json)[0] + ".materialized.json")
    json.dump(spec, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"Materialien erzeugt: {len(pdfs)} PDF + {len(pptxs)} PPTX in {matdir}")
    print(f"Materialisierte Kursdefinition: {out}")


if __name__ == "__main__":
    main()
