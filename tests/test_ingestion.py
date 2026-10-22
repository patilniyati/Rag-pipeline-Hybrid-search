from pathlib import Path
from src.ingestion.loaders import load_md, load_html
from src.ingestion.normalisation import normalise
from src.ingestion import store


def test_markdown_ignores_hash_in_code_block(tmp_path):
    f = tmp_path / "a.md"
    f.write_text("# Setup\nIntro.\n```\n# not a heading\n```\n## Install\nRun it.\n")
    sections = load_md(f)
    assert sections[0].heading_path == ["Setup"]
    assert "# not a heading" in sections[0].text
    assert sections[1].heading_path == ["Setup", "Install"]


def test_html_removes_nav_and_footer(tmp_path):
    f = tmp_path / "a.html"
    f.write_text("<nav>Home | About</nav><h1>Guide</h1><p>Hello.</p>"
                 "<footer>Copyright 2026</footer>")
    text = " ".join(s.text for s in load_html(f))
    assert "Hello." in text
    assert "Home" not in text
    assert "Copyright" not in text


def test_html_table_becomes_rows(tmp_path):
    f = tmp_path / "a.html"
    f.write_text("<h1>Pricing</h1><table><tr><th>Plan</th><th>Cost</th></tr>"
                 "<tr><td>Basic</td><td>$10</td></tr></table>")
    assert "Basic | $10" in load_html(f)[0].text


def test_normalise_collapses_whitespace():
    assert normalise("a   b\n\n\n\nc") == "a b\n\nc"


def test_same_file_gets_same_id_and_one_raw_copy(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "RAW_DIR", tmp_path / "raw")
    f = tmp_path / "x.txt"
    f.write_text("hello")
    id1, id2 = store.save_raw(f), store.save_raw(f)
    assert id1 == id2
    assert len(list((tmp_path / "raw").iterdir())) == 1