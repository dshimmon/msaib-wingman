"""CLI preview and execution-boundary tests for folder ingestion."""

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import bulk_ingestion  # noqa: E402


class BulkIngestionCliTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        (self.root / "b.txt").write_text("B", encoding="utf-8")
        (self.root / "a.md").write_text("# A", encoding="utf-8")

    def test_default_command_is_preview_only_and_deterministic(self):
        output = io.StringIO()
        with (
            patch.object(bulk_ingestion, "execute_batch") as execute,
            redirect_stdout(output),
        ):
            self.assertEqual(
                bulk_ingestion.main([str(self.root), "--course-id", "AI-101"]),
                0,
            )
        execute.assert_not_called()
        rendered = output.getvalue()
        self.assertLess(rendered.index("a.md"), rendered.index("b.txt"))
        self.assertIn("Preview only", rendered)

    def test_execute_uses_same_preview_plan_and_explicit_context(self):
        fake_result = {
            "manifest": {
                "files": [],
            },
            "manifest_path": "manifest.json",
            "report_path": "manifest.md",
        }
        with (
            patch.object(
                bulk_ingestion,
                "execute_batch",
                return_value=fake_result,
            ) as execute,
            patch.object(
                bulk_ingestion,
                "report_counts",
                return_value={
                    "succeeded": 2,
                    "skipped": 0,
                    "duplicate": 0,
                    "needs_ocr": 0,
                    "failed": 0,
                },
            ),
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(
                bulk_ingestion.main(
                    [
                        str(self.root),
                        "--course-id",
                        "AI-101",
                        "--course-override",
                        "b.txt=AI-202",
                        "--execute",
                    ]
                ),
                0,
            )
        plan = execute.call_args.args[0]
        self.assertTrue(plan.manifest["assignments_confirmed"])
        self.assertEqual(plan.manifest["files"][1]["course_id"], "AI-202")
        self.assertEqual(
            execute.call_args.kwargs["product_context"].product_id,
            "atlas",
        )

    def test_resume_and_retry_flags_are_bounded(self):
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                bulk_ingestion.main([str(self.root), "--resume"])
            with self.assertRaises(SystemExit):
                bulk_ingestion.main([str(self.root), "--retry-failed"])


if __name__ == "__main__":
    unittest.main()
