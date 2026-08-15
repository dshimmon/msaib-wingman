# Tests isolated uploaded-document intake behavior.

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIRECTORY = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIRECTORY))

import products.atlas.intake_service as intake_service
import wingman.core.concept_registry_storage as concept_registry_storage
import wingman.core.embedding_storage as embedding_storage


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

        with patch.object(
            intake_service.source_summary_service,
            "generate_and_persist_summary",
            return_value={"status": "ready"},
        ) as generate_summary:
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
        self.assertEqual(result["summary_status"], "ready")
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
        generate_summary.assert_called_once_with(
            source_id=expected_source_id,
            source_hash=content_hash,
            original_path=original_path,
            knowledge_objects=[{"id": "knowledge-1"}],
        )

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
    def test_summary_failure_preserves_successfully_ingested_source(
        self,
        find_source,
        ingest_document,
        register_source,
    ):
        with patch.object(
            intake_service.source_summary_service,
            "generate_and_persist_summary",
            side_effect=OSError("private model failure"),
        ):
            result = intake_service.ingest_uploaded_document(
                "course-notes.txt",
                b"Source-backed notes",
            )

        source_directory = self.uploads_directory / result["source_id"]
        self.assertEqual(result["status"], "ingested")
        self.assertEqual(result["summary_status"], "failed")
        self.assertTrue((source_directory / "course-notes.txt").is_file())
        ingest_document.assert_called_once()
        register_source.assert_called_once()

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
            r"Unsupported document type: \.rtf",
        ):
            intake_service.ingest_uploaded_document(
                "notes.rtf",
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

    def test_mime_types_cover_every_routed_extension(self):
        self.assertEqual(
            set(intake_service.MIME_TYPES),
            set(intake_service.SUPPORTED_EXTENSIONS),
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

    def atomic_store_patches(self):
        root = Path(self.temporary_directory.name)
        return (
            patch.object(
                embedding_storage,
                "EMBEDDINGS_PATH",
                root / "embeddings.json",
            ),
            patch.object(
                concept_registry_storage,
                "REGISTRY_PATH",
                root / "concepts.json",
            ),
        )

    @patch.object(intake_service, "register_source")
    @patch.object(
        intake_service,
        "find_source_by_content_hash",
        return_value=(None, None),
    )
    def test_atomic_failure_restores_shared_stores_and_source_files(
        self,
        find_source,
        register_source,
    ):
        embeddings_patch, concepts_patch = self.atomic_store_patches()
        with embeddings_patch, concepts_patch:
            embedding_storage.EMBEDDINGS_PATH.write_text(
                '{"existing": {"embedding": [1]}}',
                encoding="utf-8",
            )
            concept_registry_storage.REGISTRY_PATH.write_text(
                '{"existing": {"occurrences": []}}',
                encoding="utf-8",
            )
            embedding_before = embedding_storage.EMBEDDINGS_PATH.read_bytes()
            concept_before = concept_registry_storage.REGISTRY_PATH.read_bytes()

            def fail_after_mutations(**kwargs):
                kwargs["output_path"].write_text("partial", encoding="utf-8")
                embedding_storage.EMBEDDINGS_PATH.write_text(
                    json.dumps({"partial": {}}), encoding="utf-8"
                )
                concept_registry_storage.REGISTRY_PATH.write_text(
                    json.dumps({"partial": {}}), encoding="utf-8"
                )
                raise RuntimeError("indexing failed")

            error = None
            with patch.object(
                intake_service,
                "ingest_document",
                side_effect=fail_after_mutations,
            ):
                try:
                    intake_service.ingest_uploaded_document(
                        "atomic.txt",
                        b"source text",
                        atomic=True,
                    )
                except RuntimeError as caught:
                    error = caught

            self.assertIsNotNone(error)
            self.assertTrue(error.cleanup_verified)
            self.assertEqual(error.failure_stage, "extracting")
            self.assertEqual(
                embedding_storage.EMBEDDINGS_PATH.read_bytes(),
                embedding_before,
            )
            self.assertEqual(
                concept_registry_storage.REGISTRY_PATH.read_bytes(),
                concept_before,
            )
            self.assertEqual(list(self.uploads_directory.iterdir()), [])
            register_source.assert_not_called()

    @patch.object(
        intake_service,
        "find_source_by_content_hash",
        return_value=(None, None),
    )
    def test_registration_failure_rolls_back_completed_indexing(self, find_source):
        embeddings_patch, concepts_patch = self.atomic_store_patches()
        with embeddings_patch, concepts_patch:
            def complete_ingestion(**kwargs):
                kwargs["output_path"].write_text("[]", encoding="utf-8")
                embedding_storage.save_embeddings({"new": {}})
                concept_registry_storage.save_registry({"new": {}})
                return [{"id": "knowledge-1"}]

            with (
                patch.object(
                    intake_service,
                    "ingest_document",
                    side_effect=complete_ingestion,
                ),
                patch.object(
                    intake_service,
                    "register_source",
                    side_effect=RuntimeError("registration failed"),
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "registration failed") as caught:
                    intake_service.ingest_uploaded_document(
                        "registration.md",
                        b"# Source",
                        atomic=True,
                    )

            self.assertTrue(caught.exception.cleanup_verified)
            self.assertEqual(caught.exception.failure_stage, "registering")
            self.assertFalse(embedding_storage.EMBEDDINGS_PATH.exists())
            self.assertFalse(concept_registry_storage.REGISTRY_PATH.exists())
            self.assertEqual(list(self.uploads_directory.iterdir()), [])

    @patch.object(
        intake_service,
        "find_source_by_content_hash",
        return_value=(None, None),
    )
    def test_cleanup_failure_is_typed_and_unverified(self, find_source):
        embeddings_patch, concepts_patch = self.atomic_store_patches()
        with embeddings_patch, concepts_patch:
            with (
                patch.object(
                    intake_service,
                    "ingest_document",
                    side_effect=RuntimeError("ingestion failed"),
                ),
                patch.object(
                    intake_service,
                    "restore_file",
                    side_effect=OSError("restore failed"),
                ),
            ):
                with self.assertRaises(intake_service.IntakeRollbackError) as caught:
                    intake_service.ingest_uploaded_document(
                        "rollback.csv",
                        b"Header\nValue\n",
                        atomic=True,
                    )

            self.assertFalse(caught.exception.cleanup_verified)
            self.assertEqual(caught.exception.stage, "extracting")

    @patch.object(intake_service, "register_source")
    @patch.object(
        intake_service,
        "find_source_by_content_hash",
        return_value=(None, None),
    )
    def test_empty_extraction_fails_without_registering(self, find_source, register_source):
        embeddings_patch, concepts_patch = self.atomic_store_patches()
        with embeddings_patch, concepts_patch:
            with patch.object(
                intake_service,
                "ingest_document",
                return_value=[],
            ):
                with self.assertRaisesRegex(
                    ValueError, "no readable content"
                ) as caught:
                    intake_service.ingest_uploaded_document(
                        "empty.pptx",
                        b"presentation container",
                        atomic=True,
                    )
            self.assertTrue(caught.exception.cleanup_verified)
            self.assertEqual(list(self.uploads_directory.iterdir()), [])
            register_source.assert_not_called()

    @patch.object(
        intake_service,
        "find_source_by_content_hash",
        return_value=(None, None),
    )
    def test_interrupted_cleanup_removes_only_unregistered_source_state(
        self,
        find_source,
    ):
        embeddings_patch, concepts_patch = self.atomic_store_patches()
        file_bytes = b"interrupted source"
        content_hash = hashlib.sha256(file_bytes).hexdigest()
        source_id = intake_service.create_source_id(
            "interrupted.txt",
            content_hash,
        )
        with embeddings_patch, concepts_patch:
            source_directory = self.uploads_directory / source_id
            source_directory.mkdir(parents=True)
            (source_directory / "interrupted.txt").write_bytes(file_bytes)
            (source_directory / f"{source_id}.json").write_text(
                "partial", encoding="utf-8"
            )
            embedding_storage.save_embeddings(
                {
                    f"{source_id}_001": {"embedding": [1]},
                    "other_001": {"embedding": [2]},
                }
            )
            concept_registry_storage.save_registry(
                {
                    "shared": {
                        "occurrences": [
                            {"document": source_id},
                            {"document": "other"},
                        ]
                    },
                    "source-only": {
                        "occurrences": [{"document": source_id}]
                    },
                }
            )
            Path(f"{embedding_storage.EMBEDDINGS_PATH}.tmp").write_text(
                "partial", encoding="utf-8"
            )
            Path(f"{concept_registry_storage.REGISTRY_PATH}.tmp").write_text(
                "partial", encoding="utf-8"
            )

            result = intake_service.cleanup_interrupted_upload(
                "interrupted.txt",
                content_hash,
            )

            self.assertFalse(result["registered"])
            self.assertFalse(source_directory.exists())
            self.assertEqual(
                set(embedding_storage.load_embeddings()),
                {"other_001"},
            )
            concepts = concept_registry_storage.load_registry()
            self.assertEqual(set(concepts), {"shared"})
            self.assertEqual(
                concepts["shared"]["occurrences"],
                [{"document": "other"}],
            )
            self.assertFalse(
                Path(f"{embedding_storage.EMBEDDINGS_PATH}.tmp").exists()
            )
            self.assertFalse(
                Path(f"{concept_registry_storage.REGISTRY_PATH}.tmp").exists()
            )


if __name__ == "__main__":
    unittest.main()
