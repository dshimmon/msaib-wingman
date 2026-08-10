"""Deterministic safety tests for external Crew Chief report retention."""

from __future__ import annotations

import json
import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from tools.crew_chief.__main__ import main
from tools.crew_chief.core import CrewChiefError, read_json, write_canonical_json
from tools.crew_chief.retention import (
    DEFAULT_MAX_RETAINED_REPORTS,
    DEFAULT_RETENTION_DAYS,
    REPORT_METADATA,
    RETENTION_STATE,
    initialize_retention_root,
    prune_reports,
    validate_report_id,
    write_report_metadata,
)


NOW = datetime(2026, 8, 10, 18, 0, tzinfo=timezone.utc)


class CrewChiefRetentionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / "retention"
        self.root.mkdir()
        initialize_retention_root(self.root)

    def tearDown(self):
        self.temporary.cleanup()

    def bundle(
        self,
        report_id: str,
        *,
        completed_at: datetime | None,
        state: str = "completed",
        report_kind: str = "audit",
    ) -> Path:
        bundle = self.root / "reports" / report_id
        bundle.mkdir(parents=True)
        if state == "completed":
            if report_kind == "audit":
                write_canonical_json(bundle / "crew-chief-report.json", {})
                write_canonical_json(bundle / "run-record.json", {})
                (bundle / "codex-stderr.log").write_text(
                    "fixture diagnostic\n", encoding="utf-8"
                )
                (bundle / "temporary-output.txt").write_text(
                    "fixture output\n", encoding="utf-8"
                )
            else:
                write_canonical_json(bundle / "pool-report.json", {})
        write_report_metadata(
            self.root,
            bundle,
            report_id=report_id,
            report_kind=report_kind,
            state=state,
            created_at=NOW - timedelta(days=60),
            completed_at=completed_at,
        )
        return bundle

    def prune(self, **kwargs):
        return prune_reports(self.root, clock=lambda: NOW, **kwargs)

    def test_default_limits_are_thirty_days_and_one_hundred_reports(self):
        self.assertEqual(DEFAULT_RETENTION_DAYS, 30)
        self.assertEqual(DEFAULT_MAX_RETAINED_REPORTS, 100)

    def test_age_uses_validated_completion_time_and_removes_complete_bundle(self):
        old = self.bundle("old", completed_at=NOW - timedelta(days=31))
        recent = self.bundle("recent", completed_at=NOW - timedelta(days=29))
        current_mtime = NOW.timestamp()
        for path in old.rglob("*"):
            if path.is_file():
                os.utime(path, (current_mtime, current_mtime))
        result = self.prune(retention_days=30, max_retained_reports=100)
        self.assertEqual(
            [(item["report_id"], item["reasons"]) for item in result["candidates"]],
            [("old", ["age"])],
        )
        self.assertFalse(old.exists())
        self.assertTrue(recent.is_dir())

    def test_count_retains_newest_completed_reports(self):
        oldest = self.bundle("oldest", completed_at=NOW - timedelta(days=3))
        middle = self.bundle("middle", completed_at=NOW - timedelta(days=2))
        newest = self.bundle("newest", completed_at=NOW - timedelta(days=1))
        result = self.prune(retention_days=30, max_retained_reports=2)
        self.assertEqual(result["candidates"][0]["report_id"], "oldest")
        self.assertFalse(oldest.exists())
        self.assertTrue(middle.exists())
        self.assertTrue(newest.exists())

    def test_age_and_count_thresholds_apply_together(self):
        old = self.bundle("age-expired", completed_at=NOW - timedelta(days=31))
        count_oldest = self.bundle(
            "count-oldest", completed_at=NOW - timedelta(days=3)
        )
        recent = self.bundle("recent", completed_at=NOW - timedelta(days=2))
        newest = self.bundle("newest", completed_at=NOW - timedelta(days=1))
        result = self.prune(retention_days=30, max_retained_reports=2)
        self.assertEqual(
            [(item["report_id"], item["reasons"]) for item in result["candidates"]],
            [("age-expired", ["age"]), ("count-oldest", ["count"])],
        )
        self.assertFalse(old.exists())
        self.assertFalse(count_oldest.exists())
        self.assertTrue(recent.exists())
        self.assertTrue(newest.exists())

    def test_count_tie_breaks_stably_by_report_id(self):
        completed = NOW - timedelta(days=1)
        bundles = {
            report_id: self.bundle(report_id, completed_at=completed)
            for report_id in ("charlie", "alpha", "bravo")
        }
        result = self.prune(retention_days=30, max_retained_reports=2)
        self.assertEqual(result["candidates"][0]["report_id"], "alpha")
        self.assertFalse(bundles["alpha"].exists())
        self.assertTrue(bundles["bravo"].exists())
        self.assertTrue(bundles["charlie"].exists())

    def test_queued_and_running_reports_are_never_candidates(self):
        queued = self.bundle("queued", completed_at=None, state="queued")
        running = self.bundle("running", completed_at=None, state="running")
        completed = self.bundle(
            "completed", completed_at=NOW - timedelta(days=31)
        )
        result = self.prune(retention_days=30, max_retained_reports=1)
        self.assertEqual(result["active_report_count"], 2)
        self.assertFalse(completed.exists())
        self.assertTrue(queued.exists())
        self.assertTrue(running.exists())

    def test_repository_and_outside_root_paths_are_rejected(self):
        repository = self.base / "repository"
        (repository / ".git").mkdir(parents=True)
        output = repository / "output"
        output.mkdir()
        with self.assertRaisesRegex(CrewChiefError, "Git repository"):
            initialize_retention_root(output)

        old = self.bundle("old", completed_at=NOW - timedelta(days=31))
        outside = self.base / "outside"
        outside.mkdir()
        (outside / "preserve.txt").write_text("preserve\n", encoding="utf-8")
        metadata = read_json(old / REPORT_METADATA)
        metadata["bundle_path"] = "../outside"
        write_canonical_json(old / REPORT_METADATA, metadata)
        with self.assertRaisesRegex(CrewChiefError, "mismatched"):
            self.prune(retention_days=30, max_retained_reports=100)
        self.assertTrue(old.exists())
        self.assertEqual(
            (outside / "preserve.txt").read_text(encoding="utf-8"),
            "preserve\n",
        )

    def test_symlink_anywhere_in_output_root_is_rejected_before_deletion(self):
        old = self.bundle("old", completed_at=NOW - timedelta(days=31))
        outside = self.base / "outside.txt"
        outside.write_text("preserve\n", encoding="utf-8")
        (self.root / "linked-output").symlink_to(outside)
        with self.assertRaisesRegex(CrewChiefError, "symlink"):
            self.prune(retention_days=30, max_retained_reports=100)
        self.assertTrue(old.exists())
        self.assertEqual(outside.read_text(encoding="utf-8"), "preserve\n")

    def test_malformed_metadata_aborts_before_any_bundle_is_removed(self):
        old = self.bundle("old", completed_at=NOW - timedelta(days=31))
        malformed = self.root / "reports" / "malformed"
        malformed.mkdir()
        (malformed / REPORT_METADATA).write_text("{broken", encoding="utf-8")
        with self.assertRaises(CrewChiefError):
            self.prune(retention_days=30, max_retained_reports=100)
        self.assertTrue(old.exists())

    def test_completion_timestamp_cannot_precede_creation(self):
        bundle = self.bundle(
            "reversed-time", completed_at=NOW - timedelta(days=1)
        )
        metadata = read_json(bundle / REPORT_METADATA)
        metadata["created_at"] = NOW.isoformat().replace("+00:00", "Z")
        write_canonical_json(bundle / REPORT_METADATA, metadata)
        with self.assertRaisesRegex(CrewChiefError, "precedes creation"):
            self.prune(retention_days=30, max_retained_reports=100)
        self.assertTrue(bundle.exists())

    def test_dry_run_reports_candidates_without_deleting_or_writing_state(self):
        old = self.bundle("old", completed_at=NOW - timedelta(days=31))
        result = self.prune(
            retention_days=30, max_retained_reports=100, dry_run=True
        )
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["remove_count"], 1)
        self.assertTrue(old.exists())
        self.assertFalse((self.root / RETENTION_STATE).exists())

    def test_retention_state_is_bounded_and_replaced_on_each_cleanup(self):
        self.bundle("old", completed_at=NOW - timedelta(days=31))
        self.prune(retention_days=30, max_retained_reports=100)
        state_path = self.root / RETENTION_STATE
        first_size = state_path.stat().st_size
        first = read_json(state_path)
        self.assertEqual(
            set(first),
            {
                "schema_version",
                "retention_days",
                "max_retained_reports",
                "current_retained_count",
                "last_cleanup_time",
                "removed_during_last_cleanup",
            },
        )
        self.assertEqual(first["removed_during_last_cleanup"], 1)
        self.prune(retention_days=30, max_retained_reports=100)
        second = read_json(state_path)
        self.assertEqual(second["removed_during_last_cleanup"], 0)
        self.assertLessEqual(state_path.stat().st_size, first_size + 16)
        self.assertNotIn("history", json.dumps(second))

    def test_root_symlink_and_ambiguous_root_are_rejected(self):
        target = self.base / "target"
        target.mkdir()
        link = self.base / "root-link"
        link.symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(CrewChiefError, "symlink"):
            initialize_retention_root(link)
        with self.assertRaisesRegex(CrewChiefError, "ambiguous"):
            initialize_retention_root(self.base / "part" / ".." / "target")

    def test_malformed_report_identifier_is_rejected(self):
        for report_id in ("", "../escape", "nested/report", " leading"):
            with self.subTest(report_id=report_id):
                with self.assertRaisesRegex(CrewChiefError, "ID is malformed"):
                    validate_report_id(report_id)

    def test_cli_exposes_configurable_dry_run(self):
        expected = {"dry_run": True, "candidates": []}
        with (
            mock.patch(
                "tools.crew_chief.__main__.prune_reports",
                return_value=expected,
            ) as prune,
            redirect_stdout(io.StringIO()),
        ):
            exit_code = main(
                [
                    "retention",
                    str(self.root),
                    "--retention-days",
                    "7",
                    "--max-retained-reports",
                    "9",
                    "--dry-run",
                ]
            )
        self.assertEqual(exit_code, 0)
        prune.assert_called_once_with(
            self.root,
            retention_days=7,
            max_retained_reports=9,
            dry_run=True,
        )


if __name__ == "__main__":
    unittest.main()
