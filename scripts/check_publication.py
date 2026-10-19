#!/usr/bin/env python3
"""공개 문서의 지면·링크·본문 누락과 공개 파일 범위를 확인한다."""
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlparse

import fitz

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"


class HTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.links, self.images = [], [], []
        self.stack, self.pieces = [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.append(a["id"])
        if tag in ("a", "link") and a.get("href"):
            self.links.append(a["href"])
        if tag == "img":
            self.images.append(a["src"])
        if tag in ("p", "h1", "h2", "h3", "td", "th", "li", "figcaption"):
            self.stack.append([tag, []])

    def handle_data(self, text):
        for entry in self.stack:
            entry[1].append(text)

    def handle_endtag(self, tag):
        if self.stack and self.stack[-1][0] == tag:
            self.pieces.append("".join(self.stack.pop()[1]))


def compact(value):
    return re.sub(r"\s+", "", value)


def main():
    checks = []
    for name, cover in (("AnchorBridge_Public_Brief", "brief-cover"), ("AnchorBridge_Public_Methods", "methods-cover")):
        doc = fitz.open(SITE / f"documents/{name}.pdf")
        page = doc[0]
        page.get_pixmap(matrix=fitz.Matrix(600 / page.rect.width, 600 / page.rect.width)).save(SITE / f"assets/{cover}.png")
    for path in SITE.rglob("*.html"):
        text = path.read_text()
        parsed = HTML(); parsed.feed(text)
        assert len(set(parsed.ids)) == len(parsed.ids), (path, "duplicate ID")
        assert "__DATA__" not in text and "__CSS__" not in text
        for link in parsed.links + parsed.images:
            url = urlparse(link)
            if url.scheme or link == "/":
                continue
            target = SITE / unquote(url.path).lstrip("/") if url.path.startswith("/") else path.parent / unquote(url.path)
            if not url.path:
                target = path
            if target.is_dir():
                target /= "index.html"
            assert target.exists(), (path, "missing target", link)
            if url.fragment and target.suffix == ".html":
                target_html = HTML(); target_html.feed(target.read_text())
                assert unquote(url.fragment) in target_html.ids, (path, "missing anchor", link)
        checks.append(f"HTML links and IDs: {path.relative_to(SITE)}")
    for source, name, count, cover in (("brief", "AnchorBridge_Public_Brief", 4, "brief-cover"),
                                       ("methods", "AnchorBridge_Public_Methods", 10, "methods-cover")):
        path = SITE / f"documents/{name}.pdf"
        doc = fitz.open(path)
        assert len(doc) == count, (path, len(doc))
        assert doc.get_toc(), (path, "no bookmarks")
        assert all(1 <= item[2] <= count for item in doc.get_toc())
        text = compact("".join(p.get_text() for p in doc))
        parsed = HTML(); parsed.feed((ROOT / f"documents/{source}.html").read_text())
        missing = [p for p in parsed.pieces if compact(p) and compact(p) not in text]
        assert not missing, (path, "missing body fragments", missing)
        for n, page in enumerate(doc):
            assert len(page.get_text()) > 250, (path, n, "near-empty page")
            assert "\ufffd" not in page.get_text()
            for link in page.get_links():
                if link["kind"] == fitz.LINK_GOTO:
                    assert 0 <= link["page"] < count
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    for span in line["spans"]:
                        x0, y0, x1, y1 = span["bbox"]
                        assert x0 >= 0 and y0 >= 0 and x1 <= page.rect.width + 1 and y1 <= page.rect.height + 1, (path, n, span)
            if n == 0:
                page.get_pixmap(matrix=fitz.Matrix(600 / page.rect.width, 600 / page.rect.width)).save(SITE / f"assets/{cover}.png")
        subprocess.run(["qpdf", "--check", str(path)], check=True, capture_output=True)
        checks.append(f"PDF {count} pages, all text, bounds, bookmarks, links, qpdf: {name}")
    # Explicit region/result exclusion for the agreed public edition.
    forbidden = ("대전광역시", "영암군", "남원시", "35.08", "22.53", "0.948", "1.156", "7.05", "242,574")
    for folder in ("analysis", "web", "documents", "site"):
        for path in (ROOT / folder).rglob("*"):
            if path.suffix in (".py", ".html", ".css", ".md", ".json"):
                text = path.read_text()
            elif path.suffix == ".pdf":
                doc = fitz.open(path); text = "\n".join(p.get_text() for p in doc)
                assert not doc.embfile_count(), (path, "embedded files")
            else:
                continue
            assert not [term for term in forbidden if term in text], (path, "private result signature")
    for path in SITE.rglob("*"):
        assert path.suffix not in (".csv", ".zip"), path
    checks.append("public sources/artifacts exclude original result signatures and embedded data attachments")
    output = ROOT / ".cache"
    output.mkdir(exist_ok=True)
    (output / "publication-checks.json").write_text(json.dumps({"checks": checks}, ensure_ascii=False, indent=2))
    print("\n".join("PASS " + c for c in checks))


if __name__ == "__main__":
    main()
