"""make_combined_pdf(): fasst die Infoblatt-PDFs zu EINEM diagramm-reichen
Kurs-Materialdossier zusammen — als echte Bild-Quelle für NotebookLM
(nicht nur Text). Strang #9."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from make_materials import make_combined_pdf  # noqa: E402


def _mini_pdf(path, pages=1):
    import fitz
    d = fitz.open()
    for _ in range(pages):
        d.new_page()
    d.save(path)
    d.close()


def test_make_combined_pdf_concatenates_pages(tmp_path):
    a = str(tmp_path / "a.pdf"); _mini_pdf(a, 2)
    b = str(tmp_path / "b.pdf"); _mini_pdf(b, 1)
    out = str(tmp_path / "Kurs-Materialdossier.pdf")
    make_combined_pdf([a, b], out)
    import fitz
    assert os.path.exists(out)
    with fitz.open(out) as c:
        assert c.page_count == 3          # 2 + 1 Seiten zusammengeführt


def test_make_combined_pdf_empty_list_no_file(tmp_path):
    out = str(tmp_path / "leer.pdf")
    make_combined_pdf([], out)
    assert not os.path.exists(out)        # keine Quellen -> kein Dossier
