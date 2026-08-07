# Tests deterministic and semantic retrieval coordination.

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIRECTORY = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIRECTORY))

import products.atlas.retrieval_pipeline as retrieval_pipeline


class RetrievalPipelineTests(unittest.TestCase):
    def run_retrieval(
        self,
        query_plan,
        deterministic_evidence,
        semantic_evidence=None,
        memory_evidence=None,
    ):
        with (
            patch.object(
                retrieval_pipeline,
                "interpret_query",
                return_value=query_plan,
            ),
            patch.object(
                retrieval_pipeline,
                "retrieve_evidence",
                return_value=deterministic_evidence,
            ),
            patch.object(
                retrieval_pipeline,
                "retrieve_semantic_evidence",
                return_value=semantic_evidence or [],
            ) as semantic_retrieval,
            patch.object(
                retrieval_pipeline,
                "retrieve_concept_occurrences",
                return_value=memory_evidence or [],
            ) as concept_retrieval,
        ):
            result = (
                retrieval_pipeline.retrieve_question_evidence(
                    "question"
                )
            )

        return (
            result,
            semantic_retrieval,
            concept_retrieval,
        )

    def test_forwards_conversation_context(self):
        query_plan = {
            "text_search_terms": [],
            "record_types": ["course_schedule"],
            "record_filters": [],
            "memory_search_terms": [],
        }
        conversation_context = [
            {
                "user_question": "Previous question",
                "evidence": [],
            }
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
                return_value=[],
            ),
        ):
            retrieval_pipeline.retrieve_question_evidence(
                "Follow-up question",
                conversation_context=conversation_context,
            )

        interpret_query.assert_called_once_with(
            "Follow-up question",
            conversation_context=conversation_context,
        )

    def test_no_context_forwards_none_safely(self):
        query_plan = {
            "text_search_terms": [],
            "record_types": [],
            "record_filters": [],
            "memory_search_terms": [],
        }

        with (
            patch.object(
                retrieval_pipeline,
                "interpret_query",
                return_value=query_plan,
            ) as interpret_query,
            patch.object(
                retrieval_pipeline,
                "retrieve_evidence",
                return_value=[],
            ),
        ):
            retrieval_pipeline.retrieve_question_evidence(
                "Question"
            )

        interpret_query.assert_called_once_with(
            "Question",
            conversation_context=None,
        )

    def test_strong_heading_match_skips_semantic_retrieval(self):
        query_plan = {
            "text_search_terms": ["orientation"],
            "record_types": [],
            "record_filters": [],
            "memory_search_terms": [],
        }
        evidence = [
            {
                "heading": "Orientation",
                "section": None,
                "text": "Welcome",
            }
        ]

        (_, returned), semantic, _ = self.run_retrieval(
            query_plan,
            evidence,
        )

        semantic.assert_not_called()
        self.assertEqual(returned[0]["score"], 5)

    def test_low_body_text_match_triggers_semantic_retrieval(self):
        query_plan = {
            "text_search_terms": ["laptop"],
            "record_types": [],
            "record_filters": [],
            "memory_search_terms": [],
        }
        semantic_evidence = [
            {
                "heading": None,
                "section": None,
                "text": "laptop requirements",
                "location": "High",
            },
            {
                "heading": None,
                "section": None,
                "text": "other information",
                "location": "Low",
            },
        ]

        (_, returned), semantic, _ = self.run_retrieval(
            query_plan,
            [
                {
                    "heading": None,
                    "section": None,
                    "text": "mentions laptop",
                }
            ],
            semantic_evidence=semantic_evidence,
        )

        semantic.assert_called_once_with(
            "question",
            top_k=3,
        )
        self.assertEqual(
            [item["location"] for item in returned],
            ["High", "Low"],
        )
        self.assertEqual(
            [item["score"] for item in returned],
            [2, 0],
        )

    def test_no_deterministic_text_evidence_uses_semantic(self):
        query_plan = {
            "text_search_terms": ["curriculum"],
            "record_types": [],
            "record_filters": [],
            "memory_search_terms": [],
        }

        (_, returned), semantic, _ = self.run_retrieval(
            query_plan,
            [],
            semantic_evidence=[
                {
                    "heading": "Curriculum",
                    "section": None,
                    "text": "Details",
                }
            ],
        )

        semantic.assert_called_once()
        self.assertEqual(returned[0]["score"], 5)

    def test_structured_record_request_skips_semantic(self):
        query_plan = {
            "text_search_terms": ["schedule"],
            "record_types": ["course"],
            "record_filters": [],
            "memory_search_terms": [],
        }

        (_, returned), semantic, _ = self.run_retrieval(
            query_plan,
            [
                {
                    "heading": None,
                    "section": None,
                    "text": "schedule",
                }
            ],
        )

        semantic.assert_not_called()
        self.assertEqual(returned[0]["score"], 2)

    def test_concept_memory_request_skips_semantic(self):
        query_plan = {
            "text_search_terms": ["curriculum"],
            "record_types": [],
            "record_filters": [],
            "memory_search_terms": ["curriculum"],
        }
        memory_evidence = [
            {
                "heading": "Curriculum",
                "section": None,
                "text": "Concept occurrence",
            }
        ]

        (_, returned), semantic, concept = (
            self.run_retrieval(
                query_plan,
                [],
                memory_evidence=memory_evidence,
            )
        )

        semantic.assert_not_called()
        concept.assert_called_once_with(["curriculum"])
        self.assertEqual(returned[0]["score"], 5)

    def test_single_broad_term_does_not_hijack_semantic_retrieval(self):
        query_plan = {
            "text_search_terms": [
                "Laptop requirements",
                "Computer requirements",
                "Technology requirements",
                "Minimum specifications",
                "MSAIB",
            ],
            "record_types": [],
            "record_filters": [],
            "memory_search_terms": [],
        }

        deterministic_evidence = [
            {
                "heading": "MSAIB Curriculum",
                "section": None,
                "text": "General program information",
                "location": "Slide 8",
            }
        ]

        semantic_evidence = [
            {
                "heading": "Laptop Recommendations",
                "section": None,
                "text": "Computer and laptop requirements",
                "location": "Slide 5",
            }
        ]

        (_, returned), semantic, _ = self.run_retrieval(
            query_plan,
            deterministic_evidence,
            semantic_evidence=semantic_evidence,
        )

        semantic.assert_called_once_with(
            "question",
            top_k=3,
        )

        self.assertEqual(
            returned[0]["location"],
            "Slide 5",
        )

    def test_deterministic_results_remain_ranked(self):
        query_plan = {
            "text_search_terms": ["module"],
            "record_types": ["course"],
            "record_filters": [],
            "memory_search_terms": [],
        }
        evidence = [
            {
                "heading": None,
                "section": None,
                "text": "module details",
                "location": "Body",
            },
            {
                "heading": "Module",
                "section": None,
                "text": "details",
                "location": "Heading",
            },
        ]

        (_, returned), _, _ = self.run_retrieval(
            query_plan,
            evidence,
        )

        self.assertEqual(
            [item["location"] for item in returned],
            ["Heading", "Body"],
        )
        self.assertEqual(
            [item["score"] for item in returned],
            [5, 2],
        )


if __name__ == "__main__":
    unittest.main()
