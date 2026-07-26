# Tests PDF document extraction and routing.

import sys
import tempfile
import unittest
from pathlib import Path

import pymupdf


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIRECTORY = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIRECTORY))

from document_router import extract_document_units
from pdf_adapter import (
    extract_pdf_units,
    flatten_table_rows,
)


class PdfAdapterTests(unittest.TestCase):
    def create_pdf(self, build_document):
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)

        file_path = (
            Path(temporary_directory.name)
            / "test-document.pdf"
        )

        with pymupdf.open() as document:
            build_document(document)
            document.save(file_path)

        return file_path

    def create_readable_pdf(self):
        def build_document(document):
            first_page = document.new_page()
            first_page.insert_text(
                (72, 72),
                "Mission Overview",
                fontsize=20,
            )
            first_page.insert_text(
                (72, 120),
                "First page body text.",
                fontsize=11,
            )

            second_page = document.new_page()
            second_page.insert_text(
                (72, 72),
                "Second page body text.",
                fontsize=11,
            )

            document.new_page()

        return self.create_pdf(build_document)

    def test_extracts_readable_pages_and_omits_blank_pages(self):
        units = extract_pdf_units(
            self.create_readable_pdf()
        )

        self.assertEqual(
            [unit["location"] for unit in units],
            ["Page 1", "Page 2"],
        )
        self.assertEqual(
            units[0]["heading"],
            "Mission Overview",
        )
        self.assertIsNone(units[1]["heading"])
        self.assertIn(
            "First page body text.",
            units[0]["text"],
        )
        self.assertIn(
            "Second page body text.",
            units[1]["text"],
        )

    def test_textless_pdf_raises_clear_error(self):
        def build_document(document):
            document.new_page()
            document.new_page()

        with self.assertRaisesRegex(
            ValueError,
            "no extractable text.*require OCR",
        ):
            extract_pdf_units(
                self.create_pdf(build_document)
            )

    def test_router_routes_pdf_files(self):
        file_path = self.create_readable_pdf()

        self.assertEqual(
            extract_document_units(file_path),
            extract_pdf_units(file_path),
        )

    def test_router_preserves_unsupported_format_errors(self):
        with self.assertRaisesRegex(
            ValueError,
            r"Unsupported document type: \.txt",
        ):
            extract_document_units("notes.txt")

    def test_flattens_non_empty_table_rows(self):
        rows = flatten_table_rows(
            [
                ["Name", "Role", "Status"],
                ["Avery", "Pilot", "Ready"],
                ["", None, "   "],
            ]
        )

        self.assertEqual(
            rows,
            [
                "Name | Role | Status",
                "Avery | Pilot | Ready",
            ],
        )


if __name__ == "__main__":
    unittest.main()
