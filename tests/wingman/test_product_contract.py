"""Focused Mission 028 Product Contract, registry, and isolation tests."""

import ast
import io
import json
import sys
import tempfile
import unittest
from dataclasses import FrozenInstanceError, replace
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIRECTORY = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIRECTORY))

import wingman.core.concept_registry_storage as concept_registry_storage
import products.atlas.library_management_service as library_management_service
from products.atlas.product_config import (
    ATLAS_PRODUCT,
    PRODUCTION_PRODUCT_REGISTRY,
    create_atlas_context,
    create_product_context,
    normalize_course_id,
)
from wingman.shared.product_contract import (
    PRODUCT_CONTRACT_VERSION,
    BriefingComposition,
    ProductCapability,
    ProductConfiguration,
    ProductContract,
    ProductContext,
    ProductRegistry,
    RecordComposition,
    RecordDeclaration,
    RetrievalComposition,
    SourceMetadataField,
)
from wingman.shared.product_runtime import (
    create_product_knowledge_objects,
    normalize_source_metadata,
    retrieve_product_evidence,
    validate_product_records,
)
from wingman.core.knowledge_ingestion import save_knowledge_objects
import products.atlas.intake_service as intake_service
from products.atlas.batch_ingestion import browser_file_input, preview_batch
import products.atlas.main as main


def normalize_observation_kind(value):
    if isinstance(value, str):
        return value.strip().upper()
    return value


def enrich_field_note(knowledge_object):
    knowledge_object["records"] = [
        {
            "type": "field_note",
            "title": knowledge_object.get("heading"),
            "body": knowledge_object.get("text"),
        }
    ]
    return knowledge_object


def interpret_field_note_query(
    question,
    conversation_context=None,
):
    del conversation_context
    return {
        "memory_search_terms": [],
        "text_search_terms": [question],
        "record_types": ["field_note"],
        "record_filters": [],
    }


TEST_PRODUCT = ProductContract(
    contract_version=PRODUCT_CONTRACT_VERSION,
    product_key="field-notes",
    product_name="Field Notes Companion",
    call_sign="Beacon",
    page_title="Field Notes | Wingman",
    page_icon="📝",
    default_domain="Observations",
    terminal_title="FIELD NOTES",
    terminal_welcome="Ready to review observations.",
    chat_label="Discuss",
    library_label="Archive",
    briefing_label="Digest",
    capabilities=frozenset(
        {
            ProductCapability.SOURCE_INGESTION,
            ProductCapability.EVIDENCE_RETRIEVAL,
        }
    ),
    records=RecordComposition(
        declarations=(
            RecordDeclaration(
                record_type="field_note",
                fields=("title", "body"),
            ),
        ),
        enrich_knowledge=enrich_field_note,
    ),
    source_metadata_fields=(
        SourceMetadataField(
            key="observation_kind",
            label="Observation kind",
            placeholder="Optional",
            normalizer=normalize_observation_kind,
        ),
    ),
    retrieval=RetrievalComposition(
        interpret_query=interpret_field_note_query,
    ),
)


class ProductContractTests(unittest.TestCase):
    def test_atlas_course_id_is_small_explicit_and_validated(self):
        self.assertEqual(normalize_course_id("  AI-101 / A  "), "AI-101 / A")
        self.assertIsNone(normalize_course_id("   "))
        for value in (42, "#unsafe", "x" * 121):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalize_course_id(value)

    def test_atlas_exercises_every_contract_area(self):
        self.assertEqual(
            ATLAS_PRODUCT.contract_version,
            PRODUCT_CONTRACT_VERSION,
        )
        self.assertEqual(ATLAS_PRODUCT.product_id, "atlas")
        self.assertEqual(
            ATLAS_PRODUCT.display_name,
            "Academic Wingman",
        )
        self.assertNotEqual(
            ATLAS_PRODUCT.product_id,
            ATLAS_PRODUCT.display_name,
        )
        self.assertEqual(
            ATLAS_PRODUCT.capabilities,
            frozenset(ProductCapability),
        )
        self.assertEqual(
            {
                declaration.record_type
                for declaration in (
                    ATLAS_PRODUCT.records.declarations
                )
            },
            {"curriculum_course", "course_schedule"},
        )
        self.assertEqual(
            {
                field.key
                for field in (
                    ATLAS_PRODUCT.source_metadata_fields
                )
            },
            {"course_id", "program", "academic_year"},
        )
        self.assertTrue(
            callable(
                ATLAS_PRODUCT.records.enrich_knowledge
            )
        )
        self.assertTrue(
            callable(
                ATLAS_PRODUCT.retrieval.interpret_query
            )
        )
        self.assertIsInstance(
            ATLAS_PRODUCT.briefing,
            BriefingComposition,
        )
        self.assertEqual(
            (
                ATLAS_PRODUCT.chat_label,
                ATLAS_PRODUCT.briefing_label,
                ATLAS_PRODUCT.library_label,
            ),
            ("Chat", "Briefing", "Library"),
        )
        self.assertEqual(
            ATLAS_PRODUCT.default_domain,
            "General",
        )

    def test_registry_is_deterministic_and_rejects_duplicates(self):
        registry = ProductRegistry(
            (TEST_PRODUCT, ATLAS_PRODUCT)
        )
        self.assertEqual(
            registry.product_ids,
            ("atlas", "field-notes"),
        )
        with self.assertRaisesRegex(
            AttributeError,
            "immutable",
        ):
            registry._product_ids = ()
        with self.assertRaisesRegex(
            ValueError,
            "Duplicate product ID",
        ):
            ProductRegistry(
                (ATLAS_PRODUCT, ATLAS_PRODUCT)
            )

    def test_unknown_product_fails_before_context_creation(self):
        with self.assertRaisesRegex(
            KeyError,
            "Unknown product",
        ):
            ProductRegistry(
                (ATLAS_PRODUCT,)
            ).create_context("missing")

    def test_incomplete_product_fails_early(self):
        with self.assertRaisesRegex(
            ValueError,
            "record declarations",
        ):
            replace(TEST_PRODUCT, records=None)
        with self.assertRaisesRegex(
            ValueError,
            "briefing composition",
        ):
            replace(
                TEST_PRODUCT,
                capabilities=(
                    TEST_PRODUCT.capabilities
                    | {ProductCapability.BRIEFING}
                ),
            )

    def test_library_only_product_fails_before_reprocessing_state_access(
        self,
    ):
        library_only_product = replace(
            TEST_PRODUCT,
            product_key="library-only",
            capabilities=frozenset(
                {ProductCapability.SOURCE_LIBRARY}
            ),
        )
        with (
            patch.object(
                library_management_service,
                "load_source_registry",
            ) as load_sources,
            patch.object(
                library_management_service,
                "load_embeddings",
            ) as load_embeddings,
            patch.object(
                library_management_service,
                "load_registry",
            ) as load_concepts,
            patch.object(
                library_management_service,
                "find_knowledge_path",
            ) as find_knowledge,
            patch.object(
                library_management_service,
                "save_source_registry",
            ) as save_sources,
            patch.object(
                library_management_service,
                "save_embeddings",
            ) as save_embeddings,
            patch.object(
                library_management_service,
                "save_registry",
            ) as save_concepts,
            patch.object(
                library_management_service,
                "ingest_document",
            ) as ingest_document,
            patch.object(
                library_management_service,
                "rollback_reprocessing",
            ) as rollback,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "source_ingestion",
            ):
                (
                    library_management_service
                    .reprocess_library_source(
                        "source-one",
                        product_context=ProductContext(
                            library_only_product
                        ),
                    )
                )

        for persistent_operation in (
            load_sources,
            load_embeddings,
            load_concepts,
            find_knowledge,
            save_sources,
            save_embeddings,
            save_concepts,
            ingest_document,
            rollback,
        ):
            persistent_operation.assert_not_called()

    def test_historical_product_configuration_converts_explicitly(self):
        legacy = ProductConfiguration(
            product_key="field-notes",
            product_name="Field Notes Companion",
            call_sign="Beacon",
            page_title="Field Notes | Wingman",
            page_icon="📝",
            default_domain="Observations",
            source_metadata_fields=(
                SourceMetadataField(
                    "observation_kind",
                    "Observation kind",
                ),
            ),
        )

        self.assertEqual(legacy.terminal_title, "WINGMAN")
        self.assertEqual(legacy.terminal_welcome, "Welcome.")
        self.assertNotIsInstance(legacy, ProductContract)
        with self.assertRaisesRegex(
            TypeError,
            "validated Product Contract",
        ):
            ProductContext(legacy)
        with self.assertRaisesRegex(
            TypeError,
            "Product registration requires Product Contract",
        ):
            ProductRegistry((legacy,))
        with self.assertRaises(TypeError):
            legacy.to_product_contract()

        completion = {
            "capabilities": TEST_PRODUCT.capabilities,
            "records": TEST_PRODUCT.records,
            "retrieval": TEST_PRODUCT.retrieval,
            "chat_label": "Discuss",
            "library_label": "Archive",
            "briefing_label": "Digest",
        }
        contract = legacy.to_product_contract(
            contract_version=PRODUCT_CONTRACT_VERSION,
            **completion,
        )

        self.assertIsInstance(contract, ProductContract)
        self.assertEqual(contract.product_id, legacy.product_key)
        self.assertEqual(
            contract.source_metadata_fields,
            legacy.source_metadata_fields,
        )
        self.assertIs(
            ProductContext(contract).product,
            contract,
        )
        with self.assertRaisesRegex(
            ValueError,
            "Incompatible Product Contract version",
        ):
            legacy.to_product_contract(
                contract_version=2,
                **completion,
            )

    def test_incompatible_contract_version_fails_early(self):
        for version in (2, True, "1"):
            with self.subTest(version=version):
                with self.assertRaisesRegex(
                    ValueError,
                    "Incompatible Product Contract version",
                ):
                    replace(
                        TEST_PRODUCT,
                        contract_version=version,
                    )

    def test_reserved_metadata_collision_fails_early(self):
        with self.assertRaisesRegex(
            ValueError,
            "framework-owned",
        ):
            SourceMetadataField(
                "source_id",
                "Unsafe",
            )

    def test_context_and_nested_contract_values_are_immutable(self):
        context = ProductContext(TEST_PRODUCT)
        with self.assertRaises(FrozenInstanceError):
            context.product = ATLAS_PRODUCT
        with self.assertRaises(FrozenInstanceError):
            context.product.default_domain = "Changed"
        with self.assertRaises(AttributeError):
            context.product.capabilities.add(
                ProductCapability.BRIEFING
            )

    def test_sequential_contexts_do_not_leak_product_state(self):
        registry = ProductRegistry(
            (ATLAS_PRODUCT, TEST_PRODUCT)
        )
        atlas_context = registry.create_context("atlas")
        test_context = registry.create_context("field-notes")

        self.assertEqual(
            atlas_context.product.default_domain,
            "General",
        )
        self.assertEqual(
            test_context.product.default_domain,
            "Observations",
        )
        self.assertEqual(
            atlas_context.product.call_sign,
            "Atlas",
        )
        self.assertEqual(
            test_context.product.call_sign,
            "Beacon",
        )
        self.assertNotEqual(
            atlas_context.product.records.declarations,
            test_context.product.records.declarations,
        )
        self.assertNotEqual(
            atlas_context.product.source_metadata_fields,
            test_context.product.source_metadata_fields,
        )
        self.assertTrue(
            atlas_context.product.supports(
                ProductCapability.BRIEFING
            )
        )
        self.assertFalse(
            test_context.product.supports(
                ProductCapability.BRIEFING
            )
        )
        with self.assertRaisesRegex(
            ValueError,
            "does not declare capability",
        ):
            test_context.require(
                ProductCapability.BRIEFING
            )

    def test_metadata_rules_remain_scoped_and_opaque_values_survive(self):
        atlas_context = create_atlas_context()
        test_context = ProductContext(TEST_PRODUCT)
        nested = {
            "values": [1, None],
            "rule": {"enabled": True},
        }
        self.assertEqual(
            normalize_source_metadata(
                atlas_context,
                {
                    "program": "  Cohort  ",
                    "opaque_details": nested,
                },
            ),
            {
                "program": "Cohort",
                "opaque_details": nested,
            },
        )
        self.assertEqual(
            normalize_source_metadata(
                test_context,
                {
                    "observation_kind": "  field  ",
                    "program": "  untouched  ",
                },
            ),
            {
                "observation_kind": "FIELD",
                "program": "  untouched  ",
            },
        )
        self.assertEqual(
            normalize_source_metadata(
                atlas_context,
                {"observation_kind": "  field  "},
            )["observation_kind"],
            "  field  ",
        )
        self.assertIsNone(
            normalize_source_metadata(
                atlas_context,
                {"academic_year": None},
            )["academic_year"]
        )

    def test_explicit_non_atlas_intake_preserves_opaque_metadata(self):
        context = ProductContext(TEST_PRODUCT)
        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.object(
                    intake_service,
                    "UPLOADS_DIRECTORY",
                    Path(directory) / "uploads",
                ),
                patch.object(
                    intake_service,
                    "find_source_by_content_hash",
                    return_value=(None, None),
                ),
                patch.object(
                    intake_service,
                    "ingest_document",
                    return_value=[{"id": "knowledge-1"}],
                ) as ingest_document,
                patch.object(
                    intake_service,
                    "register_source",
                ) as register_source,
            ):
                intake_service.ingest_uploaded_document(
                    "field-note.docx",
                    b"field note",
                    product_metadata={
                        "observation_kind": "  field  ",
                        "opaque_details": "  keep exact  ",
                    },
                    product_context=context,
                )

        metadata = register_source.call_args.args[1]
        self.assertEqual(metadata["observation_kind"], "FIELD")
        self.assertEqual(
            metadata["opaque_details"],
            "  keep exact  ",
        )
        self.assertNotIn("program", metadata)
        self.assertNotIn("academic_year", metadata)
        self.assertNotIn("course_id", metadata)
        self.assertIs(
            ingest_document.call_args.kwargs["product_context"],
            context,
        )

    def test_non_atlas_batch_cannot_receive_atlas_course_metadata(self):
        with self.assertRaisesRegex(
            ValueError,
            "does not declare Atlas course metadata",
        ):
            preview_batch(
                [browser_file_input("field-note.txt", b"Observation")],
                product_context=ProductContext(TEST_PRODUCT),
                input_mode="browser",
                default_course_id="AI-101",
                assignments_confirmed=True,
            )

    def test_atlas_intake_legacy_and_explicit_context_match(self):
        arguments = {
            "product_metadata": {
                "program": "  MSAIB  ",
                "academic_year": "  2026-2027  ",
            },
            "program": "MSAIB",
            "academic_year": "2026-2027",
        }

        legacy = intake_service.normalize_product_metadata(
            **arguments,
        )
        explicit = intake_service.normalize_product_metadata(
            **arguments,
            product_context=create_atlas_context(),
        )

        self.assertEqual(explicit, legacy)
        self.assertEqual(
            explicit,
            {
                "program": "MSAIB",
                "academic_year": "2026-2027",
            },
        )

    def test_record_validation_is_scoped_to_selected_product(self):
        test_context = ProductContext(TEST_PRODUCT)
        objects = [
            {
                "records": [
                    {
                        "type": "field_note",
                        "title": "Finding",
                        "body": "Source truth",
                    }
                ]
            }
        ]
        self.assertIs(
            validate_product_records(
                test_context,
                objects,
            ),
            objects,
        )
        with self.assertRaisesRegex(
            ValueError,
            "Undeclared product record type",
        ):
            validate_product_records(
                create_atlas_context(),
                objects,
            )

    def test_both_products_use_the_same_shared_core_ingestion_seam(self):
        units = [
            {
                "heading": None,
                "text": "Source-backed plain text",
                "location": "Unit 1",
            }
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(
                concept_registry_storage,
                "REGISTRY_PATH",
                root / "concepts.json",
            ):
                atlas_objects = create_product_knowledge_objects(
                    create_atlas_context(),
                    root / "atlas-source.txt",
                    "General",
                    source_id="atlas-source",
                    unit_extractor=lambda path: units,
                    section_selector=(
                        lambda heading, current: current
                    ),
                )
                test_objects = create_product_knowledge_objects(
                    ProductContext(TEST_PRODUCT),
                    root / "field-source.txt",
                    "Observations",
                    source_id="field-source",
                    unit_extractor=lambda path: units,
                    section_selector=(
                        lambda heading, current: current
                    ),
                )
            atlas_path = root / "atlas.json"
            test_path = root / "field-notes.json"
            save_knowledge_objects(atlas_objects, atlas_path)
            save_knowledge_objects(test_objects, test_path)

            self.assertEqual(
                json.loads(
                    atlas_path.read_text(encoding="utf-8")
                )[0]["document"],
                "atlas-source",
            )
            stored_test_object = json.loads(
                test_path.read_text(encoding="utf-8")
            )[0]
            self.assertEqual(
                stored_test_object["document"],
                "field-source",
            )
            self.assertEqual(
                stored_test_object["records"][0]["type"],
                "field_note",
            )

    def test_test_product_retrieval_uses_shared_core_execution(self):
        deterministic = Mock(
            return_value=[
                {
                    "heading": "Source truth",
                    "section": None,
                    "text": "Observed evidence",
                }
            ]
        )
        ranker = Mock(
            side_effect=lambda evidence, terms: evidence
        )
        semantic = Mock(return_value=[])
        concepts = Mock(return_value=[])

        plan, evidence = retrieve_product_evidence(
            ProductContext(TEST_PRODUCT),
            "finding",
            deterministic_retriever=deterministic,
            evidence_ranker=ranker,
            semantic_retriever=semantic,
            concept_retriever=concepts,
        )

        self.assertEqual(plan["record_types"], ["field_note"])
        deterministic.assert_called_once_with(plan)
        self.assertEqual(
            evidence[0]["text"],
            "Observed evidence",
        )

    def test_test_product_is_not_production_selectable(self):
        self.assertEqual(
            PRODUCTION_PRODUCT_REGISTRY.product_ids,
            ("atlas",),
        )
        with self.assertRaisesRegex(
            KeyError,
            "Unknown product",
        ):
            create_product_context(TEST_PRODUCT.product_id)

    def test_terminal_root_passes_one_scoped_context(self):
        context = create_atlas_context()
        with (
            patch.object(
                main,
                "create_atlas_context",
                return_value=context,
            ),
            patch.object(main, "show_header") as show_header,
            patch.object(
                main,
                "get_mission",
                return_value="Question",
            ),
            patch.object(main, "show_topic"),
            patch.object(main, "show_completion"),
            patch.object(
                main,
                "ask_wingman",
                return_value={
                    "answer": "Grounded answer",
                    "evidence": [],
                },
            ) as ask_wingman,
        ):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main.main(), 0)
        show_header.assert_called_once_with(context)
        ask_wingman.assert_called_once_with(
            "Question",
            product_context=context,
        )

    def test_streamlit_pages_pass_context_to_product_paths(self):
        page_directory = SRC_DIRECTORY / "products" / "atlas" / "ui" / "pages"
        trees = [
            ast.parse(path.read_text(encoding="utf-8"))
            for path in (
                page_directory / "chat.py",
                page_directory / "briefing.py",
                page_directory / "upload.py",
                page_directory / "library.py",
                page_directory / "document.py",
            )
        ]
        required_calls = {
            "ask_wingman",
            "create_study_briefing",
            "preview_batch",
            "execute_batch",
            "resume_plan",
            "remove_library_source",
            "reprocess_library_source",
        }
        observed = {}
        for tree in trees:
            for node in ast.walk(tree):
                if not (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id in required_calls
                ):
                    continue
                observed[node.func.id] = {
                    keyword.arg: keyword.value for keyword in node.keywords
                }
        self.assertEqual(set(observed), required_calls)
        for function_name, keywords in observed.items():
            with self.subTest(function_name=function_name):
                self.assertIn("product_context", keywords)
                self.assertEqual(
                    keywords["product_context"].id,
                    "product_context",
                )


if __name__ == "__main__":
    unittest.main()
