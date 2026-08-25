"""Tests for the source-backed Atlas course catalog service."""

import hashlib
import tempfile
import unittest
import sys
import os
import json
from pathlib import Path
from unittest.mock import call, patch


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from products.atlas import flight_cards_service
from wingman.shared import source_registry


def source_entry(**overrides):
    entry = {
        "source_id": "syllabus-source",
        "display_name": "Course Syllabus",
        "file_name": "syllabus.pdf",
        "file_type": "pdf",
        "mime_type": "application/pdf",
        "course_id": "FINA 7310",
        "course_name": "Corporate Financial Strategy",
        "material_type": "syllabus",
        "status": "Ready",
        "original_available": True,
        "knowledge_object_count": 4,
        "concept_count": 3,
        "record_count": 1,
        "embedding_count": 4,
        "can_reprocess": True,
        "can_remove": True,
        "source_kind": "upload",
    }
    entry.update(overrides)
    return entry


class FlightCardsServiceTests(unittest.TestCase):
    def test_course_filters_use_course_name_and_keep_unassigned_visible(self):
        sources = [
            source_entry(),
            source_entry(
                source_id="lecture-source",
                display_name="Lecture 1",
                material_type="lectures",
            ),
            source_entry(
                source_id="unassigned-source",
                course_id=None,
                course_name=None,
                material_type="other",
            ),
        ]
        with patch.object(
            flight_cards_service,
            "list_library_sources",
            return_value=sources,
        ):
            filters = flight_cards_service.list_course_filters()

        self.assertEqual(filters[0]["document_count"], 3)
        self.assertEqual(filters[1]["course_id"], "FINA 7310")
        self.assertEqual(filters[1]["label"], "Corporate Financial Strategy")
        self.assertEqual(filters[1]["document_count"], 2)
        self.assertEqual(filters[2]["kind"], "unassigned")

    def test_course_folder_keeps_readable_name_over_later_id_fallbacks(self):
        sources = [
            source_entry(),
            source_entry(
                source_id="notes-source",
                course_name="FINA 7310",
                material_type="notes",
            ),
            source_entry(
                source_id="homework-source",
                course_name="FINA 7310",
                material_type="homework",
            ),
        ]
        with patch.object(
            flight_cards_service,
            "list_library_sources",
            return_value=sources,
        ):
            filters = flight_cards_service.list_course_filters()

        self.assertEqual(filters[1]["label"], "Corporate Financial Strategy")

    def test_flight_cards_expose_material_folder_and_source_access(self):
        with patch.object(
            flight_cards_service,
            "list_library_sources",
            return_value=[source_entry()],
        ):
            cards = flight_cards_service.list_flight_cards(course_id="FINA 7310")

        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["material_type"], "syllabus")
        self.assertEqual(cards[0]["source_link"]["kind"], "download")
        self.assertEqual(cards[0]["summary_status"], "missing")
        self.assertFalse(
            cards[0]["allowed_actions"]["request_source_summary"]
        )

    def test_flight_card_loads_persisted_summary_into_course_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            source_directory = Path(directory) / "syllabus-source"
            source_directory.mkdir()
            original = source_directory / "syllabus.pdf"
            original.write_bytes(b"source bytes")
            content_hash = hashlib.sha256(original.read_bytes()).hexdigest()
            summary_path = (
                source_directory
                / flight_cards_service.source_summary_service.SUMMARY_FILE_NAME
            )
            knowledge = [
                {
                    "id": "syllabus-source_001",
                    "document": "syllabus-source",
                    "text": "Evidence",
                }
            ]
            summary_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "source_id": "syllabus-source",
                        "source_hash": content_hash,
                        "knowledge_hash": (
                            flight_cards_service.source_summary_service.processed_knowledge_hash(
                                knowledge
                            )
                        ),
                        "status": "ready",
                        "title": "Course Syllabus Summary",
                        "points": [
                            {"text": "Grounded summary.", "evidence_refs": ["E1"]}
                        ],
                        "evidence_map": {
                            "E1": {"location": "Page 1", "excerpt": "Evidence"}
                        },
                        "generator_version": "generator-v1",
                        "prompt_version": "prompt-v1",
                        "generated_at": "2026-08-14T12:00:00+00:00",
                    }
                ),
                encoding="utf-8",
            )
            source = source_entry(
                original_path=str(original),
                content_hash=content_hash,
                knowledge_path=str(source_directory / "syllabus-source.json"),
            )
            (source_directory / "syllabus-source.json").write_text(
                json.dumps(knowledge), encoding="utf-8"
            )
            with (
                patch.object(
                    flight_cards_service,
                    "list_library_sources",
                    return_value=[source],
                ),
                patch.object(
                    flight_cards_service.intake_service,
                    "UPLOADS_DIRECTORY",
                    Path(directory),
                ),
            ):
                card = flight_cards_service.get_flight_card("syllabus-source")
                original.write_bytes(b"changed source bytes")
                stale_card = flight_cards_service.get_flight_card(
                    "syllabus-source"
                )

        self.assertEqual(card["summary_status"], "ready")
        self.assertEqual(card["summary_title"], "Course Syllabus Summary")
        self.assertEqual(card["summary_points"][0]["evidence_refs"], ["E1"])
        self.assertTrue(card["allowed_actions"]["request_source_summary"])
        self.assertEqual(stale_card["summary_status"], "stale")

    def test_attempt_marker_preserves_failed_state_when_artifact_is_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            source_directory = Path(directory) / "notes-source"
            source_directory.mkdir()
            original = source_directory / "notes.txt"
            original.write_text("source", encoding="utf-8")
            knowledge_path = source_directory / "notes-source.json"
            knowledge_path.write_text(
                json.dumps([{"id": "notes-source_001", "text": "Evidence"}]),
                encoding="utf-8",
            )
            source = source_entry(
                source_id="notes-source",
                original_path=str(original),
                knowledge_path=str(knowledge_path),
                content_hash=hashlib.sha256(original.read_bytes()).hexdigest(),
                atlas_summary_status="pending",
            )
            with (
                patch.object(
                    flight_cards_service,
                    "list_library_sources",
                    return_value=[source],
                ),
                patch.object(
                    flight_cards_service.intake_service,
                    "UPLOADS_DIRECTORY",
                    Path(directory),
                ),
            ):
                card = flight_cards_service.get_flight_card("notes-source")

        self.assertEqual(card["summary_status"], "failed")
        self.assertEqual(card["source_link"]["kind"], "download")
        self.assertTrue(card["allowed_actions"]["request_source_summary"])

    def test_persistence_exception_survives_intake_and_later_card_load(self):
        with tempfile.TemporaryDirectory() as directory:
            uploads = Path(directory) / "uploads"
            registered = {}

            def register(source_id, metadata):
                registered[source_id] = dict(metadata)

            def update(source_id, metadata, **_kwargs):
                registered[source_id].update(metadata)

            with (
                patch.object(
                    flight_cards_service.intake_service,
                    "UPLOADS_DIRECTORY",
                    uploads,
                ),
                patch.object(
                    flight_cards_service.intake_service,
                    "find_source_by_content_hash",
                    return_value=(None, None),
                ),
                patch.object(
                    flight_cards_service.intake_service,
                    "ingest_document",
                    return_value=[{"id": "notes-source_001", "text": "Evidence"}],
                ),
                patch.object(
                    flight_cards_service.intake_service,
                    "register_source",
                    side_effect=register,
                ),
                patch.object(
                    flight_cards_service.intake_service,
                    "update_active_source_metadata",
                    side_effect=update,
                ),
                patch.object(
                    flight_cards_service.source_summary_service,
                    "generate_and_persist_summary",
                    side_effect=OSError("artifact write failed"),
                ),
            ):
                result = flight_cards_service.intake_service.ingest_uploaded_document(
                    "notes.txt", b"source notes"
                )

            source_id = result["source_id"]
            source_directory = uploads / source_id
            knowledge_path = source_directory / f"{source_id}.json"
            knowledge_path.write_text(
                json.dumps([{"id": "notes-source_001", "text": "Evidence"}]),
                encoding="utf-8",
            )
            source = source_entry(
                **registered[source_id],
                source_id=source_id,
                knowledge_path=str(knowledge_path),
                knowledge_object_count=1,
            )
            with (
                patch.object(
                    flight_cards_service,
                    "list_library_sources",
                    return_value=[source],
                ),
                patch.object(
                    flight_cards_service.intake_service,
                    "UPLOADS_DIRECTORY",
                    uploads,
                ),
            ):
                card = flight_cards_service.get_flight_card(source_id)

        self.assertEqual(result["summary_status"], "failed")
        self.assertEqual(registered[source_id]["atlas_summary_status"], "failed")
        self.assertEqual(card["summary_status"], "failed")
        self.assertEqual(card["source_link"]["kind"], "download")
        self.assertTrue(card["allowed_actions"]["request_source_summary"])

    def test_summary_refresh_uses_registered_upload_and_processed_knowledge(self):
        with tempfile.TemporaryDirectory() as directory:
            source_directory = Path(directory) / "notes-source"
            source_directory.mkdir()
            original = source_directory / "notes.txt"
            original.write_text("source", encoding="utf-8")
            knowledge_path = source_directory / "notes-source.json"
            knowledge = [{"id": "notes-source_001", "text": "Source evidence"}]
            knowledge_path.write_text(json.dumps(knowledge), encoding="utf-8")
            source = source_entry(
                source_id="notes-source",
                original_path=str(original),
                knowledge_path=str(knowledge_path),
                content_hash="source-hash",
            )
            with (
                patch.object(
                    flight_cards_service,
                    "list_library_sources",
                    return_value=[source],
                ),
                patch.object(
                    flight_cards_service.intake_service,
                    "UPLOADS_DIRECTORY",
                    Path(directory),
                ),
                patch.object(
                    flight_cards_service.source_summary_service,
                    "generate_and_persist_summary",
                    return_value={"status": "ready"},
                ) as generate,
                patch.object(
                    flight_cards_service,
                    "update_active_source_metadata",
                ) as update,
            ):
                result = flight_cards_service.request_source_summary("notes-source")

        self.assertEqual(result["status"], "ready")
        generate.assert_called_once_with(
            source_id="notes-source",
            source_hash="source-hash",
            original_path=original,
            knowledge_objects=knowledge,
        )
        self.assertEqual(
            update.call_args_list,
            [
                call(
                    "notes-source",
                    {"atlas_summary_status": "pending"},
                    expected_metadata={"content_hash": "source-hash"},
                ),
                call(
                    "notes-source",
                    {"atlas_summary_status": "ready"},
                    expected_metadata={"content_hash": "source-hash"},
                ),
            ],
        )

    def test_summary_refresh_does_not_generate_if_pending_marker_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            source_directory = Path(directory) / "notes-source"
            source_directory.mkdir()
            original = source_directory / "notes.txt"
            original.write_text("source", encoding="utf-8")
            knowledge_path = source_directory / "notes-source.json"
            knowledge_path.write_text("[]", encoding="utf-8")
            source = source_entry(
                source_id="notes-source",
                original_path=str(original),
                knowledge_path=str(knowledge_path),
                content_hash="source-hash",
            )
            with (
                patch.object(
                    flight_cards_service,
                    "list_library_sources",
                    return_value=[source],
                ),
                patch.object(
                    flight_cards_service.intake_service,
                    "UPLOADS_DIRECTORY",
                    Path(directory),
                ),
                patch.object(
                    flight_cards_service,
                    "update_active_source_metadata",
                    side_effect=OSError("registry unavailable"),
                ),
                patch.object(
                    flight_cards_service.source_summary_service,
                    "generate_and_persist_summary",
                ) as generate,
            ):
                with self.assertRaises(OSError):
                    flight_cards_service.request_source_summary("notes-source")

        generate.assert_not_called()

    def test_legacy_manual_summary_failure_is_durable_on_next_card_load(self):
        with tempfile.TemporaryDirectory() as directory:
            source_directory = Path(directory) / "notes-source"
            source_directory.mkdir()
            original = source_directory / "notes.txt"
            original.write_text("source", encoding="utf-8")
            knowledge_path = source_directory / "notes-source.json"
            knowledge_path.write_text(
                json.dumps([{"id": "notes-source_001", "text": "Evidence"}]),
                encoding="utf-8",
            )
            source = source_entry(
                source_id="notes-source",
                original_path=str(original),
                knowledge_path=str(knowledge_path),
                content_hash=hashlib.sha256(original.read_bytes()).hexdigest(),
            )

            def update(_source_id, metadata, **_kwargs):
                source.update(metadata)

            expected_metadata = {"content_hash": source["content_hash"]}
            with (
                patch.object(
                    flight_cards_service,
                    "list_library_sources",
                    return_value=[source],
                ),
                patch.object(
                    flight_cards_service.intake_service,
                    "UPLOADS_DIRECTORY",
                    Path(directory),
                ),
                patch.object(
                    flight_cards_service,
                    "update_active_source_metadata",
                    side_effect=update,
                ) as persist_status,
                patch.object(
                    flight_cards_service.source_summary_service,
                    "generate_and_persist_summary",
                    side_effect=OSError("artifact write failed"),
                ),
            ):
                with self.assertRaises(OSError):
                    flight_cards_service.request_source_summary("notes-source")
                card = flight_cards_service.get_flight_card("notes-source")

        self.assertEqual(source["atlas_summary_status"], "failed")
        self.assertEqual(card["summary_status"], "failed")
        self.assertEqual(card["source_link"]["kind"], "download")
        self.assertTrue(card["allowed_actions"]["request_source_summary"])
        self.assertEqual(
            persist_status.call_args_list,
            [
                call(
                    "notes-source",
                    {"atlas_summary_status": "pending"},
                    expected_metadata=expected_metadata,
                ),
                call(
                    "notes-source",
                    {"atlas_summary_status": "failed"},
                    expected_metadata=expected_metadata,
                ),
            ],
        )

    def test_summary_refresh_rejects_paths_outside_source_upload_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outside = root / "outside"
            outside.mkdir()
            original = outside / "notes.txt"
            original.write_text("source", encoding="utf-8")
            knowledge_path = outside / "notes-source.json"
            knowledge_path.write_text("[]", encoding="utf-8")
            source = source_entry(
                source_id="notes-source",
                original_path=str(original),
                knowledge_path=str(knowledge_path),
                content_hash="source-hash",
            )
            with (
                patch.object(
                    flight_cards_service,
                    "list_library_sources",
                    return_value=[source],
                ),
                patch.object(
                    flight_cards_service.intake_service,
                    "UPLOADS_DIRECTORY",
                    root / "uploads",
                ),
                patch.object(
                    flight_cards_service.source_summary_service,
                    "generate_and_persist_summary",
                ) as generate,
            ):
                with self.assertRaises(FileNotFoundError):
                    flight_cards_service.request_source_summary("notes-source")

        generate.assert_not_called()

    def test_legacy_material_category_remains_visible_as_other(self):
        with patch.object(
            flight_cards_service,
            "list_library_sources",
            return_value=[source_entry(material_type="exam")],
        ):
            cards = flight_cards_service.list_flight_cards()

        self.assertEqual(cards[0]["material_type"], "other")

    def test_source_download_preserves_registered_original(self):
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / "syllabus.pdf"
            original.write_bytes(b"source bytes")
            with patch.object(
                flight_cards_service,
                "load_source_registry",
                return_value={
                    "syllabus-source": {
                        "original_path": str(original),
                        "file_name": "original-syllabus.pdf",
                        "mime_type": "application/pdf",
                    }
                },
            ):
                download = flight_cards_service.get_source_download(
                    "syllabus-source"
                )

        self.assertEqual(download["data"], b"source bytes")
        self.assertEqual(download["file_name"], "original-syllabus.pdf")

    def test_course_reassignment_reuses_existing_folder_name(self):
        registry = {
            "notes-source": {
                "display_name": "Notes",
                "course_id": None,
                "course_name": None,
            },
            "syllabus-source": {
                "display_name": "Syllabus",
                "course_id": "FINA 7310",
                "course_name": "Corporate Financial Strategy",
            },
        }
        updates = []
        with (
            patch.object(
                flight_cards_service,
                "load_source_registry",
                return_value=registry,
            ),
            patch.object(
                flight_cards_service,
                "update_active_source_metadata",
                side_effect=lambda source_id, value: updates.append(
                    (source_id, value)
                ),
            ),
        ):
            result = flight_cards_service.set_source_course(
                "notes-source", " FINA 7310 "
            )

        self.assertEqual(result["status"], "assigned")
        self.assertEqual(
            updates[0][1]["course_name"],
            "Corporate Financial Strategy",
        )

    def test_course_reassignment_preserves_source_registered_after_read(self):
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            environment = {
                "WINGMAN_LEDGER_PATH": str(directory_path / "ledger.sqlite3")
            }
            with (
                patch.dict(os.environ, environment),
                patch.object(
                    source_registry,
                    "SOURCE_REGISTRY_PATH",
                    directory_path / "missing-legacy.json",
                ),
            ):
                source_registry.register_source(
                    "notes-source",
                    {"display_name": "Notes", "course_id": None},
                )
                source_registry.register_source(
                    "syllabus-source",
                    {
                        "display_name": "Syllabus",
                        "course_id": "FINA 7310",
                        "course_name": "Corporate Financial Strategy",
                    },
                )

                def load_then_register_concurrent_source():
                    stale_snapshot = source_registry.load_source_registry()
                    source_registry.register_source(
                        "lecture-source",
                        {"display_name": "Lecture 1"},
                    )
                    return stale_snapshot

                with patch.object(
                    flight_cards_service,
                    "load_source_registry",
                    side_effect=load_then_register_concurrent_source,
                ):
                    flight_cards_service.set_source_course(
                        "notes-source", "FINA 7310"
                    )

                registry = source_registry.load_source_registry()

        self.assertIn("lecture-source", registry)
        self.assertEqual(
            registry["notes-source"]["course_name"],
            "Corporate Financial Strategy",
        )


if __name__ == "__main__":
    unittest.main()
