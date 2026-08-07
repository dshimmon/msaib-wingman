"""Focused tests for the product-neutral prompt optimizer."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from prompt_optimizer import (  # noqa: E402
    PROMPT_OPTIMIZER_INSTRUCTIONS,
    PROMPT_OPTIMIZER_MODEL,
    optimize_prompt,
)
from airframe_manifest import CORE, MODULE_OWNERS  # noqa: E402
from product_config import ATLAS_PRODUCT  # noqa: E402
from product_contract import ProductCapability  # noqa: E402


APP_PATH = ROOT / "src" / "streamlit_app.py"
PROMPT_OPTIMIZER_LABEL = "Prompt Optimizer"
OPTIMIZED_PROMPT = (
    "Act as a launch strategist. Create a concise product launch plan."
)


class PromptOptimizerTests(unittest.TestCase):
    def create_client(self, output_text):
        client = Mock()
        client.responses.create.return_value = SimpleNamespace(
            output_text=output_text
        )
        return client

    def test_optimizes_trimmed_prompt_with_bounded_instructions(self):
        client = self.create_client(
            "Act as a launch strategist. Create a launch plan."
        )

        result = optimize_prompt(
            "  Make a launch plan  ",
            response_client=client,
        )

        self.assertEqual(
            result,
            "Act as a launch strategist. Create a launch plan.",
        )
        client.responses.create.assert_called_once_with(
            model=PROMPT_OPTIMIZER_MODEL,
            instructions=PROMPT_OPTIMIZER_INSTRUCTIONS,
            input="Make a launch plan",
        )
        self.assertIn("Do not answer the prompt", PROMPT_OPTIMIZER_INSTRUCTIONS)
        self.assertIn("preserving", PROMPT_OPTIMIZER_INSTRUCTIONS)

    def test_rejects_missing_prompt_without_calling_ai(self):
        client = self.create_client("unused")

        for prompt in ("", "   "):
            with self.subTest(prompt=prompt):
                with self.assertRaisesRegex(ValueError, "Enter a prompt"):
                    optimize_prompt(prompt, response_client=client)

        client.responses.create.assert_not_called()

    def test_rejects_non_text_prompt_without_calling_ai(self):
        client = self.create_client("unused")

        with self.assertRaisesRegex(TypeError, "must be text"):
            optimize_prompt(None, response_client=client)

        client.responses.create.assert_not_called()

    def test_rejects_empty_ai_response(self):
        for output_text in ("   ", None):
            with self.subTest(output_text=output_text):
                client = self.create_client(output_text)

                with self.assertRaisesRegex(
                    RuntimeError,
                    "empty optimized prompt",
                ):
                    optimize_prompt(
                        "Improve this",
                        response_client=client,
                    )


class PromptOptimizerUITests(unittest.TestCase):
    def assert_no_app_exception(self, app):
        self.assertEqual(
            [exception.message for exception in app.exception],
            [],
        )

    def find_button(self, app, label):
        return next(
            button
            for button in app.button
            if button.label == label
        )

    def open_prompt_optimizer(self):
        app = AppTest.from_file(
            APP_PATH,
            default_timeout=10,
        ).run()
        self.assert_no_app_exception(app)
        self.assertEqual(
            app.radio[0].options,
            [
                ATLAS_PRODUCT.chat_label,
                ATLAS_PRODUCT.briefing_label,
                ATLAS_PRODUCT.library_label,
                PROMPT_OPTIMIZER_LABEL,
            ],
        )

        app.radio[0].set_value(PROMPT_OPTIMIZER_LABEL).run()
        self.assert_no_app_exception(app)
        self.assertEqual(app.title[0].value, PROMPT_OPTIMIZER_LABEL)
        return app

    def optimize(self, app, source_prompt):
        app.text_area[0].set_value(source_prompt).run()
        self.assert_no_app_exception(app)
        self.find_button(app, "Optimize Prompt").click().run()
        self.assert_no_app_exception(app)
        return app

    def test_navigation_and_prompt_button_states(self):
        app = self.open_prompt_optimizer()

        self.assertTrue(
            self.find_button(app, "Optimize Prompt").disabled
        )

        app.text_area[0].set_value("  Draft a launch plan  ").run()

        self.assert_no_app_exception(app)
        self.assertFalse(
            self.find_button(app, "Optimize Prompt").disabled
        )

    @patch("prompt_optimizer.optimize_prompt", return_value=OPTIMIZED_PROMPT)
    def test_success_displays_result_and_returns_it_to_editor(self, optimizer):
        app = self.open_prompt_optimizer()
        self.optimize(app, "Draft a launch plan")

        optimizer.assert_called_once_with("Draft a launch plan")
        self.assertEqual(
            [element.value for element in app.get("code")],
            [OPTIMIZED_PROMPT],
        )

        self.find_button(app, "Edit Optimized Prompt").click().run()

        self.assert_no_app_exception(app)
        self.assertEqual(app.text_area[0].value, OPTIMIZED_PROMPT)
        self.assertEqual(list(app.get("code")), [])

    @patch("prompt_optimizer.optimize_prompt", return_value=OPTIMIZED_PROMPT)
    def test_prompt_change_invalidates_stale_output(self, optimizer):
        app = self.open_prompt_optimizer()
        self.optimize(app, "Draft a launch plan")
        self.assertEqual(len(app.get("code")), 1)

        app.text_area[0].set_value("Draft a hiring plan").run()

        self.assert_no_app_exception(app)
        self.assertEqual(list(app.get("code")), [])
        self.assertFalse(
            any(
                button.label == "Edit Optimized Prompt"
                for button in app.button
            )
        )
        optimizer.assert_called_once_with("Draft a launch plan")

    @patch(
        "prompt_optimizer.optimize_prompt",
        side_effect=(OPTIMIZED_PROMPT, RuntimeError("offline failure")),
    )
    def test_failed_retry_clears_prior_result(self, optimizer):
        app = self.open_prompt_optimizer()
        self.optimize(app, "Draft a launch plan")
        self.assertEqual(len(app.get("code")), 1)

        self.find_button(app, "Optimize Prompt").click().run()

        self.assert_no_app_exception(app)
        self.assertEqual(list(app.get("code")), [])
        self.assertEqual(
            [error.value for error in app.error],
            [
                "The prompt could not be optimized: "
                "offline failure"
            ],
        )
        self.assertEqual(optimizer.call_count, 2)

    def test_global_shell_tool_does_not_expand_product_contract_v1(self):
        product_workspace_labels = (
            ATLAS_PRODUCT.chat_label,
            ATLAS_PRODUCT.briefing_label,
            ATLAS_PRODUCT.library_label,
        )

        self.assertNotIn(
            PROMPT_OPTIMIZER_LABEL,
            product_workspace_labels,
        )
        self.assertNotIn(
            "prompt_optimizer",
            {capability.value for capability in ProductCapability},
        )
        self.assertEqual(MODULE_OWNERS["prompt_optimizer"], CORE)


if __name__ == "__main__":
    unittest.main()
