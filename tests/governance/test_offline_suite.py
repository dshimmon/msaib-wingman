"""Regression checks for credential-free offline test discovery."""

import os
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class OfflineSuiteTests(unittest.TestCase):
    def _run_isolated_import(self, environment):
        return subprocess.run(
            [
                sys.executable,
                "-c",
                textwrap.dedent(
                    """
                    import os

                    expected = os.environ.pop("EXPECTED_OPENAI_API_KEY")
                    expect_missing = os.environ.pop("EXPECT_MISSING") == "1"
                    expect_dotenv_missing = (
                        os.environ.pop("EXPECT_DOTENV_MISSING") == "1"
                    )
                    if expect_missing:
                        assert "OPENAI_API_KEY" not in os.environ
                    if expect_dotenv_missing:
                        assert "PYTHON_DOTENV_DISABLED" not in os.environ

                    import tests
                    import tests.products.atlas.test_briefing_generator

                    assert os.environ["OPENAI_API_KEY"] == expected
                    assert os.environ["PYTHON_DOTENV_DISABLED"] == "1"
                    """
                ),
            ],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_formerly_failing_import_needs_no_real_credential(self):
        environment = os.environ.copy()
        environment.pop("OPENAI_API_KEY", None)
        environment.pop("PYTHON_DOTENV_DISABLED", None)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["EXPECTED_OPENAI_API_KEY"] = (
            "wingman-offline-tests-no-credential"
        )
        environment["EXPECT_MISSING"] = "1"
        environment["EXPECT_DOTENV_MISSING"] = "1"

        result = self._run_isolated_import(environment)

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_test_package_preserves_caller_supplied_value(self):
        environment = os.environ.copy()
        environment["OPENAI_API_KEY"] = "caller-supplied-test-value"
        environment["PYTHON_DOTENV_DISABLED"] = "1"
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["EXPECTED_OPENAI_API_KEY"] = "caller-supplied-test-value"
        environment["EXPECT_MISSING"] = "0"
        environment["EXPECT_DOTENV_MISSING"] = "0"

        result = self._run_isolated_import(environment)

        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
