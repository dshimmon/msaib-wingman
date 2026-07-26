# Extracts normalized document units from Word files.

import re

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph


HEADING_STYLE_PATTERN = re.compile(
    r"^Heading\s+\d+$",
    re.IGNORECASE,
)


def is_heading(paragraph):
    """
    Return whether a paragraph uses a numbered Word heading style.
    """
    style_name = (
        paragraph.style.name
        if paragraph.style
        else ""
    )

    return bool(
        HEADING_STYLE_PATTERN.match(style_name)
    )


def extract_table_rows(table):
    """
    Flatten non-empty table rows into readable text.
    """
    rows = []

    for row in table.rows:
        cell_values = [
            cell.text.strip()
            for cell in row.cells
        ]

        if any(cell_values):
            rows.append(" | ".join(cell_values))

    return rows


def extract_word_units(file_path):
    """
    Extract section-based normalized units from a .docx file.
    """
    document = Document(file_path)
    sections = []
    current_heading = None
    current_text = []

    def append_current_section():
        if not current_text:
            return

        sections.append(
            {
                "heading": current_heading,
                "text": "\n".join(current_text),
            }
        )

    for block in document.iter_inner_content():
        if isinstance(block, Paragraph):
            paragraph_text = block.text.strip()

            if not paragraph_text:
                continue

            if is_heading(block):
                append_current_section()
                current_heading = paragraph_text
                current_text = [paragraph_text]
            else:
                current_text.append(paragraph_text)

        elif isinstance(block, Table):
            current_text.extend(
                extract_table_rows(block)
            )

    append_current_section()

    return [
        {
            "heading": section["heading"],
            "location": f"Section {section_number}",
            "text": section["text"],
        }
        for section_number, section in enumerate(
            sections,
            start=1,
        )
    ]
