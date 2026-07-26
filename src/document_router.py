# Routes supported documents to their format-specific adapters.

from pathlib import Path

from excel_adapter import extract_excel_units
from pdf_adapter import extract_pdf_units
from powerpoint_adapter import (
    extract_powerpoint_units,
)
from word_adapter import extract_word_units


SUPPORTED_EXTENSIONS = {
    ".pptx",
    ".pdf",
    ".docx",
    ".xlsx",
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

    raise NotImplementedError(
        f"The {extension} adapter is not built yet."
    )
