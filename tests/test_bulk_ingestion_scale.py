"""Blocking 100-document real-orchestration offline validation."""

import unittest

from tools.bulk_ingestion_soak import run_offline_batch


class BulkIngestionScaleTests(unittest.TestCase):
    def test_one_hundred_mixed_documents_with_resume_retry_and_retrieval(self):
        summary = run_offline_batch(100, include_edge_cases=True)

        self.assertEqual(summary["document_count"], 100)
        self.assertEqual(summary["first_counts"]["failed"], 1)
        self.assertEqual(summary["final_counts"]["failed"], 0)
        self.assertEqual(summary["final_counts"]["duplicate"], 1)
        self.assertEqual(summary["final_counts"]["skipped"], 2)
        self.assertEqual(summary["final_counts"]["needs_ocr"], 1)
        self.assertEqual(sum(summary["final_counts"].values()), 100)
        self.assertEqual(summary["possible_revision_count"], 1)
        self.assertGreaterEqual(summary["resumed_attempt_count"], 2)
        self.assertEqual(summary["retry_attempt_count"], 2)
        self.assertTrue(summary["failed_artifacts_absent"])
        self.assertTrue(summary["no_text_artifacts_absent"])
        self.assertFalse(summary["cleanup_failure_stopped_batch"])
        self.assertGreater(summary["course_counts"]["AI-101"], 0)
        self.assertEqual(summary["course_counts"]["AI-202"], 1)
        self.assertIn(
            "baseline-source",
            summary["retrieval_before"]["source_ids"],
        )
        self.assertIn(
            "baseline-source",
            summary["retrieval_after"]["source_ids"],
        )
        self.assertGreater(summary["retrieval_after"]["evidence_count"], 1)
        self.assertTrue(
            any(
                source_id != "baseline-source"
                for source_id in summary["retrieval_after"]["source_ids"]
            )
        )


if __name__ == "__main__":
    unittest.main()
