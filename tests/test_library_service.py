# Tests Atlas Library inventory behavior in isolation.

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIRECTORY = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIRECTORY))

import library_service


class LibraryServiceTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )
        self.addCleanup(
            self.temporary_directory.cleanup
        )
        self.documents_directory = (
            Path(self.temporary_directory.name)
            / "documents"
        )
        self.documents_directory.mkdir()
        self.documents_patch = patch.object(
            library_service,
            "DOCUMENTS_DIRECTORY",
            self.documents_directory,
        )
        self.documents_patch.start()
        self.addCleanup(self.documents_patch.stop)

    def write_json(self, path, value):
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        path.write_text(
            json.dumps(value),
            encoding="utf-8",
        )

    def test_find_knowledge_path_prefers_source_id_json(self):
        source_directory = (
            self.documents_directory
            / "source-one"
        )
        original_path = (
            source_directory
            / "original.docx"
        )
        preferred_path = (
            source_directory
            / "source-one.json"
        )
        fallback_path = (
            source_directory
            / "original.json"
        )
        self.write_json(preferred_path, [])
        self.write_json(fallback_path, [])

        self.assertEqual(
            library_service.find_knowledge_path(
                "source-one",
                original_path,
            ),
            preferred_path,
        )

    def test_find_knowledge_path_supports_stem_fallback(self):
        source_directory = (
            self.documents_directory
            / "source-one"
        )
        original_path = (
            source_directory
            / "original.docx"
        )
        fallback_path = (
            source_directory
            / "original.json"
        )
        self.write_json(fallback_path, [])

        self.assertEqual(
            library_service.find_knowledge_path(
                "source-one",
                original_path,
            ),
            fallback_path,
        )

    def test_find_knowledge_path_searches_recursively(self):
        recursive_path = (
            self.documents_directory
            / "nested"
            / "source-one.json"
        )
        self.write_json(recursive_path, [])

        self.assertEqual(
            library_service.find_knowledge_path(
                "source-one"
            ),
            recursive_path,
        )

    def test_find_knowledge_path_returns_none(self):
        self.assertIsNone(
            library_service.find_knowledge_path(
                "missing-source"
            )
        )

    def test_load_source_knowledge_behaviors(self):
        self.assertEqual(
            library_service.load_source_knowledge(None),
            [],
        )

        valid_path = (
            self.documents_directory
            / "valid.json"
        )
        knowledge_objects = [{"id": "source-one_1"}]
        self.write_json(valid_path, knowledge_objects)
        self.assertEqual(
            library_service.load_source_knowledge(
                valid_path
            ),
            knowledge_objects,
        )

        invalid_path = (
            self.documents_directory
            / "invalid.json"
        )
        self.write_json(invalid_path, {"id": "not-a-list"})

        with self.assertRaisesRegex(
            ValueError,
            "must contain a JSON list",
        ):
            library_service.load_source_knowledge(
                invalid_path
            )

    def test_count_source_embeddings_uses_exact_prefix(self):
        embeddings = {
            "source-one_1": [],
            "source-one_2": [],
            "source-one-extra_1": [],
            "source-on_1": [],
            "source-one": [],
        }

        self.assertEqual(
            library_service.count_source_embeddings(
                "source-one",
                embeddings,
            ),
            2,
        )

    def test_determine_source_status_states(self):
        cases = [
            (
                (False, 0, 0),
                "Original unavailable",
            ),
            (
                (True, 0, 0),
                "Needs processing",
            ),
            (
                (True, 3, 2),
                "Partially indexed",
            ),
            (
                (True, 3, 3),
                "Ready",
            ),
            (
                (True, 3, 4),
                "Ready",
            ),
        ]

        for arguments, expected_status in cases:
            with self.subTest(status=expected_status):
                self.assertEqual(
                    library_service.determine_source_status(
                        *arguments
                    ),
                    expected_status,
                )

    def test_build_library_entry_reports_counts_and_metadata(
        self,
    ):
        source_id = "source-one"
        source_directory = (
            self.documents_directory
            / source_id
        )
        original_path = (
            source_directory
            / "original.docx"
        )
        original_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        original_path.write_bytes(b"original")
        knowledge_path = (
            source_directory
            / f"{source_id}.json"
        )
        self.write_json(
            knowledge_path,
            [
                {
                    "records": [{}, {}],
                    "concepts": [
                        {"id": "concept-1"},
                        {"canonical": "Concept Two"},
                        "Concept Three",
                    ],
                },
                {
                    "records": [{}],
                    "concepts": [
                        {"id": "concept-1"},
                        {"name": "Concept Four"},
                        "Concept Three",
                    ],
                },
            ],
        )
        metadata = {
            "display_name": "Source One",
            "file_name": "original.docx",
            "file_type": "docx",
            "domain": "Academics",
            "program": "MSAIB",
            "academic_year": "2026-2027",
            "uploaded_at": "2026-07-27T12:00:00+00:00",
            "source_url": None,
            "original_path": str(original_path),
        }
        embeddings = {
            "source-one_1": [],
            "source-one_2": [],
            "source-one-other_1": [],
        }

        entry = library_service.build_library_entry(
            source_id,
            metadata,
            embeddings,
        )

        self.assertEqual(entry["source_id"], source_id)
        for key, value in metadata.items():
            self.assertEqual(entry[key], value)
        self.assertTrue(entry["original_available"])
        self.assertEqual(
            entry["knowledge_path"],
            str(knowledge_path),
        )
        self.assertEqual(
            entry["knowledge_object_count"],
            2,
        )
        self.assertEqual(entry["record_count"], 3)
        self.assertEqual(entry["concept_count"], 4)
        self.assertEqual(entry["embedding_count"], 2)
        self.assertEqual(entry["status"], "Ready")

    @patch.object(library_service, "load_embeddings")
    @patch.object(
        library_service,
        "load_source_registry",
    )
    def test_list_library_sources_combines_and_sorts(
        self,
        load_registry,
        load_embeddings,
    ):
        alpha_path = (
            self.documents_directory
            / "alpha.docx"
        )
        zebra_path = (
            self.documents_directory
            / "zebra.docx"
        )
        alpha_path.write_bytes(b"alpha")
        zebra_path.write_bytes(b"zebra")
        self.write_json(
            alpha_path.parent / "alpha-source.json",
            [{"id": "alpha-source_1"}],
        )
        self.write_json(
            zebra_path.parent / "zebra-source.json",
            [{"id": "zebra-source_1"}],
        )
        load_registry.return_value = {
            "zebra-source": {
                "display_name": "zebra",
                "original_path": str(zebra_path),
            },
            "alpha-source": {
                "display_name": "Alpha",
                "original_path": str(alpha_path),
            },
        }
        load_embeddings.return_value = {
            "alpha-source_1": [],
            "zebra-source_1": [],
        }

        entries = library_service.list_library_sources()

        self.assertEqual(
            [
                entry["source_id"]
                for entry in entries
            ],
            ["alpha-source", "zebra-source"],
        )
        self.assertEqual(
            [entry["embedding_count"] for entry in entries],
            [1, 1],
        )

    @patch.object(
        library_service,
        "load_embeddings",
        return_value={},
    )
    @patch.object(
        library_service,
        "load_source_registry",
        return_value={},
    )
    def test_list_library_sources_handles_empty_registry(
        self,
        load_registry,
        load_embeddings,
    ):
        self.assertEqual(
            library_service.list_library_sources(),
            [],
        )

    def test_missing_optional_metadata_uses_fallbacks(self):
        entry = library_service.build_library_entry(
            "minimal-source",
            {},
            {},
        )

        self.assertEqual(
            entry["display_name"],
            "minimal-source",
        )
        self.assertIsNone(entry["file_name"])
        self.assertIsNone(entry["file_type"])
        self.assertIsNone(entry["domain"])
        self.assertIsNone(entry["original_path"])
        self.assertFalse(entry["original_available"])
        self.assertEqual(
            entry["status"],
            "Original unavailable",
        )


if __name__ == "__main__":
    unittest.main()
