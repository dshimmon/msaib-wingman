"""Failure-isolation coverage for every mutable single-file stage."""

import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import concept_registry_storage  # noqa: E402
import document_ingestion  # noqa: E402
import embedding_storage  # noqa: E402
import intake_service  # noqa: E402


class IngestionAtomicityTests(unittest.TestCase):
    def test_extraction_enrichment_save_and_index_failures_leave_no_artifacts(self):
        scenarios = (
            ("extracting", "extract_document_units"),
            ("extracting", "enrich_concepts"),
            ("saving", "save_knowledge_objects"),
            ("indexing", "index_knowledge_objects"),
        )
        for expected_stage, failing_name in scenarios:
            with self.subTest(stage=failing_name):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    uploads = root / "uploads"
                    patches = [
                        patch.object(intake_service, "UPLOADS_DIRECTORY", uploads),
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
                        patch.object(
                            intake_service,
                            "find_source_by_content_hash",
                            return_value=(None, None),
                        ),
                        patch.object(intake_service, "register_source"),
                        patch.object(
                            document_ingestion,
                            "enrich_concepts",
                            side_effect=lambda item: item,
                        ),
                    ]
                    with ExitStack() as stack:
                        started = [stack.enter_context(value) for value in patches]
                        failure = RuntimeError(f"{failing_name} failed")
                        stack.enter_context(
                            patch.object(
                                document_ingestion,
                                failing_name,
                                side_effect=failure,
                            )
                        )
                        with self.assertRaises(RuntimeError) as caught:
                            intake_service.ingest_uploaded_document(
                                "source.txt",
                                b"Source evidence",
                                atomic=True,
                            )
                        self.assertIs(caught.exception, failure)
                        self.assertTrue(caught.exception.cleanup_verified)
                        self.assertEqual(caught.exception.failure_stage, expected_stage)
                        self.assertEqual(list(uploads.iterdir()), [])
                        self.assertFalse(embedding_storage.EMBEDDINGS_PATH.exists())
                        self.assertFalse(concept_registry_storage.REGISTRY_PATH.exists())
                        started[4].assert_not_called()


if __name__ == "__main__":
    unittest.main()
