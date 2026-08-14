"""Focused syllabus detection and course-folder metadata tests."""

import unittest
import sys
from pathlib import Path
from unittest.mock import patch

import pymupdf


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from products.atlas.syllabus_intake import (
    analyze_uploaded_document,
    classify_material_type,
    material_type_for_catalog,
    normalize_course_name,
    normalize_material_type,
)


class SyllabusIntakeTests(unittest.TestCase):
    def test_detects_syllabus_and_reads_course_identity_from_opening_text(self):
        analysis = analyze_uploaded_document(
            "fall-syllabus.txt",
            (
                "Course Syllabus\n"
                "Course Number: FINA 7310\n"
                "Course Title: Corporate Financial Strategy\n"
                "Instructor: Avery Pilot\n"
                "Learning Objectives\n"
            ).encode("utf-8"),
        )

        self.assertTrue(analysis.is_syllabus)
        self.assertEqual(analysis.course_id, "FINA 7310")
        self.assertEqual(analysis.course_name, "Corporate Financial Strategy")
        self.assertEqual(analysis.material_type, "syllabus")

    def test_uses_readable_filename_fallback_when_opening_has_no_labeled_title(self):
        analysis = analyze_uploaded_document(
            "MGMT-6400-Strategic-Innovation-Syllabus.txt",
            b"Syllabus\nInstructor information\nGrading policy\n",
        )

        self.assertEqual(analysis.course_id, "MGMT 6400")
        self.assertEqual(analysis.course_name, "Strategic Innovation")

    def test_term_line_is_not_mistaken_for_the_adjacent_course_code(self):
        analysis = analyze_uploaded_document(
            "course-syllabus.txt",
            (
                "Course Syllabus\n"
                "Fall 2026\n"
                "FINA 7310\n"
                "Corporate Financial Strategy\n"
                "Instructor: Avery Pilot\n"
            ).encode("utf-8"),
        )

        self.assertEqual(analysis.course_id, "FINA 7310")
        self.assertEqual(analysis.course_name, "Corporate Financial Strategy")

    def test_non_syllabus_does_not_create_a_course(self):
        analysis = analyze_uploaded_document(
            "week-2-class-notes.txt",
            b"Discussion notes for the second week.\n",
        )

        self.assertFalse(analysis.is_syllabus)
        self.assertIsNone(analysis.course_id)
        self.assertIsNone(analysis.course_name)
        self.assertEqual(analysis.material_type, "notes")

        self.assertEqual(
            classify_material_type(
                "lecture-2.txt",
                "Check the syllabus before next week's lecture.",
            ),
            "lectures",
        )

    def test_material_categories_are_bounded_and_reviewable(self):
        cases = {
            "course-syllabus.pdf": "syllabus",
            "week-4-lecture-slides.pptx": "lectures",
            "class_notes.md": "notes",
            "hw-03.docx": "homework",
            "reading-list.pdf": "other",
        }
        for file_name, expected in cases.items():
            with self.subTest(file_name=file_name):
                self.assertEqual(classify_material_type(file_name), expected)

        self.assertEqual(normalize_material_type(None), "other")
        with self.assertRaises(ValueError):
            normalize_material_type("exams")
        self.assertEqual(material_type_for_catalog("exams"), "other")

    def test_preview_consumes_only_the_bounded_opening_units(self):
        consumed = []

        def opening_units(_file_path):
            for index in range(8):
                consumed.append(index)
                yield {
                    "heading": None,
                    "text": "Course Syllabus\nFINA 7310\nCorporate Finance",
                }
            raise AssertionError("preview consumed a later unit")

        analysis = analyze_uploaded_document(
            "course-syllabus.pdf",
            b"bounded fixture",
            unit_extractor=opening_units,
        )

        self.assertTrue(analysis.is_syllabus)
        self.assertEqual(consumed, list(range(8)))

    def test_pdf_preview_does_not_read_syllabus_text_after_page_eight(self):
        document = pymupdf.open()
        try:
            for page_number in range(1, 10):
                page = document.new_page()
                page.insert_text(
                    (72, 72),
                    (
                        "Course Syllabus FINA 7310 Corporate Finance"
                        if page_number == 9
                        else f"Reading material page {page_number}"
                    ),
                )
            file_bytes = document.tobytes()
        finally:
            document.close()

        analysis = analyze_uploaded_document("reading-material.pdf", file_bytes)

        self.assertFalse(analysis.is_syllabus)
        self.assertIsNone(analysis.course_id)

    def test_oversized_preview_falls_back_without_extracting_content(self):
        with patch(
            "products.atlas.syllabus_intake.MAX_PREVIEW_FILE_BYTES",
            1,
        ):
            analysis = analyze_uploaded_document(
                "FINA-7310-Corporate-Finance-Syllabus.pdf",
                b"too large",
                unit_extractor=lambda _path: (_ for _ in ()).throw(
                    AssertionError("oversized preview should not be extracted")
                ),
            )

        self.assertTrue(analysis.is_syllabus)
        self.assertEqual(analysis.course_id, "FINA 7310")
        self.assertEqual(analysis.course_name, "Corporate Finance")

    def test_course_folder_name_is_bounded_and_rejects_controls(self):
        self.assertEqual(
            normalize_course_name("  Strategy   & Innovation  "),
            "Strategy & Innovation",
        )
        with self.assertRaises(ValueError):
            normalize_course_name("Unsafe\nName")


if __name__ == "__main__":
    unittest.main()
