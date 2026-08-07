# Tests source-grounded conversation continuity.

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIRECTORY = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIRECTORY))

import products.atlas.retrieval_pipeline as retrieval_pipeline
import products.atlas.wingman_service as wingman_service


class ConversationContextTests(unittest.TestCase):
    def test_compact_evidence_item_preserves_grounding(self):
        long_text = (
            "  First\n\tline   "
            + "x" * (
                wingman_service
                .MAX_TEXT_EXCERPT_CHARACTERS
                + 50
            )
        )
        item = {
            "source": "source-one",
            "location": "Slide 8",
            "heading": "Curriculum",
            "section": "Academics",
            "concepts": [
                {"canonical": "Canonical Concept"},
                {"name": "Named Concept"},
                {"id": "concept-id"},
                "Scalar Concept",
            ],
            "records": [{"type": "curriculum_course"}],
            "text": long_text,
        }

        compacted = wingman_service.compact_evidence_item(
            item
        )

        self.assertEqual(
            compacted["source"],
            "source-one",
        )
        self.assertEqual(
            compacted["location"],
            "Slide 8",
        )
        self.assertEqual(
            compacted["heading"],
            "Curriculum",
        )
        self.assertEqual(
            compacted["section"],
            "Academics",
        )
        self.assertEqual(
            compacted["concepts"],
            [
                "Canonical Concept",
                "Named Concept",
                "concept-id",
                "Scalar Concept",
            ],
        )
        self.assertEqual(
            compacted["records"],
            [{"type": "curriculum_course"}],
        )
        self.assertTrue(
            compacted["text_excerpt"].startswith(
                "First line "
            )
        )
        self.assertNotIn(
            "\n",
            compacted["text_excerpt"],
        )
        self.assertLessEqual(
            len(compacted["text_excerpt"]),
            (
                wingman_service
                .MAX_TEXT_EXCERPT_CHARACTERS
            ),
        )

    def test_build_context_pairs_messages_without_prose(self):
        history = [
            {
                "role": "assistant",
                "content": "Orphan assistant prose",
                "evidence": [{"source": "orphan"}],
            },
            {
                "role": "user",
                "content": " First question? ",
            },
            {
                "role": "assistant",
                "content": "Answer prose must not appear",
                "evidence": [
                    {
                        "source": f"source-{index}",
                        "text": f"Evidence {index}",
                    }
                    for index in range(
                        (
                            wingman_service
                            .MAX_EVIDENCE_ITEMS_PER_TURN
                        )
                        + 2
                    )
                ],
            },
            {
                "role": "user",
                "content": "Final unanswered question?",
            },
        ]

        context = (
            wingman_service.build_conversation_context(
                history
            )
        )

        self.assertEqual(len(context), 1)
        self.assertEqual(
            context[0]["user_question"],
            "First question?",
        )
        self.assertEqual(
            len(context[0]["evidence"]),
            (
                wingman_service
                .MAX_EVIDENCE_ITEMS_PER_TURN
            ),
        )
        self.assertNotIn(
            "Answer prose must not appear",
            str(context),
        )
        self.assertNotIn("orphan", str(context))
        self.assertNotIn(
            "Final unanswered question?",
            str(context),
        )

    def test_build_context_keeps_only_recent_turns(self):
        history = []
        total_turns = (
            wingman_service.MAX_CONVERSATION_TURNS
            + 2
        )

        for turn_number in range(total_turns):
            history.extend(
                [
                    {
                        "role": "user",
                        "content": (
                            f"Question {turn_number}"
                        ),
                    },
                    {
                        "role": "assistant",
                        "content": (
                            f"Answer {turn_number}"
                        ),
                        "evidence": [
                            {
                                "source": (
                                    f"source-{turn_number}"
                                )
                            }
                        ],
                    },
                ]
            )

        context = (
            wingman_service.build_conversation_context(
                history
            )
        )

        self.assertEqual(
            [
                turn["user_question"]
                for turn in context
            ],
            ["Question 2", "Question 3", "Question 4"],
        )

    def test_build_context_handles_missing_history(self):
        self.assertEqual(
            wingman_service.build_conversation_context(
                None
            ),
            [],
        )
        self.assertEqual(
            wingman_service.build_conversation_context(
                []
            ),
            [],
        )

    @patch.object(
        wingman_service,
        "enrich_evidence_sources",
    )
    @patch.object(
        wingman_service,
        "summarize_results",
    )
    @patch.object(
        wingman_service,
        "retrieve_question_evidence",
    )
    def test_ask_wingman_uses_context_and_fresh_evidence(
        self,
        retrieve_evidence,
        summarize_results,
        enrich_sources,
    ):
        fresh_evidence = [
            {
                "source": "fresh-source",
                "location": "Slide 11",
                "text": "Fresh evidence",
            }
        ]
        display_evidence = [
            {
                **fresh_evidence[0],
                "source_metadata": {
                    "display_name": "Fresh Source"
                },
            }
        ]
        retrieve_evidence.return_value = (
            {"record_types": ["course_schedule"]},
            fresh_evidence,
        )
        summarize_results.return_value = "Fresh answer"
        enrich_sources.return_value = display_evidence
        history = [
            {
                "role": "user",
                "content": "What classes are in fall?",
            },
            {
                "role": "assistant",
                "content": "Prior assistant wording",
                "evidence": [
                    {
                        "source": "prior-source",
                        "location": "Slide 8",
                        "text": "Prior curriculum evidence",
                    }
                ],
            },
        ]

        result = wingman_service.ask_wingman(
            "Which of those meet Tuesday?",
            conversation_history=history,
        )

        context = result["conversation_context"]
        retrieve_evidence.assert_called_once_with(
            "Which of those meet Tuesday?",
            conversation_context=context,
        )
        summarize_results.assert_called_once_with(
            "Which of those meet Tuesday?",
            fresh_evidence,
        )
        enrich_sources.assert_called_once_with(
            fresh_evidence
        )
        self.assertNotIn(
            "Prior assistant wording",
            str(context),
        )
        self.assertEqual(
            result["evidence"],
            display_evidence,
        )

    @patch.object(
        wingman_service,
        "enrich_evidence_sources",
        return_value=[],
    )
    @patch.object(
        wingman_service,
        "summarize_results",
        return_value="No evidence",
    )
    @patch.object(
        wingman_service,
        "retrieve_question_evidence",
        return_value=({}, []),
    )
    def test_ask_wingman_without_history(
        self,
        retrieve_evidence,
        summarize_results,
        enrich_sources,
    ):
        result = wingman_service.ask_wingman(
            "Orientation"
        )

        retrieve_evidence.assert_called_once_with(
            "Orientation",
            conversation_context=[],
        )
        self.assertEqual(
            result["conversation_context"],
            [],
        )

    @patch.object(
        wingman_service,
        "enrich_evidence_sources",
        side_effect=lambda evidence: evidence,
    )
    @patch.object(
        wingman_service,
        "summarize_results",
        return_value="Tuesday answer",
    )
    def test_follow_up_uses_context_but_returns_fresh_evidence(
        self,
        summarize_results,
        enrich_sources,
    ):
        prior_evidence = {
            "source": "curriculum-source",
            "location": "Slide 8",
            "heading": "Fall Curriculum",
            "records": [
                {
                    "type": "curriculum_course",
                    "course_name": "Decision Models",
                    "term": "Fall 2026",
                }
            ],
            "text": "Fall courses",
        }
        fresh_evidence = [
            {
                "source": "schedule-source",
                "location": "Slide 11",
                "heading": "Schedule",
                "section": "Academics",
                "records": [
                    {
                        "type": "course_schedule",
                        "day": "Tuesday",
                    }
                ],
                "text": "Tuesday schedule",
            }
        ]
        query_plan = {
            "text_search_terms": [],
            "record_types": ["course_schedule"],
            "record_filters": [
                {"field": "day", "value": "Tuesday"}
            ],
            "memory_search_terms": [],
        }
        history = [
            {
                "role": "user",
                "content": (
                    "What classes will I take in the fall?"
                ),
            },
            {
                "role": "assistant",
                "content": "Prior curriculum answer",
                "evidence": [prior_evidence],
            },
        ]

        with (
            patch.object(
                retrieval_pipeline,
                "interpret_query",
                return_value=query_plan,
            ) as interpret_query,
            patch.object(
                retrieval_pipeline,
                "retrieve_evidence",
                return_value=fresh_evidence,
            ) as retrieve_evidence,
        ):
            result = wingman_service.ask_wingman(
                "Which of those meet on Tuesday?",
                conversation_history=history,
            )

        interpret_query.assert_called_once_with(
            "Which of those meet on Tuesday?",
            conversation_context=(
                result["conversation_context"]
            ),
        )
        retrieve_evidence.assert_called_once_with(query_plan)
        summarize_results.assert_called_once_with(
            "Which of those meet on Tuesday?",
            fresh_evidence,
        )
        self.assertNotIn(
            "Prior curriculum answer",
            str(result["conversation_context"]),
        )
        self.assertEqual(
            result["evidence"][0]["location"],
            "Slide 11",
        )
        self.assertNotIn(
            prior_evidence,
            result["evidence"],
        )

    @patch.object(
        wingman_service,
        "enrich_evidence_sources",
        side_effect=lambda evidence: evidence,
    )
    @patch.object(
        wingman_service,
        "summarize_results",
        return_value="Computer answer",
    )
    def test_topic_change_does_not_inherit_prior_evidence(
        self,
        summarize_results,
        enrich_sources,
    ):
        current_evidence = [
            {
                "source": "computer-source",
                "location": "Slide 5",
                "heading": "Laptop Recommendations",
                "section": None,
                "text": (
                    "Laptop requirements and current "
                    "computer evidence"
                ),
            }
        ]
        query_plan = {
            "text_search_terms": ["Laptop requirements"],
            "record_types": [],
            "record_filters": [],
            "memory_search_terms": [],
        }
        history = [
            {
                "role": "user",
                "content": "What classes are in fall?",
            },
            {
                "role": "assistant",
                "content": "Prior curriculum answer",
                "evidence": [
                    {
                        "source": "curriculum-source",
                        "location": "Slide 8",
                        "text": "Old curriculum evidence",
                    }
                ],
            },
        ]

        with (
            patch.object(
                retrieval_pipeline,
                "interpret_query",
                return_value=query_plan,
            ),
            patch.object(
                retrieval_pipeline,
                "retrieve_evidence",
                return_value=[],
            ),
            patch.object(
                retrieval_pipeline,
                "retrieve_semantic_evidence",
                return_value=current_evidence,
            ),
        ):
            result = wingman_service.ask_wingman(
                (
                    "What kind of computer do I need "
                    "for the program?"
                ),
                conversation_history=history,
            )

        summarize_results.assert_called_once_with(
            (
                "What kind of computer do I need "
                "for the program?"
            ),
            [
                {
                    **current_evidence[0],
                    "score": 2,
                }
            ],
        )
        self.assertEqual(
            result["evidence"][0]["location"],
            "Slide 5",
        )
        self.assertEqual(len(result["evidence"]), 1)


if __name__ == "__main__":
    unittest.main()
