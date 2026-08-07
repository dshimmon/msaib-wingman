"""Extract normalized, row-addressable units from inert UTF-8 CSV files."""

import csv
import io
from pathlib import Path

from wingman.core.document_errors import (
    DocumentDecodingError,
    NoReadableContentError,
)


def decode_csv(file_path):
    """Decode CSV as UTF-8 deterministically, accepting an optional BOM."""
    path = Path(file_path)
    try:
        return path.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise DocumentDecodingError(
            "CSV document must be valid UTF-8."
        ) from error


def stable_headers(row):
    """Return non-empty, unique labels for every physical column."""
    labels = []
    seen = set()
    for column_number, value in enumerate(row, start=1):
        label = value.strip() or f"Column {column_number}"
        if label in seen:
            label = f"{label} (Column {column_number})"
        labels.append(label)
        seen.add(label)
    return labels


def format_row(row, headers):
    """Preserve column relationships, including meaningful empty cells."""
    width = max(len(row), len(headers))
    values = list(row) + [""] * (width - len(row))
    labels = list(headers) + [
        f"Column {column_number}"
        for column_number in range(len(headers) + 1, width + 1)
    ]
    return " | ".join(
        f"{label}: {value.strip()}"
        for label, value in zip(labels, values)
    )


def extract_csv_units(file_path):
    """Extract the header and each non-empty data row as stable units."""
    text = decode_csv(file_path)
    try:
        rows = list(csv.reader(io.StringIO(text, newline=""), strict=True))
    except csv.Error as error:
        raise ValueError(f"CSV document is unreadable: {error}") from error

    non_empty_rows = [
        (row_number, row)
        for row_number, row in enumerate(rows, start=1)
        if any(value.strip() for value in row)
    ]
    if not non_empty_rows:
        raise NoReadableContentError(
            "CSV document contains no readable rows."
        )

    header_row_number, header_row = non_empty_rows[0]
    headers = stable_headers(header_row)
    units = [
        {
            "heading": "CSV columns",
            "location": f"Row {header_row_number}",
            "text": " | ".join(headers),
        }
    ]
    for row_number, row in non_empty_rows[1:]:
        units.append(
            {
                "heading": None,
                "location": f"Row {row_number}",
                "text": format_row(row, headers),
            }
        )
    return units
