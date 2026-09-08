"""
PDF Parser — extracts text page-by-page, with fallback table handling.

Strategy:
  1. Try pdfplumber first (better table extraction).
  2. Fall back to PyMuPDF (fitz) if pdfplumber fails.

Returns a list of PageChunk dicts:
  {
      "page_number": int,         # 1-based
      "text": str,                # full text of the page
      "tables": list[list[str]],  # raw cell strings from any tables found
  }
"""

import logging
from pathlib import Path
from typing import TypedDict

logger = logging.getLogger(__name__)


class PageChunk(TypedDict):
    page_number: int
    text: str
    tables: list[list[list[str]]]  # tables[t][row][col]


def parse_pdf(filepath: str | Path) -> list[PageChunk]:
    """
    Parse a PDF and return a PageChunk per page.
    Tries pdfplumber; falls back to PyMuPDF.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {filepath}")

    try:
        chunks = _parse_with_pdfplumber(path)
        logger.info("Parsed %s with pdfplumber (%d pages)", path.name, len(chunks))
        return chunks
    except Exception as e:
        logger.warning("pdfplumber failed (%s); trying PyMuPDF: %s", path.name, e)

    chunks = _parse_with_pymupdf(path)
    logger.info("Parsed %s with PyMuPDF (%d pages)", path.name, len(chunks))
    return chunks


# --------------------------------------------------------------------------- #
#  pdfplumber implementation
# --------------------------------------------------------------------------- #

def _parse_with_pdfplumber(path: Path) -> list[PageChunk]:
    import pdfplumber  # type: ignore

    chunks: list[PageChunk] = []
    with pdfplumber.open(str(path)) as pdf:
        for page_index, page in enumerate(pdf.pages):
            page_number = page_index + 1

            # Extract prose text
            text = page.extract_text(x_tolerance=3, y_tolerance=3) or ""

            # Extract tables and serialise each cell to string
            raw_tables = page.extract_tables() or []
            serialised_tables: list[list[list[str]]] = []
            for table in raw_tables:
                serialised_table: list[list[str]] = []
                for row in (table or []):
                    serialised_table.append(
                        [str(cell).strip() if cell is not None else "" for cell in row]
                    )
                serialised_tables.append(serialised_table)

            # Append table text to page text for LLM context
            table_text_parts: list[str] = []
            for table in serialised_tables:
                for row in table:
                    row_text = " | ".join(cell for cell in row if cell)
                    if row_text:
                        table_text_parts.append(row_text)

            if table_text_parts:
                text = text + "\n\n[TABLE DATA]\n" + "\n".join(table_text_parts)

            chunks.append(
                PageChunk(
                    page_number=page_number,
                    text=text.strip(),
                    tables=serialised_tables,
                )
            )
    return chunks


# --------------------------------------------------------------------------- #
#  PyMuPDF fallback implementation
# --------------------------------------------------------------------------- #

def _parse_with_pymupdf(path: Path) -> list[PageChunk]:
    import fitz  # type: ignore  (PyMuPDF)

    chunks: list[PageChunk] = []
    doc = fitz.open(str(path))
    try:
        for page_index in range(len(doc)):
            page = doc[page_index]
            page_number = page_index + 1
            text = page.get_text("text") or ""
            chunks.append(
                PageChunk(
                    page_number=page_number,
                    text=text.strip(),
                    tables=[],  # PyMuPDF table extraction requires extra work; skip for fallback
                )
            )
    finally:
        doc.close()
    return chunks
