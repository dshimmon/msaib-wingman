"""Focused persistence and grounding tests for Atlas source summaries."""

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from products.atlas import source_summary_service


def knowledge_units(unit_count=4, words_per_unit=200):
    return [
        {
            "id": f"source-1_{index:03}",
            "document": "source-1",
            "heading": f"Section {index}",
            "location": f"Page {index}",
            "text": " ".join(
                f"evidence-{index}-{word}" for word in range(words_per_unit)
            ),
        }
        for index in range(1, unit_count + 1)
    ]


def response_client(payload):
    create = Mock(return_value=SimpleNamespace(output_text=json.dumps(payload)))
    return SimpleNamespace(responses=SimpleNamespace(create=create)), create


def source_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class SourceSummaryServiceTests(unittest.TestCase):
    def test_summary_artifact_does_not_collide_with_core_knowledge_json(self):
        self.assertFalse(source_summary_service.SUMMARY_FILE_NAME.endswith(".json"))

    def test_generates_and_persists_a_grounded_one_to_two_page_summary(self):
        paragraphs = [
            {
                "text": " ".join(f"summary-{paragraph}-{word}" for word in range(100)),
                "evidence_refs": [f"E{((paragraph - 1) % 4) + 1}"],
            }
            for paragraph in range(1, 6)
        ]
        client, create = response_client(
            {"title": "Document Study Summary", "paragraphs": paragraphs}
        )

        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / "source.pdf"
            original.write_bytes(b"source")
            original_hash = source_hash(original)
            artifact = source_summary_service.generate_and_persist_summary(
                source_id="source-1",
                source_hash=original_hash,
                original_path=original,
                knowledge_objects=knowledge_units(),
                response_client=client,
                clock=lambda: "2026-08-14T12:00:00+00:00",
            )
            stored = json.loads(
                (Path(directory) / source_summary_service.SUMMARY_FILE_NAME).read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(artifact["status"], "ready")
        self.assertEqual(artifact["word_count"], 500)
        self.assertEqual(stored, artifact)
        self.assertEqual(stored["source_hash"], original_hash)
        self.assertEqual(
            stored["knowledge_hash"],
            source_summary_service.processed_knowledge_hash(knowledge_units()),
        )
        self.assertEqual(stored["points"][0]["evidence_refs"], ["E1"])
        request = create.call_args.kwargs
        self.assertEqual(request["model"], source_summary_service.SUMMARY_MODEL)
        self.assertIn("roughly 1–2 pages", request["input"])
        self.assertEqual(
            request["text"]["format"]["schema"]["properties"]["paragraphs"]["items"][
                "properties"
            ]["evidence_refs"]["items"]["enum"],
            ["E1", "E2", "E3", "E4"],
        )

    def test_short_source_receives_proportional_summary_without_padding(self):
        client, create = response_client(
            {
                "title": "Short Note",
                "paragraphs": [
                    {
                        "text": "A concise summary grounded in the short source note.",
                        "evidence_refs": ["E1"],
                    }
                ],
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / "note.txt"
            original.write_text("source", encoding="utf-8")
            artifact = source_summary_service.generate_and_persist_summary(
                source_id="source-1",
                source_hash=source_hash(original),
                original_path=original,
                knowledge_objects=knowledge_units(1, 20),
                response_client=client,
            )

        self.assertEqual(artifact["status"], "ready")
        self.assertLess(
            artifact["word_count"],
            source_summary_service.SUMMARY_TARGET_MIN_WORDS,
        )
        self.assertIn("never repeat or pad", create.call_args.kwargs["input"])

    def test_short_source_rejects_a_padded_non_proportional_summary(self):
        client, _ = response_client(
            {
                "title": "Padded",
                "paragraphs": [
                    {
                        "text": " ".join(f"padding-{index}" for index in range(900)),
                        "evidence_refs": ["E1"],
                    }
                ],
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / "note.txt"
            original.write_text("source", encoding="utf-8")
            artifact = source_summary_service.generate_and_persist_summary(
                source_id="source-1",
                source_hash=source_hash(original),
                original_path=original,
                knowledge_objects=knowledge_units(1, 20),
                response_client=client,
            )

        self.assertEqual(artifact["status"], "failed")
        self.assertEqual(artifact["points"], [])

    def test_invalid_length_persists_safe_failure_without_private_details(self):
        client, _ = response_client(
            {
                "title": "Too Short",
                "paragraphs": [{"text": "Far too short.", "evidence_refs": ["E1"]}],
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / "source.pdf"
            original.write_bytes(b"source")
            artifact = source_summary_service.generate_and_persist_summary(
                source_id="source-1",
                source_hash=source_hash(original),
                original_path=original,
                knowledge_objects=knowledge_units(),
                response_client=client,
            )

        self.assertEqual(artifact["status"], "failed")
        self.assertEqual(artifact["points"], [])
        self.assertEqual(
            artifact["safe_failure"]["message"],
            source_summary_service.SAFE_FAILURE_MESSAGE,
        )
        self.assertNotIn("length", artifact["safe_failure"]["message"].lower())

    def test_generation_rejects_registry_and_current_file_hash_mismatch(self):
        client, create = response_client(
            {
                "title": "Summary",
                "paragraphs": [
                    {"text": "Grounded summary.", "evidence_refs": ["E1"]}
                ],
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / "note.txt"
            original.write_text("changed source", encoding="utf-8")
            current_hash = source_hash(original)
            artifact = source_summary_service.generate_and_persist_summary(
                source_id="source-1",
                source_hash="0" * 64,
                original_path=original,
                knowledge_objects=knowledge_units(1, 20),
                response_client=client,
            )

        self.assertEqual(artifact["status"], "failed")
        self.assertEqual(artifact["source_hash"], current_hash)
        create.assert_not_called()

    def test_concurrent_source_removal_is_not_recreated_by_summary_write(self):
        with tempfile.TemporaryDirectory() as directory:
            source_directory = Path(directory) / "source-1"
            source_directory.mkdir()
            original = source_directory / "source.txt"
            original.write_text("source", encoding="utf-8")

            def remove_source_directory(**_kwargs):
                original.unlink()
                source_directory.rmdir()
                return SimpleNamespace(
                    output_text=json.dumps(
                        {
                            "title": "Summary",
                            "paragraphs": [
                                {
                                    "text": "Grounded summary.",
                                    "evidence_refs": ["E1"],
                                }
                            ],
                        }
                    )
                )

            client = SimpleNamespace(
                responses=SimpleNamespace(create=remove_source_directory)
            )
            with self.assertRaises(FileNotFoundError):
                source_summary_service.generate_and_persist_summary(
                    source_id="source-1",
                    source_hash=source_hash(original),
                    original_path=original,
                    knowledge_objects=knowledge_units(1, 20),
                    response_client=client,
                )

            self.assertFalse(source_directory.exists())

    def test_load_marks_ready_summary_stale_when_source_hash_changes(self):
        client, _ = response_client(
            {
                "title": "Short Note",
                "paragraphs": [
                    {"text": "Grounded summary text.", "evidence_refs": ["E1"]}
                ],
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / "note.txt"
            original.write_text("source", encoding="utf-8")
            original_hash = source_hash(original)
            source_summary_service.generate_and_persist_summary(
                source_id="source-1",
                source_hash=original_hash,
                original_path=original,
                knowledge_objects=knowledge_units(1, 20),
                response_client=client,
            )
            ready = source_summary_service.load_persisted_summary(
                source_id="source-1",
                source_hash=original_hash,
                original_path=original,
                knowledge_objects=knowledge_units(1, 20),
            )
            stale = source_summary_service.load_persisted_summary(
                source_id="source-1",
                source_hash="new-hash",
                original_path=original,
                knowledge_objects=knowledge_units(1, 20),
            )

        self.assertEqual(ready["summary_status"], "ready")
        self.assertEqual(stale["summary_status"], "stale")
        self.assertEqual(stale["summary_points"], ready["summary_points"])
        self.assertIn(
            "source or its processed knowledge changed",
            stale["safe_failure_message"].lower(),
        )

    def test_load_marks_ready_summary_stale_when_original_bytes_change(self):
        client, _ = response_client(
            {
                "title": "Short Note",
                "paragraphs": [
                    {"text": "Grounded summary text.", "evidence_refs": ["E1"]}
                ],
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / "note.txt"
            original.write_text("version one", encoding="utf-8")
            registered_hash = source_hash(original)
            knowledge = knowledge_units(1, 20)
            source_summary_service.generate_and_persist_summary(
                source_id="source-1",
                source_hash=registered_hash,
                original_path=original,
                knowledge_objects=knowledge,
                response_client=client,
            )
            original.write_text("version two changed bytes", encoding="utf-8")
            stale = source_summary_service.load_persisted_summary(
                source_id="source-1",
                source_hash=registered_hash,
                original_path=original,
                knowledge_objects=knowledge,
            )

        self.assertEqual(stale["summary_status"], "stale")

    def test_load_marks_summary_stale_when_processed_knowledge_changes(self):
        original_knowledge = knowledge_units(1, 20)
        reprocessed_knowledge = knowledge_units(1, 20)
        reprocessed_knowledge[0]["text"] = "Materially changed extracted evidence."
        client, _ = response_client(
            {
                "title": "Short Note",
                "paragraphs": [
                    {"text": "Grounded summary text.", "evidence_refs": ["E1"]}
                ],
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / "note.txt"
            original.write_text("unchanged source", encoding="utf-8")
            original_hash = source_hash(original)
            artifact = source_summary_service.generate_and_persist_summary(
                source_id="source-1",
                source_hash=original_hash,
                original_path=original,
                knowledge_objects=original_knowledge,
                response_client=client,
            )
            ready = source_summary_service.load_persisted_summary(
                source_id="source-1",
                source_hash=original_hash,
                original_path=original,
                knowledge_objects=original_knowledge,
            )
            stale = source_summary_service.load_persisted_summary(
                source_id="source-1",
                source_hash=original_hash,
                original_path=original,
                knowledge_objects=reprocessed_knowledge,
            )

        self.assertEqual(ready["summary_status"], "ready")
        self.assertEqual(stale["summary_status"], "stale")
        self.assertEqual(
            artifact["knowledge_hash"],
            ready["summary_knowledge_hash"],
        )
        self.assertNotEqual(
            artifact["knowledge_hash"],
            source_summary_service.processed_knowledge_hash(reprocessed_knowledge),
        )
        self.assertIn(
            "processed knowledge changed",
            stale["safe_failure_message"].lower(),
        )

    def test_large_document_sampling_preserves_opening_and_ending_evidence(self):
        evidence_map, catalog, _ = source_summary_service.build_evidence_catalog(
            knowledge_units(200, 5)
        )

        self.assertEqual(len(evidence_map), source_summary_service.MAX_EVIDENCE_UNITS)
        self.assertIn("Page 1", catalog)
        self.assertIn("Page 200", catalog)

    def test_many_short_units_use_complete_source_length_for_full_page_target(self):
        evidence_map, catalog, source_word_count = (
            source_summary_service.build_evidence_catalog(knowledge_units(1000, 3))
        )
        prompt = source_summary_service._summary_prompt(catalog, source_word_count)

        self.assertEqual(source_word_count, 3000)
        self.assertGreater(
            len(evidence_map),
            source_summary_service.MAX_EVIDENCE_UNITS,
        )
        self.assertIn("roughly 1–2 pages", prompt)
        self.assertNotIn("shorter than a full-length summary target", prompt)


if __name__ == "__main__":
    unittest.main()
