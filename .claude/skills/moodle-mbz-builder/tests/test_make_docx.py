"""make_docx(): editierbare Word-Version eines Infoblatts (Strang #8).
Spiegelt Titel, Prosa, Listen, Tabellen, Merke-Box und Diagramme."""
import os
import sys
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from make_materials import make_docx  # noqa: E402


def test_make_docx_produces_editable_word(tmp_path):
    page = {
        "type": "page", "name": "Infoblatt: Test", "material": True,
        "content": "<h3>Überschrift</h3><p>Ein erklärender Absatz.</p>"
                   "<ul><li>Punkt eins</li><li>Punkt zwei</li></ul>"
                   "<div style='background:#fff3cd'>💡 Merke: Wichtig.</div>",
    }
    out = str(tmp_path / "t.docx")
    make_docx(page, str(tmp_path), out, str(tmp_path))
    assert os.path.exists(out)
    assert zipfile.is_zipfile(out)          # .docx ist ein ZIP
    with zipfile.ZipFile(out) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    assert "Punkt eins" in xml               # Listeninhalt übernommen
    assert "berschrift" in xml               # Überschrift übernommen
    assert "Merke" in xml                    # Merke-Box übernommen


def test_make_docx_renders_table(tmp_path):
    page = {
        "type": "page", "name": "Tab", "material": True,
        "content": "<table><tr><th>A</th><th>B</th></tr>"
                   "<tr><td>1</td><td>2</td></tr></table>",
    }
    out = str(tmp_path / "tab.docx")
    make_docx(page, str(tmp_path), out, str(tmp_path))
    with zipfile.ZipFile(out) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    assert "<w:tbl>" in xml and "1" in xml and "2" in xml
