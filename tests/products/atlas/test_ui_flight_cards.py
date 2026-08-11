"""Tests for the narrow Flight Cards website adapter."""

import unittest
from types import SimpleNamespace

from products.atlas.ui.flight_cards import (
    FlightCardsGateway,
    FlightCardsRequestError,
    FlightCardsUnavailable,
    normalize_flight_card,
)


def flight_card_payload(**overrides):
    payload = {
        "source_id": "orientation-2026",
        "display_name": "Orientation Deck",
        "file_name": "orientation.pdf",
        "file_type": "pdf",
        "course_state": "assigned",
        "course_id": "AI-101",
        "course_label": "AI Foundations",
        "source_status": "ready",
        "summary_status": "ready",
        "summary_points": [
            {"text": "Classes begin August 23.", "evidence_refs": ["E1"]}
        ],
        "source_hash": "source-hash",
        "summary_source_hash": "source-hash",
        "generator_version": "flight-cards-v1",
        "prompt_version": "summary-v2",
        "evidence_map": {"E1": {"location": "Page 4"}},
        "source_link": {"kind": "download", "label": "Download source"},
        "knowledge_object_count": 4,
        "allowed_actions": {
            "set_source_course": True,
            "request_source_summary": True,
            "reprocess_library_source": True,
            "remove_library_source": False,
        },
    }
    payload.update(overrides)
    return payload


class FlightCardsAdapterTests(unittest.TestCase):
    def test_normalizes_contract_and_allowed_actions(self):
        card = normalize_flight_card(flight_card_payload())
        self.assertEqual(card.source_id, "orientation-2026")
        self.assertEqual(card.course_label, "AI Foundations")
        self.assertEqual(card.summary_points[0].evidence_refs, ("E1",))
        self.assertEqual(card.evidence_map["E1"]["location"], "Page 4")
        self.assertTrue(card.can_set_course)
        self.assertTrue(card.can_request_summary)
        self.assertTrue(card.can_reprocess)
        self.assertFalse(card.can_remove)

    def test_keeps_valid_source_visible_when_summary_failed_or_stale(self):
        for status in ("failed", "stale"):
            with self.subTest(status=status):
                card = normalize_flight_card(
                    flight_card_payload(
                        summary_status=status,
                        safe_failure_message="Summary unavailable.",
                    )
                )
                self.assertEqual(card.source_status, "ready")
                self.assertEqual(card.source_link.kind, "download")
                self.assertEqual(card.summary_status, status)
                self.assertEqual(card.safe_failure_message, "Summary unavailable.")

    def test_accepts_attribute_objects_and_nested_summary(self):
        card = normalize_flight_card(
            SimpleNamespace(
                source_id="source-2",
                display_name="Source Two",
                course_state="unassigned",
                source_status="partially_indexed",
                summary_status="pending",
                summary_points=(),
                source_link=SimpleNamespace(kind="unavailable", url=None),
            )
        )
        self.assertIsNone(card.course_id)
        self.assertEqual(card.course_label, "Unassigned")
        self.assertEqual(card.source_status, "partially_indexed")

    def test_normalizes_nested_metadata_and_counts(self):
        card = normalize_flight_card(
            flight_card_payload(
                generator_version=None,
                prompt_version=None,
                generator_metadata={"version": "generator-v3"},
                prompt_metadata={"id": "prompt-v4"},
                knowledge_object_count=None,
                concept_count=None,
                record_count=None,
                embedding_count=None,
                counts={
                    "knowledge_objects": 8,
                    "concepts": 3,
                    "records": 2,
                    "embeddings": 8,
                },
            )
        )
        self.assertEqual(card.generator_version, "generator-v3")
        self.assertEqual(card.prompt_version, "prompt-v4")
        self.assertEqual(
            (
                card.knowledge_object_count,
                card.concept_count,
                card.record_count,
                card.embedding_count,
            ),
            (8, 3, 2, 8),
        )

    def test_gateway_calls_only_presentation_contract(self):
        calls = []

        class Service:
            def list_course_filters(self):
                calls.append(("filters",))
                return [
                    {
                        "kind": "assigned",
                        "course_id": "AI-101",
                        "label": "AI Foundations",
                        "document_count": 1,
                    }
                ]

            def list_flight_cards(self):
                calls.append(("cards",))
                return [flight_card_payload()]

            def get_flight_card(self, source_id):
                calls.append(("card", source_id))
                return flight_card_payload(source_id=source_id)

            def get_source_download(self, source_id):
                calls.append(("download", source_id))
                return {
                    "data": b"source",
                    "file_name": "source.pdf",
                    "mime_type": "application/pdf",
                }

            def set_source_course(self, source_id, course_id):
                calls.append(("assign", source_id, course_id))

            def request_source_summary(self, source_id):
                calls.append(("summary", source_id))

        gateway = FlightCardsGateway(Service())
        self.assertEqual(gateway.list_course_filters()[0].course_id, "AI-101")
        self.assertEqual(
            gateway.list_flight_cards(course_id="AI-101")[0].source_id,
            "orientation-2026",
        )
        self.assertEqual(gateway.get_flight_card("source-1").source_id, "source-1")
        self.assertEqual(gateway.get_source_download("source-1").data, b"source")
        gateway.set_source_course("source-1", None)
        gateway.request_source_summary("source-1")
        self.assertEqual(
            calls,
            [
                ("filters",),
                ("cards",),
                ("card", "source-1"),
                ("download", "source-1"),
                ("assign", "source-1", None),
                ("summary", "source-1"),
            ],
        )

    def test_unavailable_and_service_errors_are_safe(self):
        with self.assertRaisesRegex(FlightCardsUnavailable, "waiting"):
            FlightCardsGateway(unavailable_reason="waiting").list_course_filters()

        service = SimpleNamespace(
            get_flight_card=lambda source_id: (_ for _ in ()).throw(
                RuntimeError("private database path")
            )
        )
        with self.assertRaisesRegex(
            FlightCardsRequestError, "could not complete"
        ) as raised:
            FlightCardsGateway(service).get_flight_card("source-1")
        self.assertNotIn("database", str(raised.exception))

    def test_rejects_card_without_stable_source_id(self):
        with self.assertRaisesRegex(FlightCardsRequestError, "without an ID"):
            normalize_flight_card({"display_name": "Unknown"})


if __name__ == "__main__":
    unittest.main()
