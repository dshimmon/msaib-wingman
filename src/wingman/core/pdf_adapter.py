# Extracts normalized document units from PDF files.

import re
import statistics

import pymupdf

from wingman.core.document_errors import NoExtractableTextError


MAX_HEADING_WORDS = 12
MAX_HEADING_CHARACTERS = 120
MIN_HEADING_FONT_SIZE = 14


def get_text_spans(page):
    """
    Return non-empty text spans with their size and position.
    """
    spans = []
    page_text = page.get_text("dict", sort=True)

    for block in page_text.get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "").strip()

                if text:
                    spans.append(
                        {
                            "text": text,
                            "size": span.get("size", 0),
                            "top": span.get(
                                "bbox",
                                (0, 0, 0, 0),
                            )[1],
                        }
                    )

    return spans


def detect_page_heading(page):
    """
    Conservatively identify a likely heading near the page top.
    """
    spans = get_text_spans(page)

    if not spans:
        return None

    top_limit = min(
        144,
        page.rect.height * 0.25,
    )
    candidates = [
        span
        for span in spans
        if span["top"] <= top_limit
        and len(span["text"].split()) <= MAX_HEADING_WORDS
        and len(span["text"]) <= MAX_HEADING_CHARACTERS
    ]

    if not candidates:
        return None

    best_candidate = min(
        candidates,
        key=lambda span: (
            -span["size"],
            span["top"],
        ),
    )

    if best_candidate["size"] < MIN_HEADING_FONT_SIZE:
        return None

    other_font_sizes = [
        span["size"]
        for span in spans
        if span is not best_candidate
    ]

    if other_font_sizes:
        typical_font_size = statistics.median(
            other_font_sizes
        )

        if best_candidate["size"] < typical_font_size * 1.2:
            return None

    elif best_candidate["size"] < 16:
        return None

    return best_candidate["text"]


def flatten_table_rows(rows):
    """
    Convert non-empty extracted table rows to pipe-separated text.
    """
    flattened_rows = []

    for row in rows:
        cell_values = [
            re.sub(
                r"\s+",
                " ",
                str(cell).strip(),
            )
            if cell is not None
            else ""
            for cell in row
        ]

        if any(cell_values):
            flattened_rows.append(
                " | ".join(cell_values)
            )

    return flattened_rows


def normalize_comparison_text(text):
    """
    Normalize text for conservative duplicate detection.
    """
    return " ".join(text.lower().split())


def extract_page_tables(page, page_text):
    """
    Best-effort extraction of table rows missing from page text.
    """
    table_rows = []
    normalized_page_text = normalize_comparison_text(
        page_text
    )

    try:
        tables = page.find_tables()

        for table in tables.tables:
            for row_text in flatten_table_rows(
                table.extract()
            ):
                cell_values = [
                    value.strip()
                    for value in row_text.split("|")
                    if value.strip()
                ]

                if cell_values and all(
                    normalize_comparison_text(value)
                    in normalized_page_text
                    for value in cell_values
                ):
                    continue

                table_rows.append(row_text)
    except Exception:
        return []

    return table_rows


def extract_pdf_units(file_path):
    """
    Extract one normalized document unit per readable PDF page.
    """
    units = []

    with pymupdf.open(file_path) as document:
        for page_number, page in enumerate(
            document,
            start=1,
        ):
            page_text = page.get_text(
                "text",
                sort=True,
            ).strip()
            table_rows = extract_page_tables(
                page,
                page_text,
            )
            text_parts = []

            if page_text:
                text_parts.append(page_text)

            if table_rows:
                text_parts.append(
                    "\n".join(table_rows)
                )

            combined_text = "\n".join(text_parts).strip()

            if not combined_text:
                continue

            units.append(
                {
                    "heading": detect_page_heading(page),
                    "location": f"Page {page_number}",
                    "text": combined_text,
                }
            )

    if not units:
        raise NoExtractableTextError(
            "PDF contains no extractable text and may require OCR."
        )

    return units
