"""Focused tests for the Mission 027 composition seams."""

import ast
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIRECTORY = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIRECTORY))

import products.atlas.document_ingestion as document_ingestion
import products.atlas.interface as interface
import wingman.core.knowledge_ingestion as knowledge_ingestion
import wingman.core.retrieval_engine as retrieval_engine
from products.atlas.product_config import ATLAS_PRODUCT
from wingman.shared.product_contract import (
    FRAMEWORK_SOURCE_METADATA_FIELDS,
    ProductConfiguration,
    SourceMetadataField,
)


PUBLIC_FRAMEWORK_METADATA_FIELDS = frozenset(
    {
        "can_remove",
        "can_reprocess",
        "concept_count",
        "content_hash",
        "display_name",
        "domain",
        "embedding_count",
        "file_name",
        "file_type",
        "id",
        "knowledge_object_count",
        "knowledge_path",
        "mime_type",
        "original_available",
        "original_path",
        "record_count",
        "reprocessed_at",
        "source_id",
        "source_kind",
        "source_url",
        "status",
        "uploaded_at",
    }
)


class AirframeCompositionTests(unittest.TestCase):
    @patch.object(
        knowledge_ingestion,
        "extract_document_units",
        return_value=[
            {
                "heading": "Heading",
                "text": "Generic body",
                "location": "Unit 1",
            }
        ],
    )
    def test_core_ingestion_has_no_product_enrichment(
        self,
        extractor,
    ):
        objects = knowledge_ingestion.create_knowledge_objects(
            "source.pdf",
            "Generic",
            source_id="source",
        )

        extractor.assert_called_once_with("source.pdf")
        self.assertEqual(objects[0]["concepts"], [])
        self.assertEqual(objects[0]["records"], [])

    @patch.object(
        knowledge_ingestion,
        "extract_document_units",
        return_value=[
            {
                "heading": None,
                "text": "Source text",
                "location": "Unit 1",
            }
        ],
    )
    def test_product_enrichment_is_injected(
        self,
        extractor,
    ):
        def enrich(item):
            return {
                **item,
                "records": [{"type": "product_record"}],
            }

        objects = knowledge_ingestion.create_knowledge_objects(
            "source.pdf",
            "Generic",
            source_id="source",
            enricher=enrich,
        )

        extractor.assert_called_once()
        self.assertEqual(
            objects[0]["records"],
            [{"type": "product_record"}],
        )

    def test_core_retrieval_executes_supplied_plan(self):
        deterministic = Mock(
            return_value=[
                {
                    "heading": "Evidence",
                    "section": None,
                    "text": "Source truth",
                }
            ]
        )
        ranker = Mock(
            side_effect=lambda evidence, terms: evidence
        )
        semantic = Mock(return_value=[])
        concepts = Mock(return_value=[])
        plan = {
            "text_search_terms": [],
            "record_types": ["product_record"],
            "record_filters": [],
            "memory_search_terms": [],
        }

        result = retrieval_engine.retrieve_evidence_for_plan(
            "Question",
            plan,
            deterministic_retriever=deterministic,
            evidence_ranker=ranker,
            semantic_retriever=semantic,
            concept_retriever=concepts,
        )

        deterministic.assert_called_once_with(plan)
        semantic.assert_not_called()
        concepts.assert_not_called()
        self.assertEqual(result[0]["text"], "Source truth")

    def test_configuration_keeps_internal_and_visible_names_separate(
        self,
    ):
        self.assertEqual(ATLAS_PRODUCT.product_key, "atlas")
        self.assertEqual(
            ATLAS_PRODUCT.product_name,
            "Academic Wingman",
        )
        self.assertEqual(ATLAS_PRODUCT.call_sign, "Atlas")

    def test_product_configuration_rejects_duplicate_fields(self):
        duplicate_fields = (
            SourceMetadataField("field", "First"),
            SourceMetadataField("field", "Second"),
        )
        with self.assertRaisesRegex(
            ValueError,
            "must be unique",
        ):
            ProductConfiguration(
                product_key="product",
                product_name="Product",
                call_sign="Call Sign",
                page_title="Product | Wingman",
                page_icon="",
                default_domain="General",
                source_metadata_fields=duplicate_fields,
            )

    def test_only_real_public_metadata_collisions_are_reserved(
        self,
    ):
        self.assertEqual(
            FRAMEWORK_SOURCE_METADATA_FIELDS,
            PUBLIC_FRAMEWORK_METADATA_FIELDS,
        )
        for key in PUBLIC_FRAMEWORK_METADATA_FIELDS:
            with self.subTest(key=key):
                with self.assertRaisesRegex(
                    ValueError,
                    "framework-owned",
                ):
                    SourceMetadataField(key, "Unsafe")

        for internal_key in (
            "change_type",
            "entity_id",
            "version_number",
        ):
            SourceMetadataField(
                internal_key,
                "Product field",
            )

    def test_product_metadata_keys_use_lower_snake_case(self):
        for key in (
            "",
            "_private",
            "Academic Year",
            "academic-year",
            42,
        ):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    SourceMetadataField(key, "Invalid")

    def test_document_ingestion_facade_is_explicit(self):
        self.assertEqual(
            set(document_ingestion.__all__),
            {
                "create_knowledge_objects",
                "extract_document_units",
                "index_knowledge_objects",
                "ingest_document",
                "resolve_section",
                "save_knowledge_objects",
            },
        )
        for name in document_ingestion.__all__:
            self.assertTrue(
                callable(getattr(document_ingestion, name))
            )

    def test_facade_helpers_remain_patchable(self):
        units = [
            {
                "heading": None,
                "text": "Compatibility body",
                "location": "Unit 1",
            }
        ]
        with (
            patch.object(
                document_ingestion,
                "extract_document_units",
                return_value=units,
            ) as extractor,
            patch.object(
                document_ingestion,
                "resolve_section",
                return_value="Compatibility",
            ) as resolver,
            patch.object(
                document_ingestion,
                "enrich_concepts",
                side_effect=lambda item: item,
            ),
        ):
            objects = (
                document_ingestion.create_knowledge_objects(
                    "source.pdf",
                    "Generic",
                    source_id="source",
                )
            )

        extractor.assert_called_once_with("source.pdf")
        resolver.assert_called_once()
        self.assertEqual(
            objects[0]["section"],
            "Compatibility",
        )

    def test_facade_pipeline_callback_contract(self):
        objects = [{"id": "compatibility-object"}]
        with (
            patch.object(
                document_ingestion,
                "create_knowledge_objects",
                return_value=objects,
            ) as creator,
            patch.object(
                document_ingestion,
                "save_knowledge_objects",
            ) as saver,
            patch.object(
                document_ingestion,
                "index_knowledge_objects",
            ) as indexer,
        ):
            result = document_ingestion.ingest_document(
                "source.pdf",
                "Generic",
                output_path="objects.json",
                source_id="source",
            )

        creator.assert_called_once()
        self.assertEqual(
            creator.call_args.kwargs["enricher"],
            document_ingestion.enrich_concepts,
        )
        saver.assert_called_once_with(
            objects,
            "objects.json",
        )
        indexer.assert_called_once_with(objects)
        self.assertIs(result, objects)

    def test_streamlit_routes_multi_selection_through_batch_preview(self):
        source_text = (SRC_DIRECTORY / "products" / "atlas" / "streamlit_app.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source_text)
        preview_calls = [
            node
            for node in ast.walk(tree)
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id
                == "preview_batch"
            )
        ]
        self.assertEqual(len(preview_calls), 1)
        values = [
            keyword.value
            for keyword in preview_calls[0].keywords
            if keyword.arg == "product_metadata"
        ]
        self.assertEqual(len(values), 1)
        self.assertEqual(values[0].id, "product_metadata")

        uploader_calls = [
            node
            for node in ast.walk(tree)
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "file_uploader"
            )
        ]
        document_uploader = next(
            call
            for call in uploader_calls
            if isinstance(call.args[0], ast.Constant)
            and call.args[0].value == "Upload documents"
        )
        keywords = {
            keyword.arg: keyword.value
            for keyword in document_uploader.keywords
        }
        self.assertIs(keywords["accept_multiple_files"].value, True)
        self.assertEqual(
            {element.value for element in keywords["type"].elts},
            {
                "pptx",
                "pdf",
                "docx",
                "xlsx",
                "csv",
                "txt",
                "md",
                "markdown",
            },
        )
        self.assertIn("default_course_id.strip()", source_text)
        self.assertIn("course_overrides.items()", source_text)
        self.assertLess(
            source_text.index("reset_assignment_confirmation_if_changed("),
            source_text.index("assignments_confirmed = st.checkbox"),
        )
        confirmation_calls = [
            node
            for node in ast.walk(tree)
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "checkbox"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and "confirm the course assignment" in node.args[0].value
            )
        ]
        self.assertEqual(len(confirmation_calls), 1)
        confirmation_keywords = {
            keyword.arg: keyword.value
            for keyword in confirmation_calls[0].keywords
        }
        self.assertEqual(
            confirmation_keywords["key"].value,
            "batch_assignments_confirmed",
        )

    def test_terminal_defaults_and_configuration_match(self):
        default_output = io.StringIO()
        configured_output = io.StringIO()
        with redirect_stdout(default_output):
            interface.show_header()
        with redirect_stdout(configured_output):
            interface.show_header(ATLAS_PRODUCT)

        self.assertEqual(
            default_output.getvalue(),
            configured_output.getvalue(),
        )
        self.assertIn(
            "Welcome aboard, Maverick.",
            configured_output.getvalue(),
        )


if __name__ == "__main__":
    unittest.main()
