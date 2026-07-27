# Tests transactional Atlas Library source management.

import hashlib
import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIRECTORY = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIRECTORY))

import library_management_service
import library_service


class LibraryManagementServiceTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )
        self.addCleanup(
            self.temporary_directory.cleanup
        )
        self.root = Path(self.temporary_directory.name)
        self.uploads_directory = self.root / "uploads"
        self.uploads_directory.mkdir()
        self.state = {
            "sources": {},
            "embeddings": {},
            "concepts": {},
        }
        self.knowledge_path = None

        self.enterContext(
            patch.object(
                library_management_service,
                "UPLOADS_DIRECTORY",
                self.uploads_directory,
            )
        )
        self.load_sources = self.enterContext(
            patch.object(
                library_management_service,
                "load_source_registry",
                side_effect=lambda: deepcopy(
                    self.state["sources"]
                ),
            )
        )
        self.save_sources = self.enterContext(
            patch.object(
                library_management_service,
                "save_source_registry",
                side_effect=self.save_source_registry,
            )
        )
        self.enterContext(
            patch.object(
                library_management_service,
                "load_embeddings",
                side_effect=lambda: deepcopy(
                    self.state["embeddings"]
                ),
            )
        )
        self.save_embeddings = self.enterContext(
            patch.object(
                library_management_service,
                "save_embeddings",
                side_effect=self.save_embedding_index,
            )
        )
        self.enterContext(
            patch.object(
                library_management_service,
                "load_registry",
                side_effect=lambda: deepcopy(
                    self.state["concepts"]
                ),
            )
        )
        self.save_concepts = self.enterContext(
            patch.object(
                library_management_service,
                "save_registry",
                side_effect=self.save_concept_registry,
            )
        )
        self.find_knowledge = self.enterContext(
            patch.object(
                library_management_service,
                "find_knowledge_path",
                side_effect=lambda *args, **kwargs: (
                    self.knowledge_path
                ),
            )
        )
        self.ingest_document = self.enterContext(
            patch.object(
                library_management_service,
                "ingest_document",
                return_value=[],
            )
        )

    def save_source_registry(self, registry):
        self.state["sources"] = deepcopy(registry)

    def save_embedding_index(self, embeddings):
        self.state["embeddings"] = deepcopy(embeddings)

    def save_concept_registry(self, concepts):
        self.state["concepts"] = deepcopy(concepts)

    def create_original(self, source_id="source-one"):
        source_directory = (
            self.uploads_directory
            / source_id
        )
        source_directory.mkdir(
            parents=True,
            exist_ok=True,
        )
        original_path = (
            source_directory
            / "original.docx"
        )
        original_path.write_bytes(b"original")

        return original_path

    def set_reprocessable_source(self):
        original_path = self.create_original()
        self.knowledge_path = (
            original_path.parent
            / "source-one.json"
        )
        self.knowledge_path.write_bytes(
            b'{"previous": true}'
        )
        self.state["sources"] = {
            "source-one": {
                "display_name": "Source One",
                "domain": "Academics",
                "original_path": str(original_path),
                "source_kind": "upload",
                "custom_metadata": "preserve me",
                "content_hash": hashlib.sha256(
                    b"old original bytes"
                ).hexdigest(),
            },
            "other-source": {
                "display_name": "Other",
            },
        }
        self.state["embeddings"] = {
            "source-one_001": [1],
            "source-one_002": [2],
            "source-one-extra_001": [3],
            "other-source_001": [4],
        }
        self.state["concepts"] = {
            "shared": {
                "id": "shared-id",
                "canonical": "Shared",
                "occurrences": [
                    {"document": "source-one"},
                    {"document": "other-source"},
                ],
            },
            "source-only": {
                "id": "source-only-id",
                "canonical": "Source Only",
                "occurrences": [
                    {"document": "source-one"},
                ],
            },
        }

        return original_path

    def test_remove_source_embeddings_uses_exact_prefix(self):
        updated, removed_count = (
            library_management_service
            .remove_source_embeddings(
                "source-one",
                {
                    "source-one_001": [],
                    "source-one_002": [],
                    "source-one-extra_001": [],
                    "source-one": [],
                },
            )
        )

        self.assertEqual(removed_count, 2)
        self.assertEqual(
            set(updated),
            {
                "source-one-extra_001",
                "source-one",
            },
        )

    def test_concept_cleanup_preserves_shared_concepts(self):
        concepts = {
            "shared": {
                "canonical": "Shared",
                "extra": "preserved",
                "occurrences": [
                    {"document": "source-one"},
                    {"document": "other-source"},
                ],
            }
        }

        updated, occurrence_count, concept_count = (
            library_management_service
            .remove_source_concept_occurrences(
                "source-one",
                concepts,
            )
        )

        self.assertEqual(occurrence_count, 1)
        self.assertEqual(concept_count, 0)
        self.assertEqual(
            updated["shared"],
            {
                "canonical": "Shared",
                "extra": "preserved",
                "occurrences": [
                    {"document": "other-source"}
                ],
            },
        )

    def test_concept_cleanup_removes_unused_concepts(self):
        updated, occurrence_count, concept_count = (
            library_management_service
            .remove_source_concept_occurrences(
                "source-one",
                {
                    "unused": {
                        "occurrences": [
                            {"document": "source-one"}
                        ],
                    }
                },
            )
        )

        self.assertEqual(updated, {})
        self.assertEqual(occurrence_count, 1)
        self.assertEqual(concept_count, 1)

    def test_successful_reprocessing(self):
        original_path = self.set_reprocessable_source()

        def ingest(**kwargs):
            self.assertNotIn(
                "source-one_001",
                self.state["embeddings"],
            )
            self.assertNotIn(
                "source-only",
                self.state["concepts"],
            )
            self.assertEqual(
                self.state["concepts"]["shared"][
                    "occurrences"
                ],
                [{"document": "other-source"}],
            )
            kwargs["output_path"].write_text(
                "new knowledge",
                encoding="utf-8",
            )

            return [{"id": "new-1"}, {"id": "new-2"}]

        self.ingest_document.side_effect = ingest

        result = (
            library_management_service
            .reprocess_library_source("source-one")
        )

        self.ingest_document.assert_called_once_with(
            file_path=original_path,
            domain="Academics",
            output_path=self.knowledge_path,
            source_id="source-one",
        )
        metadata = self.state["sources"]["source-one"]
        expected_content_hash = hashlib.sha256(
            original_path.read_bytes()
        ).hexdigest()
        self.assertEqual(
            metadata["custom_metadata"],
            "preserve me",
        )
        self.assertEqual(
            metadata["content_hash"],
            expected_content_hash,
        )
        self.assertNotEqual(
            metadata["content_hash"],
            hashlib.sha256(
                b"old original bytes"
            ).hexdigest(),
        )
        self.assertEqual(
            metadata["reprocessed_at"],
            result["reprocessed_at"],
        )
        self.assertEqual(result["status"], "reprocessed")
        self.assertEqual(result["source_id"], "source-one")
        self.assertIn(
            "source-one",
            self.state["sources"],
        )
        self.assertEqual(
            result["knowledge_object_count"],
            2,
        )
        self.assertEqual(
            result["removed_embedding_count"],
            2,
        )
        self.assertEqual(
            result["removed_occurrence_count"],
            2,
        )
        self.assertEqual(
            result["removed_concept_count"],
            1,
        )

    def test_reprocessing_missing_source_raises(self):
        with self.assertRaisesRegex(
            KeyError,
            "Unknown library source: missing",
        ):
            (
                library_management_service
                .reprocess_library_source("missing")
            )

    def test_reprocessing_missing_original_raises(self):
        self.state["sources"] = {
            "source-one": {
                "original_path": str(
                    self.root / "missing.docx"
                )
            }
        }

        with self.assertRaisesRegex(
            FileNotFoundError,
            "Original file is unavailable",
        ):
            (
                library_management_service
                .reprocess_library_source("source-one")
            )

    def test_reprocessing_failure_restores_all_state(self):
        self.set_reprocessable_source()
        original_state = deepcopy(self.state)
        original_bytes = (
            self.knowledge_path.read_bytes()
        )
        failure = RuntimeError("ingestion failed")

        def fail_ingestion(**kwargs):
            kwargs["output_path"].write_bytes(
                b"partial replacement"
            )
            raise failure

        self.ingest_document.side_effect = fail_ingestion

        with self.assertRaises(RuntimeError) as caught:
            (
                library_management_service
                .reprocess_library_source("source-one")
            )

        self.assertIs(caught.exception, failure)
        self.assertEqual(self.state, original_state)
        self.assertEqual(
            self.knowledge_path.read_bytes(),
            original_bytes,
        )

    def test_reprocessing_removes_new_json_on_failure(self):
        original_path = self.set_reprocessable_source()
        self.knowledge_path.unlink()
        failure = RuntimeError("ingestion failed")

        def fail_ingestion(**kwargs):
            kwargs["output_path"].write_bytes(b"partial")
            raise failure

        self.ingest_document.side_effect = fail_ingestion

        with self.assertRaises(RuntimeError) as caught:
            (
                library_management_service
                .reprocess_library_source("source-one")
            )

        self.assertIs(caught.exception, failure)
        self.assertFalse(self.knowledge_path.exists())
        self.assertTrue(original_path.exists())

    def test_reprocessing_rollback_failure_is_chained(self):
        self.set_reprocessable_source()
        original_error = RuntimeError("ingestion failed")
        rollback_error = OSError("registry unavailable")
        self.ingest_document.side_effect = original_error
        self.save_sources.side_effect = rollback_error

        with self.assertRaisesRegex(
            RuntimeError,
            "rollback was incomplete.*source registry",
        ) as caught:
            (
                library_management_service
                .reprocess_library_source("source-one")
            )

        self.assertIs(caught.exception.__cause__, original_error)

    def test_repository_source_is_protected(self):
        self.state["sources"] = {
            "repository-source": {
                "source_kind": "repository",
            }
        }

        with self.assertRaisesRegex(
            PermissionError,
            "Repository sources are protected",
        ):
            (
                library_management_service
                .remove_library_source(
                    "repository-source"
                )
            )

    def test_uploaded_source_outside_root_is_rejected(self):
        self.state["sources"] = {
            "../outside": {
                "source_kind": "upload",
            }
        }

        with self.assertRaisesRegex(
            ValueError,
            "outside the configured uploads directory",
        ):
            (
                library_management_service
                .remove_library_source("../outside")
            )

    def test_uploaded_source_symlink_is_rejected(self):
        sibling_directory = (
            self.uploads_directory
            / "sibling-source"
        )
        sibling_directory.mkdir()
        source_path = (
            self.uploads_directory
            / "source-one"
        )
        source_path.symlink_to(
            sibling_directory,
            target_is_directory=True,
        )
        self.state["sources"] = {
            "source-one": {
                "source_kind": "upload",
            }
        }

        with self.assertRaisesRegex(
            ValueError,
            "cannot be a symbolic link",
        ):
            (
                library_management_service
                .remove_library_source("source-one")
            )

        self.assertTrue(source_path.is_symlink())
        self.assertTrue(sibling_directory.exists())

    def test_uploaded_source_regular_file_is_rejected(self):
        source_path = (
            self.uploads_directory
            / "source-one"
        )
        source_path.write_bytes(b"not a directory")
        self.state["sources"] = {
            "source-one": {
                "source_kind": "upload",
            }
        }

        with self.assertRaisesRegex(
            ValueError,
            "must be a directory",
        ):
            (
                library_management_service
                .remove_library_source("source-one")
            )

        self.assertEqual(
            source_path.read_bytes(),
            b"not a directory",
        )

    def test_successful_uploaded_source_removal(self):
        source_directory = (
            self.set_reprocessable_source().parent
        )
        removed_paths = []
        real_rmtree = (
            library_management_service.shutil.rmtree
        )

        def record_removal(path):
            removed_paths.append(path)
            real_rmtree(path)

        with patch.object(
            library_management_service.shutil,
            "rmtree",
            side_effect=record_removal,
        ):
            result = (
                library_management_service
                .remove_library_source("source-one")
            )

        self.assertFalse(source_directory.exists())
        self.assertEqual(len(removed_paths), 1)
        self.assertIn(
            ".source-one.",
            removed_paths[0].name,
        )
        self.assertNotIn(
            "source-one",
            self.state["sources"],
        )
        self.assertIn(
            "other-source",
            self.state["sources"],
        )
        self.assertNotIn(
            "source-one_001",
            self.state["embeddings"],
        )
        self.assertIn(
            "source-one-extra_001",
            self.state["embeddings"],
        )
        self.assertEqual(
            self.state["concepts"]["shared"][
                "occurrences"
            ],
            [{"document": "other-source"}],
        )
        self.assertNotIn(
            "source-only",
            self.state["concepts"],
        )
        self.assertEqual(result["status"], "removed")
        self.assertEqual(
            result["removed_embedding_count"],
            2,
        )
        self.assertEqual(
            result["removed_occurrence_count"],
            2,
        )
        self.assertEqual(
            result["removed_concept_count"],
            1,
        )
        self.assertIsNone(result["cleanup_warning"])

    def test_removal_save_failure_restores_everything(self):
        source_directory = (
            self.set_reprocessable_source().parent
        )
        original_state = deepcopy(self.state)
        save_calls = 0

        def fail_once(registry):
            nonlocal save_calls
            save_calls += 1

            if save_calls == 1:
                raise OSError("source save failed")

            self.save_source_registry(registry)

        self.save_sources.side_effect = fail_once

        with self.assertRaisesRegex(
            OSError,
            "source save failed",
        ):
            (
                library_management_service
                .remove_library_source("source-one")
            )

        self.assertEqual(self.state, original_state)
        self.assertTrue(source_directory.exists())
        self.assertTrue(
            (source_directory / "original.docx").exists()
        )

    def test_tombstone_cleanup_failure_is_nonfatal(self):
        source_directory = (
            self.set_reprocessable_source().parent
        )

        with patch.object(
            library_management_service.shutil,
            "rmtree",
            side_effect=OSError("cleanup denied"),
        ):
            result = (
                library_management_service
                .remove_library_source("source-one")
            )

        self.assertFalse(source_directory.exists())
        self.assertNotIn(
            "source-one",
            self.state["sources"],
        )
        self.assertIn(
            "cleanup denied",
            result["cleanup_warning"],
        )
        tombstones = list(
            self.uploads_directory.glob(
                ".source-one.*.tombstone"
            )
        )
        self.assertEqual(len(tombstones), 1)

    def test_library_entry_exposes_management_fields(self):
        original_path = self.create_original("upload-source")
        knowledge_path = (
            original_path.parent
            / "upload-source.json"
        )
        knowledge_path.write_text("[]", encoding="utf-8")

        with patch.object(
            library_service,
            "DOCUMENTS_DIRECTORY",
            self.root,
        ):
            entry = library_service.build_library_entry(
                "upload-source",
                {
                    "source_kind": "upload",
                    "original_path": str(original_path),
                    "reprocessed_at": "timestamp",
                },
                {},
            )

        self.assertEqual(entry["source_kind"], "upload")
        self.assertTrue(entry["can_remove"])
        self.assertTrue(entry["can_reprocess"])
        self.assertEqual(
            entry["reprocessed_at"],
            "timestamp",
        )

    def test_missing_source_kind_defaults_to_repository(self):
        entry = library_service.build_library_entry(
            "repository-source",
            {},
            {},
        )

        self.assertEqual(
            entry["source_kind"],
            "repository",
        )
        self.assertFalse(entry["can_remove"])
        self.assertFalse(entry["can_reprocess"])
        self.assertIsNone(entry["reprocessed_at"])


if __name__ == "__main__":
    unittest.main()
