# Tests deterministic and general study-briefing planning.

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIRECTORY = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIRECTORY))

import briefing_planner


class BriefingPlannerTests(unittest.TestCase):
    @patch.object(
        briefing_planner.client.responses,
        "create",
    )
    def test_fall_module_a_plan_is_deterministic(
        self,
        create_response,
    ):
        plan = briefing_planner.create_briefing_plan(
            "Prepare me for Fall Module A"
        )

        self.assertEqual(
            [
                item["category"]
                for item in plan["retrieval_questions"]
            ],
            [
                "curriculum",
                "schedule",
                "dates",
                "preparation",
                "technology",
            ],
        )
        create_response.assert_not_called()

    def test_module_plan_uses_exact_preparation_question(
        self,
    ):
        plan = (
            briefing_planner.create_module_briefing_plan(
                "Prepare me for Fall Module A"
            )
        )
        preparation_query = next(
            item
            for item in plan["retrieval_questions"]
            if item["category"] == "preparation"
        )

        self.assertEqual(
            preparation_query["question"],
            "Summer Work",
        )

    @patch.object(
        briefing_planner.client.responses,
        "create",
    )
    def test_general_request_uses_llm_planner(
        self,
        create_response,
    ):
        expected_plan = {
            "briefing_title": "Orientation Briefing",
            "retrieval_questions": [
                {
                    "category": "policies",
                    "question": (
                        "What orientation policies are documented?"
                    ),
                }
            ],
        }
        create_response.return_value = SimpleNamespace(
            output_text=json.dumps(expected_plan)
        )

        result = briefing_planner.create_briefing_plan(
            "Prepare me for orientation"
        )

        create_response.assert_called_once()
        self.assertEqual(result, expected_plan)


if __name__ == "__main__":
    unittest.main()
