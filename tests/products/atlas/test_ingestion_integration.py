"""Disposable integration tests for the real ingestion compatibility path."""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from openpyxl import Workbook


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIRECTORY = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIRECTORY))

import wingman.core.concept_registry_storage as concept_registry_storage
import products.atlas.document_ingestion as document_ingestion
import wingman.core.embedding_indexer as embedding_indexer
import wingman.core.embedding_storage as embedding_storage
import products.atlas.intake_service as intake_service
import products.atlas.library_management_service as library_management_service
import wingman.shared.source_registry as source_registry
from wingman.core.ledger.database import connect_database
from wingman.core.ledger.migrations import apply_migrations


class RealIngestionCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.database_path = self.root / "ledger.sqlite3"
        self.uploads_path = self.root / "uploads"
        self.concepts_path = self.root / "concepts.json"
        self.embeddings_path = self.root / "embeddings.json"
        self.enterContext(
            patch.dict(
                os.environ,
                {
                    "WINGMAN_LEDGER_PATH": str(
                        self.database_path
                    ),
                    "OPENAI_API_KEY": "",
                },
                clear=False,
            )
        )
        self.enterContext(
            patch.object(
                intake_service,
                "UPLOADS_DIRECTORY",
                self.uploads_path,
            )
        )
        self.enterContext(
            patch.object(
                library_management_service,
                "UPLOADS_DIRECTORY",
                self.uploads_path,
            )
        )
        self.enterContext(
            patch.object(
                concept_registry_storage,
                "REGISTRY_PATH",
                self.concepts_path,
            )
        )
        self.enterContext(
            patch.object(
                embedding_storage,
                "EMBEDDINGS_PATH",
                self.embeddings_path,
            )
        )
        self.enterContext(
            patch.object(
                source_registry,
                "SOURCE_REGISTRY_PATH",
                self.root / "missing-legacy.json",
            )
        )
        self.enterContext(
            patch.object(
                embedding_indexer,
                "create_embedding",
                side_effect=lambda text: [
                    float(len(text))
                ],
            )
        )
        connection = connect_database(
            self.database_path
        )
        self.assertEqual(
            apply_migrations(connection),
            {1, 2, 3},
        )
        connection.close()

    def workbook_bytes(self, body):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Overview"
        sheet.append(["Topic", "Description"])
        sheet.append(["Boundary", body])
        buffer = io.BytesIO()
        workbook.save(buffer)
        workbook.close()
        return buffer.getvalue()

    def test_upload_and_reprocessing_use_real_compatibility_wrapper(
        self,
    ):
        nested_product_metadata = {
            "tracks": ["core", "elective"],
            "policy": {
                "enabled": True,
                "thresholds": [1, 2],
            },
        }
        result = intake_service.ingest_uploaded_document(
            "airframe.xlsx",
            self.workbook_bytes("Initial content"),
            domain="General",
            program="Program A",
            academic_year="Year 1",
            product_metadata={
                "product_details": nested_product_metadata,
            },
        )
        source_id = result["source_id"]
        source_directory = (
            self.uploads_path / source_id
        )
        original_path = (
            source_directory / "airframe.xlsx"
        )
        knowledge_path = (
            source_directory / f"{source_id}.json"
        )

        self.assertEqual(result["status"], "ingested")
        first_objects = json.loads(
            knowledge_path.read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(len(first_objects), 1)
        self.assertIn(
            "Initial content",
            first_objects[0]["text"],
        )
        self.assertEqual(
            set(
                json.loads(
                    self.embeddings_path.read_text(
                        encoding="utf-8"
                    )
                )
            ),
            {first_objects[0]["id"]},
        )
        initial_metadata = (
            source_registry.load_source_registry()[
                source_id
            ]
        )
        self.assertEqual(
            initial_metadata["original_path"],
            str(original_path),
        )
        self.assertEqual(
            {
                key: initial_metadata[key]
                for key in (
                    "program",
                    "academic_year",
                    "product_details",
                )
            },
            {
                "program": "Program A",
                "academic_year": "Year 1",
                "product_details": nested_product_metadata,
            },
        )

        original_path.write_bytes(
            self.workbook_bytes("Reprocessed content")
        )
        reprocessed = (
            library_management_service
            .reprocess_library_source(source_id)
        )
        second_objects = json.loads(
            knowledge_path.read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            reprocessed["status"],
            "reprocessed",
        )
        self.assertIn(
            "Reprocessed content",
            second_objects[0]["text"],
        )
        self.assertNotEqual(
            first_objects[0]["text"],
            second_objects[0]["text"],
        )
        reprocessed_metadata = (
            source_registry.load_source_registry()[
                source_id
            ]
        )
        self.assertEqual(
            {
                key: reprocessed_metadata[key]
                for key in (
                    "program",
                    "academic_year",
                    "product_details",
                )
            },
            {
                "program": "Program A",
                "academic_year": "Year 1",
                "product_details": nested_product_metadata,
            },
        )

    def test_cli_uses_real_wrapper_and_callback_contract(self):
        source_path = self.root / "cli-source.xlsx"
        output_path = self.root / "cli-output.json"
        source_path.write_bytes(
            self.workbook_bytes("CLI content")
        )
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = document_ingestion.main(
                [
                    str(source_path),
                    "--domain",
                    "General",
                    "--output-path",
                    str(output_path),
                    "--source-id",
                    "cli-source",
                    "--skip-index",
                ]
            )

        objects = json.loads(
            output_path.read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(exit_code, 0)
        self.assertEqual(objects[0]["document"], "cli-source")
        self.assertIn("CLI content", objects[0]["text"])
        self.assertIn("Saved 1 chunks.", output.getvalue())
        self.assertFalse(self.embeddings_path.exists())


if __name__ == "__main__":
    unittest.main()
