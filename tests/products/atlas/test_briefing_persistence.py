"""Focused tests for immutable briefing persistence and diagnostics."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIRECTORY = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIRECTORY))

import wingman.shared.briefing_persistence as briefing_persistence
import products.atlas.briefing_service as briefing_service
import wingman.shared.diagnostic_service as diagnostic_service
import wingman.shared.source_registry as source_registry
from wingman.core import ledger
from wingman.core.ledger.briefing_repository import (
    get_briefing,
    get_current_briefing_version,
    list_briefing_versions,
)
from wingman.core.ledger.database import connect_database, transaction
from wingman.core.ledger.diagnostic_repository import list_events_for_trace
from wingman.core.ledger.migrations import apply_migrations
from wingman.core.ledger.source_repository import create_source, create_source_version
from wingman.core.ledger.source_repository import update_source


class BriefingPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = (
            Path(self.temporary_directory.name) / "ledger.sqlite3"
        )
        self.environment = patch.dict(
            os.environ,
            {"WINGMAN_LEDGER_PATH": str(self.database_path)},
        )
        self.environment.start()
        self.legacy_path = patch.object(
            source_registry,
            "SOURCE_REGISTRY_PATH",
            Path(self.temporary_directory.name) / "missing.json",
        )
        self.legacy_path.start()

    def tearDown(self):
        self.legacy_path.stop()
        self.environment.stop()
        self.temporary_directory.cleanup()

    def result(self, text="Evidence", source="source-one"):
        return {
            "topic": "Prepare me",
            "planner_type": "deterministic_module",
            "retrieval_results": [
                {
                    "category": "curriculum",
                    "question": "Which courses?",
                    "query_plan": {"record_types": ["course"]},
                    "evidence_count": 1,
                }
            ],
            "briefing": {
                "title": "Preparation",
                "overview": "Overview",
                "verified_facts": [{"evidence_refs": ["E1"]}],
                "recommended_actions": [],
                "open_questions": [],
            },
            "evidence_reference_map": {
                "E1": {
                    "source": source,
                    "location": "Slide 8",
                    "heading": "Curriculum",
                }
            },
            "evidence": [
                {
                    "source": source,
                    "location": "Slide 8",
                    "heading": "Curriculum",
                    "domain": "academic",
                    "section": "Module A",
                    "text": text,
                    "structured_records": [{"course": "AI"}],
                    "concepts": ["AI"],
                    "source_metadata": {"display_name": "Handbook"},
                }
            ],
        }

    def seed_source(self):
        connection = connect_database()
        apply_migrations(connection)
        with transaction(connection):
            create_source(
                connection,
                entity_id="source-one",
                source_kind="document",
                display_name="Handbook",
            )
            create_source_version(
                connection,
                entity_id="source_version_one",
                source_id="source-one",
                version_number=1,
                content_hash="abc",
                change_type="registered",
            )
        connection.close()

    def test_new_and_refreshed_versions_round_trip_and_advance(self):
        self.seed_source()
        first_payload = self.result()
        first = briefing_persistence.persist_generated_briefing(
            first_payload, trace_id="trace_one"
        )
        connection = connect_database()
        first_bytes_before_refresh = tuple(
            connection.execute(
                """
                SELECT briefing_json, retrieval_results_json,
                       evidence_snapshot_json, source_fingerprint
                FROM briefing_versions WHERE entity_id = ?
                """,
                (first.briefing_version_id,),
            ).fetchone()
        )
        connection.close()
        second_payload = self.result("Changed evidence")
        second_payload["briefing"]["title"] = "Changed title"
        second = briefing_persistence.persist_generated_briefing(
            second_payload,
            trace_id="trace_two",
            briefing_id=first.briefing_id,
        )

        connection = connect_database()
        versions = list_briefing_versions(
            connection, first.briefing_id
        )
        current = get_current_briefing_version(
            connection, first.briefing_id
        )
        briefing = get_briefing(connection, first.briefing_id)
        first_bytes_after_refresh = tuple(
            connection.execute(
                """
                SELECT briefing_json, retrieval_results_json,
                       evidence_snapshot_json, source_fingerprint
                FROM briefing_versions WHERE entity_id = ?
                """,
                (first.briefing_version_id,),
            ).fetchone()
        )
        connection.close()

        self.assertEqual(first.version_number, 1)
        self.assertEqual(second.version_number, 2)
        self.assertEqual([v.version_number for v in versions], [1, 2])
        self.assertEqual(versions[0].briefing, first_payload["briefing"])
        self.assertEqual(
            versions[0].retrieval_results,
            first_payload["retrieval_results"],
        )
        self.assertEqual(
            versions[0].evidence_snapshot["evidence_reference_map"],
            first_payload["evidence_reference_map"],
        )
        evidence = versions[0].evidence_snapshot["ordered_evidence"][0]
        self.assertEqual(evidence["text"], "Evidence")
        self.assertEqual(
            evidence["source_version_id"], "source_version_one"
        )
        self.assertEqual(current.entity_id, second.briefing_version_id)
        self.assertEqual(briefing.title, "Preparation")
        self.assertEqual(briefing.topic, "Prepare me")
        self.assertEqual(briefing.version, 3)
        self.assertEqual(
            first_bytes_after_refresh,
            first_bytes_before_refresh,
        )
        self.assertNotEqual(
            versions[0].source_fingerprint,
            versions[1].source_fingerprint,
        )

    def test_ordered_evidence_and_references_round_trip_exactly(self):
        payload = self.result()
        payload["evidence"].append(
            {
                "source": "source-two",
                "location": "Page 4",
                "heading": "Technology",
                "domain": "academic",
                "section": "Requirements",
                "text": "Second item",
                "structured_records": [{"device": "Laptop"}],
                "concepts": ["Hardware"],
                "source_metadata": {"display_name": "Technology Guide"},
            }
        )
        payload["evidence_reference_map"]["E2"] = {
            "source": "source-two",
            "location": "Page 4",
            "heading": "Technology",
        }
        saved = briefing_persistence.persist_generated_briefing(
            payload, trace_id="trace_order"
        )
        connection = connect_database()
        version = get_current_briefing_version(
            connection, saved.briefing_id
        )
        connection.close()
        snapshot = version.evidence_snapshot
        self.assertEqual(
            list(snapshot["evidence_reference_map"]), ["E1", "E2"]
        )
        self.assertEqual(
            [
                (
                    item["source"],
                    item["location"],
                    item["heading"],
                )
                for item in snapshot["ordered_evidence"]
            ],
            [
                ("source-one", "Slide 8", "Curriculum"),
                ("source-two", "Page 4", "Technology"),
            ],
        )
        self.assertEqual(
            snapshot["ordered_evidence"][1]["structured_records"],
            [{"device": "Laptop"}],
        )
        self.assertEqual(
            snapshot["ordered_evidence"][1]["concepts"], ["Hardware"]
        )

    def test_invalid_id_and_transaction_failure_leave_no_orphans(self):
        with self.assertRaisesRegex(KeyError, "Unknown briefing"):
            briefing_persistence.persist_generated_briefing(
                self.result(),
                trace_id="trace_invalid",
                briefing_id="briefing_missing",
            )
        with patch.object(
            briefing_persistence,
            "create_briefing_version",
            side_effect=RuntimeError("version failed"),
        ):
            with self.assertRaisesRegex(RuntimeError, "version failed"):
                briefing_persistence.persist_generated_briefing(
                    self.result(), trace_id="trace_rollback"
                )
        connection = connect_database()
        count = connection.execute(
            "SELECT COUNT(*) FROM briefings"
        ).fetchone()[0]
        connection.close()
        self.assertEqual(count, 0)

    def test_new_briefing_rolls_back_after_parent_entity_insert(self):
        original = ledger.briefing_repository.insert_entity

        def fail_after_entity(*args, **kwargs):
            original(*args, **kwargs)
            raise RuntimeError("briefing row failed")

        with patch.object(
            ledger.briefing_repository,
            "insert_entity",
            side_effect=fail_after_entity,
        ):
            with self.assertRaisesRegex(
                RuntimeError, "briefing row failed"
            ):
                briefing_persistence.persist_generated_briefing(
                    self.result(), trace_id="trace_parent_failure"
                )
        connection = connect_database()
        entity_count = connection.execute(
            """
            SELECT COUNT(*) FROM entities
            WHERE entity_type IN ('briefing', 'briefing_version')
            """
        ).fetchone()[0]
        briefing_count = connection.execute(
            "SELECT COUNT(*) FROM briefings"
        ).fetchone()[0]
        connection.close()
        self.assertEqual((entity_count, briefing_count), (0, 0))

    def test_failed_refresh_preserves_parent_pointer_and_prior_bytes(self):
        first = briefing_persistence.persist_generated_briefing(
            self.result(), trace_id="trace_first"
        )
        connection = connect_database()
        before_parent = get_briefing(connection, first.briefing_id)
        before_bytes = connection.execute(
            """
            SELECT briefing_json, retrieval_results_json,
                   evidence_snapshot_json, source_fingerprint
            FROM briefing_versions WHERE entity_id = ?
            """,
            (first.briefing_version_id,),
        ).fetchone()
        connection.close()

        original = ledger.briefing_repository.insert_entity

        def fail_after_version_entity(
            connection, entity_id, entity_type, *args, **kwargs
        ):
            original(
                connection,
                entity_id,
                entity_type,
                *args,
                **kwargs,
            )
            if entity_type == "briefing_version":
                raise RuntimeError("version row failed")

        with patch.object(
            ledger.briefing_repository,
            "insert_entity",
            side_effect=fail_after_version_entity,
        ):
            with self.assertRaisesRegex(
                RuntimeError, "version row failed"
            ):
                briefing_persistence.persist_generated_briefing(
                    self.result("new"),
                    trace_id="trace_refresh_failure",
                    briefing_id=first.briefing_id,
                )

        connection = connect_database()
        after_parent = get_briefing(connection, first.briefing_id)
        after_bytes = connection.execute(
            """
            SELECT briefing_json, retrieval_results_json,
                   evidence_snapshot_json, source_fingerprint
            FROM briefing_versions WHERE entity_id = ?
            """,
            (first.briefing_version_id,),
        ).fetchone()
        version_count = len(
            list_briefing_versions(connection, first.briefing_id)
        )
        orphan_count = connection.execute(
            """
            SELECT COUNT(*) FROM entities
            WHERE entity_type = 'briefing_version'
              AND entity_id NOT IN (
                  SELECT entity_id FROM briefing_versions
              )
            """
        ).fetchone()[0]
        connection.close()
        self.assertEqual(after_parent, before_parent)
        self.assertEqual(tuple(after_bytes), tuple(before_bytes))
        self.assertEqual(version_count, 1)
        self.assertEqual(orphan_count, 0)

    def test_duplicate_version_conflict_rolls_back_without_pointer_move(self):
        first = briefing_persistence.persist_generated_briefing(
            self.result(), trace_id="trace_unique_first"
        )
        with patch.object(
            briefing_persistence,
            "next_briefing_version_number",
            return_value=1,
        ):
            with self.assertRaises(Exception):
                briefing_persistence.persist_generated_briefing(
                    self.result("duplicate"),
                    trace_id="trace_unique_conflict",
                    briefing_id=first.briefing_id,
                )
        connection = connect_database()
        parent = get_briefing(connection, first.briefing_id)
        versions = list_briefing_versions(
            connection, first.briefing_id
        )
        connection.close()
        self.assertEqual(
            parent.current_briefing_version_id,
            first.briefing_version_id,
        )
        self.assertEqual(parent.version, 2)
        self.assertEqual(len(versions), 1)

    def test_version_numbers_are_scoped_to_each_briefing(self):
        first = briefing_persistence.persist_generated_briefing(
            self.result(), trace_id="trace_scope_one"
        )
        other = briefing_persistence.persist_generated_briefing(
            self.result(), trace_id="trace_scope_other"
        )
        refreshed = briefing_persistence.persist_generated_briefing(
            self.result("refreshed"),
            trace_id="trace_scope_refresh",
            briefing_id=first.briefing_id,
        )
        self.assertEqual(first.version_number, 1)
        self.assertEqual(other.version_number, 1)
        self.assertEqual(refreshed.version_number, 2)

    def test_reference_alignment_is_validated_before_database_open(self):
        payload = self.result()
        payload["evidence_reference_map"]["E1"]["location"] = "Slide 9"
        with self.assertRaisesRegex(
            ValueError, "does not match"
        ):
            briefing_persistence.persist_generated_briefing(
                payload, trace_id="trace_bad_reference"
            )
        self.assertFalse(self.database_path.exists())

        missing = self.result()
        missing["evidence_reference_map"] = {"E2": {}}
        with self.assertRaisesRegex(ValueError, "must align"):
            briefing_persistence.persist_generated_briefing(
                missing, trace_id="trace_missing_reference"
            )
        self.assertFalse(self.database_path.exists())

    def test_missing_source_fallback_and_fingerprint_canonicalization(self):
        saved = briefing_persistence.persist_generated_briefing(
            self.result(), trace_id="trace_missing"
        )
        connection = connect_database()
        version = get_current_briefing_version(
            connection, saved.briefing_id
        )
        connection.close()
        item = version.evidence_snapshot["ordered_evidence"][0]
        self.assertIsNone(item["source_version_id"])
        self.assertTrue(item["evidence_content_hash"])
        self.assertEqual(saved.unresolved_source_ids, ("source-one",))

        reordered = dict(reversed(list(item.items())))
        self.assertEqual(
            briefing_persistence.source_fingerprint([item]),
            briefing_persistence.source_fingerprint([reordered]),
        )
        changed = dict(item, location="Slide 9")
        self.assertNotEqual(
            briefing_persistence.source_fingerprint([item]),
            briefing_persistence.source_fingerprint([changed]),
        )

    def test_fingerprint_identity_fields_body_and_order_are_significant(self):
        first = briefing_persistence._snapshot_item(
            {
                "source": "source-one",
                "location": "Slide 1",
                "text": "First",
            },
            None,
            {},
        )
        second = briefing_persistence._snapshot_item(
            {
                "source": "source-two",
                "location": "Slide 2",
                "text": "Second",
            },
            None,
            {},
        )
        baseline = briefing_persistence.source_fingerprint(
            [first, second]
        )
        changes = [
            [dict(first, source_id="different"), second],
            [dict(first, source_version_id="version_two"), second],
            [dict(first, location="Slide 9"), second],
            [
                briefing_persistence._snapshot_item(
                    {
                        "source": "source-one",
                        "location": "Slide 1",
                        "text": "Changed",
                    },
                    None,
                    {},
                ),
                second,
            ],
            [second, first],
        ]
        for changed in changes:
            self.assertNotEqual(
                briefing_persistence.source_fingerprint(changed),
                baseline,
            )

    def test_historical_friendly_metadata_is_not_live_resolved(self):
        self.seed_source()
        payload = self.result()
        saved = briefing_persistence.persist_generated_briefing(
            payload, trace_id="trace_metadata"
        )
        connection = connect_database()
        with transaction(connection):
            update_source(
                connection,
                "source-one",
                source_kind="document",
                display_name="Renamed",
                status="active",
                metadata={"display_name": "Renamed"},
            )
        version = get_current_briefing_version(
            connection, saved.briefing_id
        )
        connection.close()
        self.assertEqual(
            version.evidence_snapshot["ordered_evidence"][0][
                "source_metadata"
            ],
            {"display_name": "Handbook"},
        )

    def test_service_success_warnings_and_diagnostics(self):
        generated = self.result()
        gathered = {
            "topic": generated["topic"],
            "planner_type": generated["planner_type"],
            "briefing_title": generated["briefing"]["title"],
            "retrieval_results": generated["retrieval_results"],
            "evidence": [
                {
                    key: value
                    for key, value in generated["evidence"][0].items()
                    if key != "source_metadata"
                }
            ],
        }
        with (
            patch.object(
                briefing_service,
                "gather_briefing_evidence",
                return_value=gathered,
            ),
            patch.object(
                briefing_service,
                "generate_study_briefing",
                return_value={
                    "briefing": generated["briefing"],
                    "evidence_reference_map": generated[
                        "evidence_reference_map"
                    ],
                },
            ),
            patch.object(
                briefing_service,
                "enrich_evidence_sources",
                return_value=generated["evidence"],
            ),
        ):
            result = briefing_service.create_study_briefing("Prepare me")
        self.assertEqual(result["persistence"]["status"], "saved")
        self.assertNotIn("planner_type", result)
        connection = connect_database()
        events = list_events_for_trace(
            connection, result["persistence"]["trace_id"]
        )
        connection.close()
        self.assertEqual(
            [event.severity for event in events], ["warning", "info"]
        )
        self.assertEqual(
            get_current_planner_type(self.database_path),
            "deterministic_module",
        )

    def test_persist_false_and_failure_contracts(self):
        generated_result = self.result()
        gathered = {
            "topic": "Prepare me",
            "planner_type": "general_llm",
            "briefing_title": "Preparation",
            "retrieval_results": generated_result["retrieval_results"],
            "evidence": generated_result["evidence"],
        }
        patches = (
            patch.object(
                briefing_service,
                "gather_briefing_evidence",
                return_value=gathered,
            ),
            patch.object(
                briefing_service,
                "generate_study_briefing",
                return_value={
                    "briefing": generated_result["briefing"],
                    "evidence_reference_map": generated_result[
                        "evidence_reference_map"
                    ],
                },
            ),
            patch.object(
                briefing_service,
                "enrich_evidence_sources",
                return_value=generated_result["evidence"],
            ),
        )
        with patches[0], patches[1], patches[2]:
            skipped = briefing_service.create_study_briefing(
                "Prepare me", persist=False
            )
        self.assertEqual(skipped["persistence"]["status"], "not_requested")
        self.assertFalse(self.database_path.exists())

        with (
            patch.object(
                briefing_service,
                "gather_briefing_evidence",
                return_value=gathered,
            ),
            patch.object(
                briefing_service,
                "generate_study_briefing",
                return_value={
                    "briefing": generated_result["briefing"],
                    "evidence_reference_map": generated_result[
                        "evidence_reference_map"
                    ],
                },
            ),
            patch.object(
                briefing_service,
                "enrich_evidence_sources",
                return_value=generated_result["evidence"],
            ),
            patch.object(
                briefing_service,
                "persist_generated_briefing",
                side_effect=RuntimeError("save failed"),
            ),
        ):
            failed = briefing_service.create_study_briefing("Prepare me")
        self.assertEqual(failed["persistence"]["status"], "failed")
        self.assertEqual(
            failed["persistence"]["error"],
            "Briefing could not be saved.",
        )

    def test_generation_failure_reraises_and_attempts_diagnostic(self):
        with (
            patch.object(
                briefing_service,
                "gather_briefing_evidence",
                side_effect=ValueError("generation failed"),
            ),
            patch.object(
                briefing_service, "record_diagnostic"
            ) as diagnostic,
        ):
            with self.assertRaisesRegex(ValueError, "generation failed"):
                briefing_service.create_study_briefing("topic")
        self.assertEqual(
            diagnostic.call_args.kwargs["operation"],
            "briefing_generation",
        )

    def test_diagnostic_exceptions_do_not_change_saved_or_failed_outcome(self):
        generated = self.result()
        gathered = {
            "topic": generated["topic"],
            "planner_type": generated["planner_type"],
            "briefing_title": generated["briefing"]["title"],
            "retrieval_results": generated["retrieval_results"],
            "evidence": generated["evidence"],
        }
        generation = {
            "briefing": generated["briefing"],
            "evidence_reference_map": generated[
                "evidence_reference_map"
            ],
        }
        with (
            patch.object(
                briefing_service,
                "gather_briefing_evidence",
                return_value=gathered,
            ),
            patch.object(
                briefing_service,
                "generate_study_briefing",
                return_value=generation,
            ),
            patch.object(
                briefing_service,
                "enrich_evidence_sources",
                return_value=generated["evidence"],
            ),
            patch.object(
                briefing_service,
                "record_diagnostic",
                side_effect=RuntimeError("diagnostic failed"),
            ),
        ):
            saved = briefing_service.create_study_briefing("Prepare me")
        self.assertEqual(saved["persistence"]["status"], "saved")

        original_error = ValueError("original generation failure")
        with (
            patch.object(
                briefing_service,
                "gather_briefing_evidence",
                side_effect=original_error,
            ),
            patch.object(
                briefing_service,
                "record_diagnostic",
                side_effect=RuntimeError("diagnostic failed"),
            ),
        ):
            with self.assertRaises(ValueError) as raised:
                briefing_service.create_study_briefing("topic")
        self.assertIs(raised.exception, original_error)

    def test_streamlit_warning_and_full_evidence_expander_are_safe(self):
        source = (
            PROJECT_ROOT
            / "src"
            / "products"
            / "atlas"
            / "ui"
            / "pages"
            / "briefing.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "This briefing was generated but could not be saved.",
            source,
        )
        self.assertIn("View complete source evidence", source)
        self.assertNotIn(
            "result.get(\"persistence\", {}).get(\"error\")",
            source,
        )

    def test_diagnostic_fallback_logs(self):
        with (
            patch.object(
                diagnostic_service,
                "open_registry_database",
                side_effect=RuntimeError("unavailable"),
            ),
            self.assertLogs(
                "wingman.shared.diagnostic_service", level="ERROR"
            ),
        ):
            result = diagnostic_service.record_diagnostic(
                operation="test",
                severity="error",
                recoverable=False,
                message="Test",
            )
        self.assertIsNone(result)


def get_current_planner_type(database_path):
    connection = connect_database(database_path)
    row = connection.execute(
        """
        SELECT planner_type FROM briefing_versions
        ORDER BY version_number DESC LIMIT 1
        """
    ).fetchone()
    connection.close()
    return row["planner_type"]


if __name__ == "__main__":
    unittest.main()
