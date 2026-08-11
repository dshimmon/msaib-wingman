"""Focused tests for safe Atlas deep-link state."""

import unittest

from products.atlas.ui.navigation import (
    AtlasPage,
    NavigationState,
    parse_query_state,
    query_for,
)


class AtlasNavigationTests(unittest.TestCase):
    def test_defaults_to_course_cockpit(self):
        self.assertEqual(parse_query_state({}), NavigationState())

    def test_preserves_valid_course_and_source_identifiers(self):
        state = parse_query_state(
            {
                "page": "document",
                "course": "AI 101/Fall",
                "source": "orientation-deck-2026",
            }
        )
        self.assertEqual(state.page, AtlasPage.DOCUMENT)
        self.assertEqual(state.course_id, "AI 101/Fall")
        self.assertEqual(state.source_id, "orientation-deck-2026")
        self.assertFalse(state.recovered)

    def test_recovers_unknown_and_incomplete_routes(self):
        cases = (
            ({"page": "unknown"}, "not recognized"),
            ({"page": "course"}, "course link is incomplete"),
            ({"page": "document"}, "document link is incomplete"),
            ({"page": "practice-test"}, "course link is incomplete"),
        )
        for query, expected_notice in cases:
            with self.subTest(query=query):
                state = parse_query_state(query)
                self.assertEqual(state.page, AtlasPage.COCKPIT)
                self.assertTrue(state.recovered)
                self.assertIn(expected_notice, state.notice)

    def test_rejects_control_and_oversized_identifiers(self):
        for source_id in ("unsafe\nsource", "x" * 201):
            with self.subTest(source_id=source_id):
                state = parse_query_state({"page": "document", "source": source_id})
                self.assertTrue(state.recovered)

    def test_query_builder_omits_empty_identifiers(self):
        self.assertEqual(
            query_for(AtlasPage.CHAT, course_id=" AI-101 ", source_id=""),
            {"page": "chat", "course": "AI-101"},
        )


if __name__ == "__main__":
    unittest.main()
