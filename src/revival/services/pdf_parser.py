from __future__ import annotations

from dataclasses import dataclass

import pymupdf


@dataclass
class PageContent:
    page_number: int
    text: str


def extract_pages(pdf_bytes: bytes) -> list[PageContent]:
    """Extract text from each page of a PDF."""
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    pages: list[PageContent] = []
    for i, page in enumerate(doc):
        text = page.get_text().strip()
        if text:
            pages.append(PageContent(page_number=i + 1, text=text))
    doc.close()
    return pages
