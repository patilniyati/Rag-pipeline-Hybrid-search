import pymupdf
from src.ingestion.loaders import load_pdf


def test_repeated_header_and_footer_are_removed(tmp_path):
    doc = pymupdf.open()
    for i in range(4):
        page = doc.new_page()
        page.insert_text((72, 30), "ACME Confidential", fontsize=9)
        page.insert_text((72, 400), f"Body text number {i} explains a thing.", fontsize=11)
        page.insert_text((72, 820), f"Page {i + 1} of 4", fontsize=9)
    path = tmp_path / "a.pdf"
    doc.save(str(path))
    text = " ".join(s.text for s in load_pdf(path))
    assert "Body text" in text
    assert "Confidential" not in text
    assert "Page" not in text