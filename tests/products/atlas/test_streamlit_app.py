"""Focused Streamlit AppTest coverage for the Atlas website shell."""

import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from products.atlas.ui.flight_cards import FlightCardsGateway


ROOT = Path(__file__).resolve().parents[3]
APP_PATH = ROOT / "src" / "products" / "atlas" / "streamlit_app.py"


def card_payload(**overrides):
    payload = {
        "source_id": "orientation-2026",
        "display_name": "Orientation Deck",
        "file_name": "orientation.pdf",
        "file_type": "pdf",
        "course_state": "assigned",
        "course_id": "AI-101",
        "course_label": "AI Foundations",
        "material_type": "syllabus",
        "source_status": "ready",
        "summary_status": "ready",
        "summary_points": [
            {"text": "Classes begin August 23.", "evidence_refs": ["E1"]}
        ],
        "evidence_map": {"E1": {"location": "Page 4", "text": "Start date"}},
        "source_link": {"kind": "download"},
        "knowledge_object_count": 4,
        "concept_count": 2,
        "record_count": 1,
        "embedding_count": 4,
        "allowed_actions": {},
    }
    payload.update(overrides)
    return payload


class DemoFlightCardsService:
    def list_course_filters(self):
        return [
            {
                "kind": "all",
                "course_id": None,
                "label": "All materials",
                "document_count": 2,
            },
            {
                "kind": "assigned",
                "course_id": "AI-101",
                "label": "AI Foundations",
                "document_count": 1,
            },
            {
                "kind": "unassigned",
                "course_id": None,
                "label": "Unassigned",
                "document_count": 1,
            },
        ]

    def list_flight_cards(self, course_id=None, course_state=None):
        cards = [
            card_payload(),
            card_payload(
                source_id="needs-course",
                display_name="New material",
                course_state="unassigned",
                course_id=None,
                course_label="Unassigned",
                summary_status="failed",
                safe_failure_message="Summary unavailable.",
            ),
        ]
        if course_state == "unassigned":
            return [cards[1]]
        if course_id:
            return [card for card in cards if card["course_id"] == course_id]
        return cards

    def get_flight_card(self, source_id):
        return card_payload(source_id=source_id)

    def get_source_download(self, source_id):
        return {
            "data": b"source bytes",
            "file_name": f"{source_id}.pdf",
            "mime_type": "application/pdf",
        }


class EmptyFlightCardsService(DemoFlightCardsService):
    def list_course_filters(self):
        return []

    def list_flight_cards(self, course_id=None, course_state=None):
        return []


class ErrorFlightCardsService(DemoFlightCardsService):
    def list_course_filters(self):
        raise RuntimeError("private database details")


class AtlasStreamlitAppTests(unittest.TestCase):
    def assert_no_exception(self, app):
        self.assertEqual([exception.message for exception in app.exception], [])

    def markdown_text(self, app):
        return "\n".join(element.value for element in app.markdown)

    def test_default_shell_has_navigation_and_connected_course_catalog(self):
        with patch(
            "products.atlas.ui.app.load_flight_cards_gateway",
            return_value=FlightCardsGateway(EmptyFlightCardsService()),
        ):
            app = AppTest.from_file(APP_PATH, default_timeout=10).run()
        self.assert_no_exception(app)
        self.assertEqual(
            app.radio[0].options,
            [
                "Course Cockpit",
                "Chat",
                "Briefings",
                "Library",
                "Add Materials",
                "Prompt Optimizer",
            ],
        )
        self.assertIn("Your courses, ready for takeoff.", self.markdown_text(app))
        self.assertTrue(
            any("Flight Cards connected" in success.value for success in app.success)
        )

    def test_cockpit_course_and_unassigned_success_states(self):
        gateway = FlightCardsGateway(DemoFlightCardsService())
        with patch(
            "products.atlas.ui.app.load_flight_cards_gateway", return_value=gateway
        ):
            app = AppTest.from_file(APP_PATH, default_timeout=10).run()
            self.assert_no_exception(app)
            labels = [button.label for button in app.button]
            self.assertIn("Open AI Foundations", labels)
            self.assertIn("Open Unassigned", labels)
            self.assertEqual(
                [metric.value for metric in app.metric[:3]], ["2", "1", "1"]
            )

            next(
                button for button in app.button if button.label == "Open AI Foundations"
            ).click().run()
            self.assert_no_exception(app)
            self.assertEqual(app.query_params["page"], ["course"])
            self.assertEqual(app.query_params["course"], ["AI-101"])
            self.assertIn("AI Foundations", self.markdown_text(app))
            self.assertEqual(
                [tab.label for tab in app.tabs],
                [
                    "Syllabus (1)",
                    "Class notes (0)",
                    "Class lectures (0)",
                    "Homework (0)",
                    "Other (0)",
                    "Summaries (1)",
                ],
            )

    def test_cockpit_empty_and_error_states_are_actionable_and_safe(self):
        with patch(
            "products.atlas.ui.app.load_flight_cards_gateway",
            return_value=FlightCardsGateway(EmptyFlightCardsService()),
        ):
            empty_app = AppTest.from_file(APP_PATH, default_timeout=10).run()
            self.assert_no_exception(empty_app)
            self.assertTrue(
                any("No course groups" in info.value for info in empty_app.info)
            )
            self.assertIn(
                "Add your first materials",
                [button.label for button in empty_app.button],
            )

        with patch(
            "products.atlas.ui.app.load_flight_cards_gateway",
            return_value=FlightCardsGateway(ErrorFlightCardsService()),
        ):
            error_app = AppTest.from_file(APP_PATH, default_timeout=10).run()
            self.assert_no_exception(error_app)
            self.assertEqual(
                [error.value for error in error_app.error],
                ["Atlas could not complete the Flight Cards request."],
            )
            self.assertNotIn(
                "database", " ".join(error.value for error in error_app.error)
            )

    def test_document_deep_link_preserves_source_and_summary(self):
        gateway = FlightCardsGateway(DemoFlightCardsService())
        with patch(
            "products.atlas.ui.app.load_flight_cards_gateway", return_value=gateway
        ):
            app = AppTest.from_file(APP_PATH, default_timeout=10)
            app.query_params["page"] = "document"
            app.query_params["course"] = "AI-101"
            app.query_params["source"] = "orientation-2026"
            app.run()
            self.assert_no_exception(app)
            text = self.markdown_text(app)
            self.assertIn("Orientation Deck", text)
            self.assertIn(
                "AI-generated summary",
                [subheader.value for subheader in app.subheader],
            )
            self.assertIn("Classes begin August 23.", text)
            self.assertEqual(len(app.get("download_button")), 1)

    def test_stale_document_keeps_original_source_available(self):
        service = DemoFlightCardsService()
        service.get_flight_card = lambda source_id: card_payload(
            source_id=source_id,
            summary_status="stale",
            safe_failure_message="The source changed after this summary.",
        )
        with patch(
            "products.atlas.ui.app.load_flight_cards_gateway",
            return_value=FlightCardsGateway(service),
        ):
            app = AppTest.from_file(APP_PATH, default_timeout=10)
            app.query_params["page"] = "document"
            app.query_params["source"] = "orientation-2026"
            app.run()
            self.assert_no_exception(app)
            self.assertEqual(len(app.get("download_button")), 1)
            self.assertTrue(
                any("source changed" in warning.value for warning in app.warning)
            )

    def test_invalid_deep_link_recovers_to_cockpit(self):
        with patch(
            "products.atlas.ui.app.load_flight_cards_gateway",
            return_value=FlightCardsGateway(EmptyFlightCardsService()),
        ):
            app = AppTest.from_file(APP_PATH, default_timeout=10)
            app.query_params["page"] = "document"
            app.run()
        self.assert_no_exception(app)
        self.assertTrue(
            any("document link is incomplete" in info.value for info in app.info)
        )
        self.assertIn("Your courses, ready for takeoff.", self.markdown_text(app))

    def test_practice_test_seam_is_explicitly_unavailable(self):
        app = AppTest.from_file(APP_PATH, default_timeout=10)
        app.query_params["page"] = "practice-test"
        app.query_params["course"] = "AI-101"
        app.run()
        self.assert_no_exception(app)
        self.assertIn("Assessment is not available yet.", self.markdown_text(app))
        self.assertTrue(
            any(
                "approved owning service contract" in warning.value
                for warning in app.warning
            )
        )

    def test_chat_course_context_does_not_claim_restriction(self):
        app = AppTest.from_file(APP_PATH, default_timeout=10)
        app.query_params["page"] = "chat"
        app.query_params["course"] = "AI-101"
        app.run()
        self.assert_no_exception(app)
        self.assertTrue(
            any(
                "course-only retrieval is not proven" in info.value for info in app.info
            )
        )


if __name__ == "__main__":
    unittest.main()
