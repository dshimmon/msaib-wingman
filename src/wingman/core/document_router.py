# Routes supported documents to their format-specific adapters.

from pathlib import Path

from wingman.core.csv_adapter import extract_csv_units
from wingman.core.excel_adapter import extract_excel_units
from wingman.core.pdf_adapter import extract_pdf_units
from wingman.core.powerpoint_adapter import (
    extract_powerpoint_units,
)
from wingman.core.word_adapter import extract_word_units
from wingman.core.text_adapter import (
    extract_markdown_units,
    extract_text_units,
)


SUPPORTED_EXTENSIONS = {
    ".pptx",
    ".pdf",
    ".docx",
    ".xlsx",
    ".csv",
    ".txt",
    ".md",
    ".markdown",
}


def extract_document_units(file_path):
    """
    Route a document to the correct extraction adapter.
    """
    extension = Path(file_path).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported document type: {extension}"
        )

    if extension == ".pptx":
        return extract_powerpoint_units(file_path)

    if extension == ".pdf":
        return extract_pdf_units(file_path)

    if extension == ".docx":
        return extract_word_units(file_path)

    if extension == ".xlsx":
        return extract_excel_units(file_path)

    if extension == ".csv":
        return extract_csv_units(file_path)

    if extension == ".txt":
        return extract_text_units(file_path)

    if extension in {".md", ".markdown"}:
        return extract_markdown_units(file_path)

    raise NotImplementedError(
        f"The {extension} adapter is not built yet."
    )
