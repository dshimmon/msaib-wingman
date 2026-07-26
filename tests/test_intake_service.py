# Tests isolated uploaded-document intake behavior.

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIRECTORY = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIRECTORY))

import intake_service


class IntakeServiceTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )
        self.addCleanup(
            self.temporary_directory.cleanup
        )
        self.uploads_directory = (
            Path(self.temporary_directory.name)
            / "uploads"
        )
        self.uploads_patch = patch.object(
            intake_service,
            "UPLOADS_DIRECTORY",
            self.uploads_directory,
        )
        self.uploads_patch.start()
        self.addCleanup(self.uploads_patch.stop)

    @patch.object(
        intake_service,
        "register_source",
    )
    @patch.object(
        intake_service,
        "ingest_document",
        return_value=[{"id": "knowledge-1"}],
    )
    @patch.object(
        intake_service,
        "find_source_by_content_hash",
        return_value=(None, None),
    )
    def test_successful_supported_file_intake(
        self,
        find_source,
        ingest_document,
        register_source,
    ):
        file_bytes = b"synthetic docx content"
        content_hash = hashlib.sha256(
            file_bytes
        ).hexdigest()

        result = intake_service.ingest_uploaded_document(
            "mission_notes.docx",
            file_bytes,
            domain="Academics",
            program="MSAIB",
            academic_year="2026-2027",
        )

        expected_source_id = (
            f"mission-notes-{content_hash[:12]}"
        )
        source_directory = (
            self.uploads_directory
            / expected_source_id
        )
        original_path = (
            source_directory
            / "mission_notes.docx"
        )
        output_path = (
            source_directory
            / f"{expected_source_id}.json"
        )

        self.assertEqual(result["status"], "ingested")
        self.assertEqual(
            result["source_id"],
            expected_source_id,
        )
        self.assertEqual(
            original_path.read_bytes(),
            file_bytes,
        )
        find_source.assert_called_once_with(content_hash)
        ingest_document.assert_called_once_with(
            file_path=original_path,
            domain="Academics",
            output_path=output_path,
            source_id=expected_source_id,
        )

        registered_source_id, metadata = (
            register_source.call_args.args
        )
        self.assertEqual(
            registered_source_id,
            expected_source_id,
        )
        self.assertEqual(
            {
                key: metadata[key]
                for key in (
                    "display_name",
                    "file_name",
                    "file_type",
                    "mime_type",
                    "domain",
                    "program",
                    "academic_year",
                    "original_path",
                    "content_hash",
                )
            },
            {
                "display_name": "Mission Notes",
                "file_name": "mission_notes.docx",
                "file_type": "docx",
                "mime_type": (
                    "application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document"
                ),
                "domain": "Academics",
                "program": "MSAIB",
                "academic_year": "2026-2027",
                "original_path": str(original_path),
                "content_hash": content_hash,
            },
        )
        self.assertTrue(metadata["uploaded_at"])

    @patch.object(
        intake_service,
        "register_source",
    )
    @patch.object(
        intake_service,
        "ingest_document",
    )
    @patch.object(
        intake_service,
        "find_source_by_content_hash",
    )
    def test_duplicate_content_is_not_written_or_ingested(
        self,
        find_source,
        ingest_document,
        register_source,
    ):
        find_source.return_value = (
            "existing-source",
            {"display_name": "Existing Source"},
        )

        result = intake_service.ingest_uploaded_document(
            "duplicate.pdf",
            b"same content",
        )

        self.assertEqual(
            result["status"],
            "already_exists",
        )
        self.assertFalse(
            self.uploads_directory.exists()
        )
        ingest_document.assert_not_called()
        register_source.assert_not_called()

    def test_unsupported_extension_raises_value_error(self):
        with self.assertRaisesRegex(
            ValueError,
            r"Unsupported document type: \.txt",
        ):
            intake_service.ingest_uploaded_document(
                "notes.txt",
                b"content",
            )

    def test_empty_upload_raises_value_error(self):
        with self.assertRaisesRegex(
            ValueError,
            "Uploaded document is empty.",
        ):
            intake_service.ingest_uploaded_document(
                "empty.docx",
                b"",
            )

    @patch.object(
        intake_service,
        "register_source",
    )
    @patch.object(
        intake_service,
        "find_source_by_content_hash",
        return_value=(None, None),
    )
    def test_ingestion_failure_cleans_up_and_reraises(
        self,
        find_source,
        register_source,
    ):
        error = RuntimeError("ingestion failed")
        file_bytes = b"broken workbook"
        source_id = intake_service.create_source_id(
            "broken.xlsx",
            hashlib.sha256(file_bytes).hexdigest(),
        )
        source_directory = (
            self.uploads_directory
            / source_id
        )
        original_path = source_directory / "broken.xlsx"
        output_path = (
            source_directory
            / f"{source_id}.json"
        )

        def fail_ingestion(**kwargs):
            kwargs["output_path"].write_text(
                "partial output",
                encoding="utf-8",
            )
            raise error

        with patch.object(
            intake_service,
            "ingest_document",
            side_effect=fail_ingestion,
        ):
            with self.assertRaises(RuntimeError) as caught:
                intake_service.ingest_uploaded_document(
                    "broken.xlsx",
                    file_bytes,
                )

        self.assertIs(caught.exception, error)
        self.assertFalse(original_path.exists())
        self.assertFalse(output_path.exists())
        self.assertFalse(source_directory.exists())
        register_source.assert_not_called()

    def test_create_display_name_is_friendly(self):
        self.assertEqual(
            intake_service.create_display_name(
                "mission-022_intake-notes.docx"
            ),
            "Mission 022 Intake Notes",
        )

    def test_create_source_id_is_stable_and_safe(self):
        content_hash = "abcdef1234567890"

        first_id = intake_service.create_source_id(
            "Unsafe Name! (Final).PDF",
            content_hash,
        )
        second_id = intake_service.create_source_id(
            "Unsafe Name! (Final).PDF",
            content_hash,
        )

        self.assertEqual(
            first_id,
            "unsafe-name-final-abcdef123456",
        )
        self.assertEqual(first_id, second_id)


if __name__ == "__main__":
    unittest.main()
