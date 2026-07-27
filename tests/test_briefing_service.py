# Tests briefing evidence gathering and coordination.

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIRECTORY = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIRECTORY))

import briefing_service


class BriefingServiceTests(unittest.TestCase):
    @patch.object(
        briefing_service,
        "retrieve_question_evidence",
    )
    @patch.object(
        briefing_service,
        "create_briefing_plan",
    )
    def test_gathering_limits_each_category_to_one_item(
        self,
        create_plan,
        retrieve_evidence,
    ):
        create_plan.return_value = {
            "briefing_title": "Test Briefing",
            "retrieval_questions": [
                {
                    "category": "curriculum",
                    "question": "Curriculum question",
                },
                {
                    "category": "schedule",
                    "question": "Schedule question",
                },
            ],
        }
        retrieve_evidence.side_effect = [
            (
                {"record_types": ["curriculum_course"]},
                [
                    {
                        "id": "curriculum-1",
                        "source": "source-one",
                        "location": "Slide 8",
                    },
                    {
                        "id": "curriculum-2",
                        "source": "source-one",
                        "location": "Slide 9",
                    },
                ],
            ),
            (
                {"record_types": ["course_schedule"]},
                [
                    {
                        "id": "schedule-1",
                        "source": "source-one",
                        "location": "Slide 11",
                    },
                    {
                        "id": "schedule-2",
                        "source": "source-one",
                        "location": "Slide 12",
                    },
                ],
            ),
        ]

        result = briefing_service.gather_briefing_evidence(
            "Test topic"
        )

        self.assertEqual(
            [
                item["id"]
                for item in result["evidence"]
            ],
            ["curriculum-1", "schedule-1"],
        )
        self.assertEqual(
            [
                item["evidence_count"]
                for item in result["retrieval_results"]
            ],
            [2, 2],
        )

    @patch.object(
        briefing_service,
        "retrieve_question_evidence",
    )
    @patch.object(
        briefing_service,
        "create_briefing_plan",
    )
    def test_duplicate_evidence_is_included_once(
        self,
        create_plan,
        retrieve_evidence,
    ):
        duplicate = {
            "id": "shared-evidence",
            "source": "source-one",
            "location": "Slide 8",
        }
        create_plan.return_value = {
            "briefing_title": "Test Briefing",
            "retrieval_questions": [
                {
                    "category": "curriculum",
                    "question": "First question",
                },
                {
                    "category": "dates",
                    "question": "Second question",
                },
            ],
        }
        retrieve_evidence.side_effect = [
            ({}, [duplicate]),
            ({}, [{**duplicate}]),
        ]

        result = briefing_service.gather_briefing_evidence(
            "Test topic"
        )

        self.assertEqual(
            result["evidence"],
            [duplicate],
        )

    @patch.object(
        briefing_service,
        "enrich_evidence_sources",
    )
    @patch.object(
        briefing_service,
        "generate_study_briefing",
    )
    @patch.object(
        briefing_service,
        "gather_briefing_evidence",
    )
    def test_create_study_briefing_returns_complete_result(
        self,
        gather_evidence,
        generate_briefing,
        enrich_sources,
    ):
        raw_evidence = [
            {
                "source": "source-one",
                "location": "Slide 8",
                "text": "Evidence",
            }
        ]
        retrieval_results = [
            {
                "category": "curriculum",
                "question": "Question",
                "query_plan": {},
                "evidence_count": 1,
            }
        ]
        briefing = {
            "title": "Test Briefing",
            "overview": "Overview",
            "verified_facts": [],
            "recommended_actions": [],
            "open_questions": [],
        }
        reference_map = {
            "E1": {
                "source": "source-one",
                "location": "Slide 8",
                "heading": None,
            }
        }
        display_evidence = [
            {
                **raw_evidence[0],
                "source_metadata": {
                    "display_name": "Source One"
                },
            }
        ]
        gather_evidence.return_value = {
            "topic": "Test topic",
            "briefing_title": "Test Briefing",
            "retrieval_results": retrieval_results,
            "evidence": raw_evidence,
        }
        generate_briefing.return_value = {
            "briefing": briefing,
            "evidence_reference_map": reference_map,
        }
        enrich_sources.return_value = display_evidence

        result = briefing_service.create_study_briefing(
            "Test topic"
        )

        generate_briefing.assert_called_once_with(
            topic="Test topic",
            briefing_title="Test Briefing",
            evidence=raw_evidence,
        )
        enrich_sources.assert_called_once_with(
            raw_evidence
        )
        self.assertEqual(result["briefing"], briefing)
        self.assertEqual(
            result["evidence_reference_map"],
            reference_map,
        )
        self.assertEqual(
            result["retrieval_results"],
            retrieval_results,
        )
        self.assertEqual(
            result["evidence"],
            display_evidence,
        )


if __name__ == "__main__":
    unittest.main()
