"""Credential-free concurrency tests for the Crew Chief audit pool."""

from __future__ import annotations

import json
import subprocess
import tempfile
import threading
import time
import unittest
from datetime import timedelta
from pathlib import Path
from unittest import mock

from tests.governance.test_crew_chief import (
    FIXED_TIME,
    FixtureRepository,
    finding,
    report_for,
)
from tools.crew_chief.core import CrewChiefError, read_json, write_canonical_json
from tools.crew_chief.pool import pool_exit_code, run_pool
from tools.crew_chief.runner import (
    _REQUIRED_EXEC_FLAGS,
    CodexCapabilities,
)
from tools.crew_chief.service_schema import canonical_to_service_output
from tools.crew_chief.validation import validate_instance


class CrewChiefPoolTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        first_root = self.root / "first"
        second_root = self.root / "second"
        first_root.mkdir()
        second_root.mkdir()
        self.first = FixtureRepository(first_root)
        self.second = FixtureRepository(second_root)
        self.first_envelope = Path(
            self.first.prepare("envelope")["envelope_path"]
        )
        self.second_envelope = Path(
            self.second.prepare("envelope")["envelope_path"]
        )

    def tearDown(self):
        self.temporary.cleanup()

    def capabilities(self, selector=True):
        return CodexCapabilities(
            executable="/fixture/codex",
            version="codex-cli pool fixture",
            exec_flags=tuple(sorted(_REQUIRED_EXEC_FLAGS)),
            features=("shell_tool",),
            shell_tool_control=True,
            custom_agent_selector=selector,
        )

    def manifest(self, jobs, name="jobs.json"):
        path = self.root / name
        write_canonical_json(
            path,
            {
                "schema_version": "1.0",
                "jobs": jobs,
            },
        )
        return path

    def jobs(self):
        return [
            {
                "job_id": "first",
                "audit_envelope": str(self.first_envelope),
            },
            {
                "job_id": "second",
                "audit_envelope": str(self.second_envelope),
            },
        ]

    def model_runner(
        self, delays=None, failures=None, calls=None, verdicts=None
    ):
        delays = delays or {}
        failures = failures or set()
        calls = calls if calls is not None else []
        verdicts = verdicts or {}

        def run(arguments, **_kwargs):
            if arguments[-2:] == ["login", "status"]:
                return subprocess.CompletedProcess(arguments, 0, "logged in", "")
            workspace = Path(arguments[arguments.index("--cd") + 1])
            job_id = workspace.name
            calls.append(job_id)
            time.sleep(delays.get(job_id, 0))
            if job_id in failures:
                return subprocess.CompletedProcess(
                    arguments, 1, "", "seeded fake runner failure"
                )
            report_path = Path(
                arguments[arguments.index("--output-last-message") + 1]
            )
            envelope = read_json(workspace / "frozen/audit-envelope.json")
            canonical_schema = read_json(
                workspace / "schemas/crew-chief-canonical-report.schema.json"
            )
            self.assertTrue(report_path.parent.is_dir())
            verdict = verdicts.get(job_id, "PASS")
            findings = [finding()] if verdict == "FAIL" else []
            report_path.write_text(
                json.dumps(
                    canonical_to_service_output(
                        report_for(envelope, findings, verdict=verdict),
                        canonical_schema,
                    )
                ),
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(
                arguments, 0, "", "tokens used\n42\n"
            )

        return run

    def test_preparation_defaults_to_two_and_uses_isolated_non_git_workspaces(self):
        report = run_pool(
            self.manifest(self.jobs()),
            self.root / "pool-output",
            detector=lambda _: self.capabilities(),
            clock=lambda: FIXED_TIME,
        )
        self.assertEqual(report["overall_status"], "PREPARED")
        self.assertEqual(report["requested_max_concurrency"], 2)
        self.assertEqual(report["effective_max_concurrency"], 2)
        self.assertEqual(report["maximum_observed_concurrency"], 0)
        self.assertEqual(report["queue_policy"], "bounded-input-order")
        self.assertEqual(report["automatic_retries"], 0)
        self.assertEqual([item["job_id"] for item in report["jobs"]], [
            "first",
            "second",
        ])
        self.assertEqual([item["state"] for item in report["jobs"]], [
            "QUEUED",
            "QUEUED",
        ])
        for item in report["jobs"]:
            workspace = Path(item["workspace"])
            self.assertFalse((workspace / ".git").exists())
            invocation = read_json(workspace / "invocation.json")
            self.assertIn("--skip-git-repo-check", invocation["argv"])
            self.assertEqual(
                invocation["argv"][invocation["argv"].index("--agent") + 1],
                "crew_chief",
            )
        validate_instance("pool-report-v1.schema.json", report)
        self.assertEqual(pool_exit_code(report), 0)

    def test_concurrency_is_bounded_queued_and_report_order_is_stable(self):
        jobs = []
        for index in range(5):
            jobs.append(
                {
                    "job_id": f"job-{index}",
                    "audit_envelope": str(
                        self.first_envelope
                        if index % 2 == 0
                        else self.second_envelope
                    ),
                }
            )
        report = run_pool(
            self.manifest(jobs),
            self.root / "pool-output",
            max_concurrency=2,
            execute=True,
            detector=lambda _: self.capabilities(),
            process_runner=self.model_runner(
                delays={"job-0": 0.08, "job-1": 0.01}
            ),
            clock=lambda: FIXED_TIME,
        )
        self.assertEqual(report["overall_status"], "PASS")
        self.assertEqual(report["maximum_observed_concurrency"], 2)
        self.assertEqual(
            [item["job_id"] for item in report["jobs"]],
            [f"job-{index}" for index in range(5)],
        )
        self.assertTrue(
            all(item["state"] == "COMPLETED" for item in report["jobs"])
        )
        self.assertTrue(all(item["verdict"] == "PASS" for item in report["jobs"]))
        self.assertTrue(all(item["token_count"] == 42 for item in report["jobs"]))
        self.assertEqual(report["automatic_retries"], 0)
        self.assertTrue(all(item["attempts"] == 1 for item in report["jobs"]))

    def test_audit_fail_verdict_is_an_operationally_completed_pool_job(self):
        report = run_pool(
            self.manifest(self.jobs()),
            self.root / "pool-output",
            max_concurrency=2,
            execute=True,
            detector=lambda _: self.capabilities(),
            process_runner=self.model_runner(
                delays={"first": 0.05, "second": 0.05},
                verdicts={"first": "FAIL", "second": "PASS"},
            ),
            clock=lambda: FIXED_TIME,
        )
        self.assertEqual(report["overall_status"], "PASS")
        self.assertEqual(report["maximum_observed_concurrency"], 2)
        self.assertEqual(
            [item["state"] for item in report["jobs"]],
            ["COMPLETED", "COMPLETED"],
        )
        self.assertEqual(
            [item["verdict"] for item in report["jobs"]],
            ["FAIL", "PASS"],
        )
        self.assertEqual(report["totals"]["verdict_fail"], 1)
        self.assertEqual(report["totals"]["verdict_pass"], 1)
        self.assertEqual(pool_exit_code(report), 0)
        for job_id in ("first", "second"):
            bundle = self.root / "pool-output" / "reports" / f"audit-{job_id}"
            self.assertTrue((bundle / "crew-chief-report.json").is_file())
            self.assertTrue((bundle / "run-record.json").is_file())
            self.assertTrue((bundle / "retention-report.json").is_file())
            self.assertTrue(
                (self.root / "pool-output" / job_id / ".crew-chief-consumed.json").is_file()
            )
        self.assertTrue(
            Path(report["report_path"]).parent.joinpath(
                "retention-report.json"
            ).is_file()
        )
        self.assertTrue(
            (self.root / "pool-output" / "retention-state.json").is_file()
        )

    def test_one_failure_does_not_cancel_other_jobs_or_retry(self):
        calls = []
        report = run_pool(
            self.manifest(self.jobs()),
            self.root / "pool-output",
            execute=True,
            detector=lambda _: self.capabilities(),
            process_runner=self.model_runner(failures={"first"}, calls=calls),
            clock=lambda: FIXED_TIME,
        )
        self.assertEqual(sorted(calls), ["first", "second"])
        self.assertEqual(len(calls), 2)
        self.assertEqual(report["overall_status"], "FAIL")
        self.assertEqual(report["jobs"][0]["state"], "FAILED")
        self.assertEqual(
            report["jobs"][0]["errors"][0]["category"], "CONTROL_FAILURE"
        )
        self.assertEqual(report["jobs"][1]["state"], "COMPLETED")
        self.assertEqual(report["jobs"][1]["verdict"], "PASS")
        self.assertEqual(pool_exit_code(report), 1)
        self.assertFalse(
            (self.root / "pool-output" / "retention-state.json").exists()
        )

    def test_fallback_authorization_is_scoped_per_job(self):
        jobs = self.jobs()
        jobs[0]["allow_fresh_session_fallback"] = True
        report = run_pool(
            self.manifest(jobs),
            self.root / "pool-output",
            execute=True,
            detector=lambda _: self.capabilities(selector=False),
            process_runner=self.model_runner(),
            clock=lambda: FIXED_TIME,
        )
        self.assertEqual(report["jobs"][0]["state"], "COMPLETED")
        self.assertEqual(report["jobs"][1]["state"], "FAILED")
        self.assertIn(
            "requires explicit authorization",
            report["jobs"][1]["errors"][0]["diagnostic"],
        )

    def test_structural_manifest_errors_prevent_every_launch(self):
        collision = str(self.root / "same-workspace")
        cases = {
            "empty": {"schema_version": "1.0", "jobs": []},
            "malformed": {"schema_version": "1.0", "jobs": "not-a-list"},
            "duplicate": {
                "schema_version": "1.0",
                "jobs": [self.jobs()[0], self.jobs()[0]],
            },
            "collision": {
                "schema_version": "1.0",
                "jobs": [
                    {**self.jobs()[0], "workspace": collision},
                    {**self.jobs()[1], "workspace": collision},
                ],
            },
        }
        for index, (label, manifest) in enumerate(cases.items()):
            with self.subTest(case=label):
                path = self.root / f"invalid-{index}.json"
                write_canonical_json(path, manifest)
                detector = mock.Mock(return_value=self.capabilities())
                output = self.root / f"invalid-output-{index}"
                with self.assertRaises(CrewChiefError):
                    run_pool(
                        path,
                        output,
                        detector=detector,
                        clock=lambda: FIXED_TIME,
                    )
                detector.assert_not_called()
                self.assertFalse(output.exists())

    def test_invalid_or_expired_envelope_prevents_every_launch(self):
        invalid = self.root / "invalid-envelope.json"
        invalid.write_text("{}\n", encoding="utf-8")
        cases = (
            (
                "invalid",
                [
                    self.jobs()[0],
                    {"job_id": "invalid", "audit_envelope": str(invalid)},
                ],
                FIXED_TIME,
            ),
            ("expired", self.jobs(), FIXED_TIME + timedelta(hours=2)),
        )
        for index, (label, jobs, now) in enumerate(cases):
            with self.subTest(case=label):
                detector = mock.Mock(return_value=self.capabilities())
                output = self.root / f"envelope-output-{index}"
                with self.assertRaises(CrewChiefError):
                    run_pool(
                        self.manifest(jobs, f"envelope-{index}.json"),
                        output,
                        execute=True,
                        detector=detector,
                        clock=lambda now=now: now,
                    )
                detector.assert_not_called()
                self.assertFalse(output.exists())

    def test_concurrency_range_is_enforced_before_capability_detection(self):
        for value in (0, 5):
            with self.subTest(value=value):
                detector = mock.Mock(return_value=self.capabilities())
                with self.assertRaisesRegex(CrewChiefError, "between 1 and 4"):
                    run_pool(
                        self.manifest(self.jobs(), f"range-{value}.json"),
                        self.root / f"range-output-{value}",
                        max_concurrency=value,
                        detector=detector,
                        clock=lambda: FIXED_TIME,
                    )
                detector.assert_not_called()

    def test_concurrency_range_boundaries_are_accepted(self):
        for value in (1, 4):
            with self.subTest(value=value):
                report = run_pool(
                    self.manifest(self.jobs(), f"boundary-{value}.json"),
                    self.root / f"boundary-output-{value}",
                    max_concurrency=value,
                    detector=lambda _: self.capabilities(),
                    clock=lambda: FIXED_TIME,
                )
                self.assertEqual(report["requested_max_concurrency"], value)
                self.assertEqual(
                    report["effective_max_concurrency"], min(value, 2)
                )

    def test_unexpected_job_runner_error_is_categorized_without_retry(self):
        attempts = []
        lock = threading.Lock()

        def fake_executor(envelope, invocation, **_kwargs):
            job_id = Path(invocation["workspace"]).name
            with lock:
                attempts.append(job_id)
            raise RuntimeError(f"synthetic runner error for {job_id}")

        report = run_pool(
            self.manifest(self.jobs()),
            self.root / "pool-output",
            execute=True,
            detector=lambda _: self.capabilities(),
            job_executor=fake_executor,
            clock=lambda: FIXED_TIME,
        )
        self.assertEqual(sorted(attempts), ["first", "second"])
        self.assertEqual(len(attempts), 2)
        self.assertTrue(
            all(item["state"] == "FAILED" for item in report["jobs"])
        )
        self.assertTrue(
            all(
                item["errors"][0]["category"] == "RUNNER_FAILURE"
                for item in report["jobs"]
            )
        )


if __name__ == "__main__":
    unittest.main()
