from pathlib import Path
from .models import Section
from collections import Counter
import re
from bs4 import BeautifulSoup
import pymupdf

MARGIN = 0.10        # top/bottom 10% of the page is the header/footer zone
MIN_REPEAT = 0.30    # a margin line on 30% of pages is a header/footer
_PAGE_NUM = re.compile(r"^(page\s*)?\d+(\s*(of|/)\s*\d+)?$", re.I)


def load_txt(path: Path) -> list[Section]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return [Section(text=text, source=path.name, format="txt")]


def load_md(path: Path) -> list[Section]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    sections = []
    stack = []            
    buffer = []           
    in_code = False       

    def flush():
        text = "\n".join(buffer).strip()
        if text:
            sections.append(Section(text=text, source=path.name,
                                    heading_path=list(stack), format="md"))
        buffer.clear()

    for line in lines:
        if line.strip().startswith("```"):
            in_code = not in_code          # entering or leaving a code block

        match = re.match(r"^(#{1,6})\s+(.*)", line)
        if match and not in_code:
            flush()                        # save text collected so far
            level = len(match.group(1))    # number of # symbols
            stack = stack[: level - 1]     # drop headings at same or deeper level
            stack.append(match.group(2).strip())
        else:
            buffer.append(line)

    flush()                                # save the last section
    return sections


def load_html(path: Path) -> list[Section]:
    html = path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")

    # 1. Delete page junk
    for tag in soup(["script", "style", "nav", "footer", "aside", "header", "noscript"]):
        tag.decompose()

    sections = []
    stack = []        # current headings
    buffer = []       # text under the current heading

    def flush():
        text = "\n\n".join(buffer).strip()
        if text:
            sections.append(Section(text=text, source=path.name,
                                    heading_path=list(stack), format="html"))
        buffer.clear()

    # 2. Walk the page in document order
    tags = ["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "pre", "tr"]
    for el in soup.find_all(tags):
        if el.name.startswith("h") and len(el.name) == 2:      # a heading
            flush()
            level = int(el.name[1])
            stack = stack[: level - 1]
            stack.append(el.get_text(" ", strip=True))
        elif el.name == "tr":                                   # table row
            cells = [c.get_text(" ", strip=True) for c in el.find_all(["th", "td"])]
            buffer.append(" | ".join(c for c in cells if c))
        elif el.find_parent("table") or (el.name == "p" and el.find_parent("li")):
            continue                                            # already counted
        else:
            buffer.append(el.get_text(" ", strip=True))

    flush()
    return sections


def _line_key(line: str) -> str:
    return re.sub(r"\d+", "#", line.strip().lower())


def _in_margin(bbox, page_height) -> bool:
    return bbox[3] < page_height * MARGIN or bbox[1] > page_height * (1 - MARGIN)


def _lines(block):
    for line in block["lines"]:
        text = "".join(s["text"] for s in line["spans"]).strip()
        if text:
            yield line, text


def _repeated_margin_keys(dicts, heights) -> set:
    counts = Counter()
    for d, h in zip(dicts, heights):
        keys = set()
        for b in d["blocks"]:
            if b["type"] == 0:
                for line, text in _lines(b):
                    if _in_margin(line["bbox"], h):
                        keys.add(_line_key(text))
        counts.update(keys)
    need = max(2, MIN_REPEAT * len(dicts))
    return {k for k, c in counts.items() if k and c >= need}


def _read_blocks(d, height, repeated):
    blocks = []
    for b in d["blocks"]:
        if b["type"] != 0:                                   # skip images
            continue
        lines, size = [], 0
        for line, text in _lines(b):
            if _in_margin(line["bbox"], height) and (
                    _line_key(text) in repeated or _PAGE_NUM.match(text)):
                continue                                     # header/footer line
            lines.append(text)
            for s in line["spans"]:
                if s["text"].strip():
                    size = max(size, round(s["size"], 1))
        if lines:
            text = "\n".join(lines)
            text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)     # fix hyphenation
            text = re.sub(r"\n", " ", text)                  # merge chopped lines
            blocks.append({"text": text, "size": size})
    return blocks


def load_pdf(path: Path) -> list[Section]:
    doc = pymupdf.open(path)
    dicts = [p.get_text("dict") for p in doc]
    heights = [p.rect.height for p in doc]
    doc.close()

    repeated = _repeated_margin_keys(dicts, heights)
    if repeated:
        print(f"  removing repeated header/footer lines: {sorted(repeated)}")
    pages = [_read_blocks(d, h, repeated) for d, h in zip(dicts, heights)]

    # body font size, then heading sizes
    size_weight = Counter()
    for blocks in pages:
        for b in blocks:
            size_weight[b["size"]] += len(b["text"])
    body = size_weight.most_common(1)[0][0] if size_weight else 0
    heading_sizes = sorted({b["size"] for blocks in pages for b in blocks
                            if b["size"] >= body * 1.15 and len(b["text"]) <= 120},
                           reverse=True)
    print(f"  body font: {body}, heading font sizes: {heading_sizes}")

    # sections, carrying the heading stack across pages
    sections, stack = [], []
    for i, blocks in enumerate(pages):
        buffer = []

        def flush():
            text = "\n\n".join(buffer).strip()
            if text:
                sections.append(Section(text=text, source=path.name,
                                        heading_path=list(stack),
                                        page=i + 1, format="pdf"))
            buffer.clear()

        for b in blocks:
            if b["size"] in heading_sizes and len(b["text"]) <= 120:
                flush()
                level = heading_sizes.index(b["size"])
                stack = stack[:level]
                stack.append(b["text"])
            else:
                buffer.append(b["text"])
        flush()

        if sum(len(b["text"]) for b in blocks) < 20:
            print(f"  WARNING {path.name} page {i + 1}: almost no text (scanned page?)")
    return sections