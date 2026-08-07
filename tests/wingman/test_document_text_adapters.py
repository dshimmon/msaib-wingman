"""Focused CSV, plain-text, and Markdown adapter coverage."""

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from wingman.core.csv_adapter import extract_csv_units  # noqa: E402
from wingman.core.document_errors import (  # noqa: E402
    DocumentDecodingError,
    NoReadableContentError,
)
from wingman.core.document_router import extract_document_units  # noqa: E402
from wingman.core.text_adapter import (  # noqa: E402
    extract_markdown_units,
    extract_text_units,
)


class DocumentTextAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)

    def write_bytes(self, name, content):
        path = self.root / name
        path.write_bytes(content)
        return path

    def test_csv_preserves_headers_columns_and_physical_rows(self):
        path = self.write_bytes(
            "courses.csv",
            b"\xef\xbb\xbfCode,Title,Credits\r\nAI 101,Foundations,3\r\n\r\n",
        )

        units = extract_csv_units(path)

        self.assertEqual(units[0]["location"], "Row 1")
        self.assertEqual(units[0]["text"], "Code | Title | Credits")
        self.assertEqual(units[1]["location"], "Row 2")
        self.assertEqual(
            units[1]["text"],
            "Code: AI 101 | Title: Foundations | Credits: 3",
        )

    def test_csv_duplicate_and_blank_headers_receive_stable_labels(self):
        path = self.write_bytes(
            "values.csv",
            b"Name,Name,\nFirst,Second,Third\n",
        )
        units = extract_csv_units(path)
        self.assertEqual(
            units[0]["text"],
            "Name | Name (Column 2) | Column 3",
        )
        self.assertIn("Column 3: Third", units[1]["text"])

    def test_plain_text_uses_stable_contiguous_line_ranges(self):
        path = self.write_bytes(
            "notes.txt",
            b"First line\nSecond line\n\nFourth line\n",
        )
        units = extract_text_units(path)
        self.assertEqual(
            [unit["location"] for unit in units],
            ["Lines 1-2", "Line 4"],
        )
        self.assertEqual(units[0]["text"], "First line\nSecond line")

    def test_markdown_preserves_heading_context_and_literal_content(self):
        path = self.write_bytes(
            "guide.markdown",
            (
                "# Safety\n"
                "Read [the source](https://example.invalid).\n\n"
                "```python\n"
                "# literal code comment\n"
                "raise RuntimeError('never executed')\n"
                "```\n\n"
                "Details\n"
                "-------\n"
                "Keep provenance.\n"
            ).encode("utf-8"),
        )
        units = extract_markdown_units(path)
        self.assertEqual(
            [unit["heading"] for unit in units],
            ["Safety", "Details"],
        )
        self.assertEqual(units[0]["location"], "Lines 1-8")
        self.assertIn("https://example.invalid", units[0]["text"])
        self.assertIn("raise RuntimeError", units[0]["text"])
        self.assertEqual(units[1]["location"], "Lines 9-11")

    def test_text_formats_reject_empty_invalid_and_malformed_content(self):
        for name, extractor in (
            ("empty.csv", extract_csv_units),
            ("empty.txt", extract_text_units),
            ("empty.md", extract_markdown_units),
        ):
            with self.subTest(name=name):
                path = self.write_bytes(name, b" \n\n")
                with self.assertRaises(NoReadableContentError):
                    extractor(path)

        invalid = self.write_bytes("invalid.txt", b"\xff\xfe")
        with self.assertRaisesRegex(DocumentDecodingError, "valid UTF-8"):
            extract_text_units(invalid)

        malformed = self.write_bytes("malformed.csv", b'Header\n"open\n')
        with self.assertRaisesRegex(ValueError, "CSV document is unreadable"):
            extract_csv_units(malformed)

    def test_router_supports_every_new_extension(self):
        fixtures = {
            "rows.csv": b"Header\nValue\n",
            "notes.txt": b"Text\n",
            "notes.md": b"# Heading\nBody\n",
            "notes.markdown": b"Heading\n=======\nBody\n",
        }
        for name, content in fixtures.items():
            with self.subTest(name=name):
                units = extract_document_units(
                    self.write_bytes(name, content)
                )
                self.assertTrue(units)
                self.assertTrue(units[0]["location"])


if __name__ == "__main__":
    unittest.main()
