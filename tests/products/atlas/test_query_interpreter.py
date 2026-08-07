# Tests query interpretation with conversation context.

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIRECTORY = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIRECTORY))

import products.atlas.query_interpreter as query_interpreter


class QueryInterpreterTests(unittest.TestCase):
    def make_response(self, retrieval_plan):
        return SimpleNamespace(
            output_text=json.dumps(retrieval_plan)
        )

    def test_bare_topic_without_context_is_deterministic(self):
        with patch.object(
            query_interpreter.client.responses,
            "create",
        ) as create_response:
            result = query_interpreter.interpret_query(
                "Orientation"
            )

        create_response.assert_not_called()
        self.assertEqual(
            result,
            {
                "memory_search_terms": [],
                "text_search_terms": ["Orientation"],
                "record_types": [],
                "record_filters": [],
            },
        )

    def test_short_follow_up_with_context_calls_openai(self):
        plan = {
            "memory_search_terms": [],
            "text_search_terms": [],
            "record_types": ["course_schedule"],
            "record_filters": [
                {"field": "day", "value": "Tuesday"}
            ],
        }
        context = [
            {
                "user_question": "What classes are in fall?",
                "evidence": [
                    {
                        "source": "curriculum-source",
                        "location": "Slide 8",
                        "text_excerpt": "Fall courses",
                    }
                ],
            }
        ]

        with patch.object(
            query_interpreter.client.responses,
            "create",
            return_value=self.make_response(plan),
        ) as create_response:
            result = query_interpreter.interpret_query(
                "Tuesday?",
                conversation_context=context,
            )

        create_response.assert_called_once()
        self.assertEqual(result, plan)

    def test_prompt_contains_context_and_fresh_evidence_rules(
        self,
    ):
        plan = {
            "memory_search_terms": [],
            "text_search_terms": ["Tuesday"],
            "record_types": [],
            "record_filters": [],
        }
        context = [
            {
                "user_question": "Previous question",
                "evidence": [
                    {
                        "source": "source-one",
                        "location": "Slide 8",
                        "text_excerpt": "Grounded excerpt",
                    }
                ],
            }
        ]

        with patch.object(
            query_interpreter.client.responses,
            "create",
            return_value=self.make_response(plan),
        ) as create_response:
            query_interpreter.interpret_query(
                "Which of those?",
                conversation_context=context,
            )

        prompt = (
            create_response.call_args.kwargs["input"]
        )
        self.assertIn(
            '"user_question": "Previous question"',
            prompt,
        )
        self.assertIn('"source": "source-one"', prompt)
        self.assertIn(
            '"text_excerpt": "Grounded excerpt"',
            prompt,
        )
        self.assertIn(
            "Prior assistant wording is not provided",
            prompt,
        )
        self.assertIn(
            "must always retrieve fresh Wingman evidence",
            prompt,
        )
        self.assertIn(
            "User question:\nWhich of those?",
            prompt,
        )

    def test_self_contained_question_with_context_is_parsed(
        self,
    ):
        plan = {
            "memory_search_terms": [],
            "text_search_terms": [
                "Laptop requirements"
            ],
            "record_types": [],
            "record_filters": [],
        }
        context = [
            {
                "user_question": "What classes are in fall?",
                "evidence": [],
            }
        ]

        with patch.object(
            query_interpreter.client.responses,
            "create",
            return_value=self.make_response(plan),
        ) as create_response:
            result = query_interpreter.interpret_query(
                (
                    "What kind of computer do I need "
                    "for the program?"
                ),
                conversation_context=context,
            )

        create_response.assert_called_once()
        self.assertEqual(result, plan)


if __name__ == "__main__":
    unittest.main()
