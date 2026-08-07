# Tests structured source-grounded briefing generation.

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIRECTORY = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIRECTORY))

import products.atlas.briefing_generator as briefing_generator


class BriefingGeneratorTests(unittest.TestCase):
    def test_evidence_catalog_has_stable_references(self):
        evidence = [
            {
                "source": "curriculum-source",
                "location": "Slide 8",
                "heading": "Curriculum",
                "domain": "Academics",
                "text": "Curriculum evidence",
            },
            {
                "source": "schedule-source",
                "location": "Slide 11",
                "heading": "Schedule",
                "domain": "Academics",
                "text": "Schedule evidence",
            },
        ]

        reference_map, catalog = (
            briefing_generator.build_evidence_catalog(
                evidence
            )
        )

        self.assertEqual(
            reference_map,
            {
                "E1": {
                    "source": "curriculum-source",
                    "location": "Slide 8",
                    "heading": "Curriculum",
                },
                "E2": {
                    "source": "schedule-source",
                    "location": "Slide 11",
                    "heading": "Schedule",
                },
            },
        )
        self.assertIn("Evidence Reference: E1", catalog)
        self.assertIn("Evidence Reference: E2", catalog)

    @patch.object(
        briefing_generator.client.responses,
        "create",
    )
    def test_generator_schema_restricts_evidence_references(
        self,
        create_response,
    ):
        generated_briefing = {
            "title": "Test Briefing",
            "overview": "Overview",
            "verified_facts": [
                {
                    "category": "Curriculum",
                    "fact": "Verified fact",
                    "evidence_refs": ["E1"],
                }
            ],
            "recommended_actions": [
                {
                    "priority": "High",
                    "action": "Review",
                    "rationale": "Based on evidence",
                    "evidence_refs": ["E2"],
                }
            ],
            "open_questions": [],
        }
        create_response.return_value = SimpleNamespace(
            output_text=json.dumps(generated_briefing)
        )
        evidence = [
            {
                "source": "source-one",
                "location": "Slide 8",
                "heading": "First",
                "text": "First evidence",
            },
            {
                "source": "source-two",
                "location": "Slide 11",
                "heading": "Second",
                "text": "Second evidence",
            },
        ]

        result = (
            briefing_generator.generate_study_briefing(
                topic="Test",
                briefing_title="Test Briefing",
                evidence=evidence,
            )
        )

        schema = (
            create_response.call_args.kwargs["text"]
            ["format"]["schema"]
        )
        properties = schema["properties"]
        fact_reference_schema = (
            properties["verified_facts"]["items"]
            ["properties"]["evidence_refs"]["items"]
        )
        action_reference_schema = (
            properties["recommended_actions"]["items"]
            ["properties"]["evidence_refs"]["items"]
        )

        self.assertEqual(
            fact_reference_schema["enum"],
            ["E1", "E2"],
        )
        self.assertEqual(
            action_reference_schema["enum"],
            ["E1", "E2"],
        )
        self.assertEqual(
            result["briefing"],
            generated_briefing,
        )

    @patch.object(
        briefing_generator.client.responses,
        "create",
    )
    def test_empty_evidence_returns_safe_response(
        self,
        create_response,
    ):
        result = (
            briefing_generator.generate_study_briefing(
                topic="Unknown topic",
                briefing_title="Unknown Briefing",
                evidence=[],
            )
        )

        create_response.assert_not_called()
        self.assertEqual(
            result["evidence_reference_map"],
            {},
        )
        self.assertEqual(
            result["briefing"]["verified_facts"],
            [],
        )
        self.assertEqual(
            result["briefing"]["recommended_actions"],
            [],
        )
        self.assertTrue(
            result["briefing"]["open_questions"]
        )


if __name__ == "__main__":
    unittest.main()
