"""Credential-free tests for the Landing Signal Officer closeout controller."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from tools.crew_chief.controller import prepare_audit, reconcile_report, verify_envelope
from tools.crew_chief.core import CANARY, PROFILE_FOCUS, write_canonical_json
from tools.lso.controller import (
    create_authorization_receipt,
    execute_closeout,
    prepare_closeout,
    verify_plan,
)
from tools.lso.core import GENERATED_GOVERNANCE_PATHS, LSOError, consume_once, read_json
from tools.lso.git_ops import receipt_consumption_directory


ROOT = Path(__file__).resolve().parents[2]
FIXED_TIME = datetime(2026, 8, 11, 15, 0, tzinfo=timezone.utc)


class LSOFixture:
    def __init__(self, root: Path):
        self.root = root
        self.repository = root / "repository"
        self.remote = root / "remote.git"
        self.inputs = root / "inputs"
        self.repository.mkdir()
        self.inputs.mkdir()
        self.run("git", "init", "--bare", str(self.remote), cwd=root)
        self.git("init", "-b", "main")
        self.git("config", "user.name", "LSO Tests")
        self.git("config", "user.email", "lso-tests@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("remote", "add", "origin", str(self.remote))

        self.copy(ROOT / "AGENTS.md", "AGENTS.md")
        self.copy(
            ROOT / ".codex" / "agents" / "crew-chief.toml",
            ".codex/agents/crew-chief.toml",
        )
        for schema in sorted((ROOT / "tools/crew_chief/schemas").glob("*.json")):
            self.copy(schema, f"tools/crew_chief/schemas/{schema.name}")
        self.write("src/example.py", "VALUE = 1\n")
        self.write("docs/missions/example/mission.md", self.mission("Build pending"))
        for path in GENERATED_GOVERNANCE_PATHS:
            self.write(path, f"baseline {path}\n")
        self.git("add", ".")
        self.git("commit", "-m", "fixture baseline")
        self.git("push", "-u", "origin", "main")
        self.base = self.rev("HEAD")
        self.git("switch", "-c", "codex/example-lso")

        self.write("src/example.py", "VALUE = 2\n")
        self.write("docs/missions/example/mission.md", self.mission("Build ready"))
        self.engineer = self.inputs / "engineer-report.json"
        self.engineer.write_text(
            json.dumps({"outcome": "implemented", "scope": "synthetic"}),
            encoding="utf-8",
        )
        self.evidence = self.inputs / "validation.log"
        self.evidence.write_text("synthetic validation passed\n", encoding="utf-8")
        self.claims = {
            "schema_version": "1.0",
            "canary": CANARY,
            "required_checks_complete": True,
            "commands": [
                {
                    "command": "python -m unittest synthetic",
                    "scope": "complete eligible fixture suite",
                    "result": "PASS",
                    "exit_code": 0,
                    "summary": "4 synthetic checks passed",
                }
            ],
            "limitations": [],
        }

    def mission(self, state: str) -> str:
        metadata = {
            "schema_version": 1,
            "id": "governance/example-lso",
            "legacy_aliases": [],
            "title": "Example LSO Mission",
            "call_sign": "EXAMPLE",
            "namespace": "governance",
            "lifecycle": "active",
            "priority": "high",
            "portfolio_primary": True,
            "authorization_gate": "implementation only",
            "approval_evidence": [
                {
                    "date": "2026-08-11",
                    "authority": "Maverick",
                    "scope": "Authorized synthetic fixture implementation.",
                }
            ],
            "baseline_commit": self.base if hasattr(self, "base") else None,
            "implementation_commits": [],
            "pushed": False,
            "merged": False,
            "official_decisions": [],
            "workstream": {
                "owner_session": "LSO tests",
                "branch": "codex/example-lso",
                "worktree": str(self.repository),
                "writable_scope": [
                    "src/example.py",
                    "docs/missions/example/mission.md",
                ],
                "state": "implementation",
                "next_gate": "closeout",
            },
            "next_gate": "closeout",
            "supersedes": None,
            "superseded_by": None,
            "paused": False,
            "cancelled": False,
            "capability_health": "healthy",
        }
        return (
            "# Example LSO Mission\n\n"
            "<!-- wingman-mission-metadata\n"
            + json.dumps(metadata, indent=2)
            + "\n-->\n\n"
            + state
            + "\n"
        )

    @staticmethod
    def run(*arguments: str, cwd: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            arguments, cwd=cwd, check=True, capture_output=True, text=True
        )

    def git(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return self.run("git", *arguments, cwd=self.repository)

    def rev(self, revision: str) -> str:
        return self.git("rev-parse", revision).stdout.strip()

    def write(self, relative: str, content: str) -> Path:
        path = self.repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def copy(self, source: Path, relative: str) -> None:
        target = self.repository / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)

    def report(self, envelope: dict, *, verdict: str = "PASS") -> dict:
        blocked = [] if verdict == "PASS" else ["synthetic evidence is incomplete"]
        return {
            "schema_version": "1.0",
            "canary": CANARY,
            "role": "crew_chief",
            "audit_id": envelope["audit_id"],
            "envelope_id": envelope["envelope_id"],
            "reviewer_context": {
                "fresh_session": True,
                "read_only": True,
                "implementation_conversation_inherited": False,
                "live_network_tools_enabled": False,
            },
            "verdict": verdict,
            "blocked_reasons": blocked,
            "findings": [],
            "audit_scope": list(PROFILE_FOCUS["standard"]),
            "validation_evidence": ["evidence/test-claims.json"],
            "generated_at": "2026-08-11T15:05:00Z",
            "authority_statement": "Crew Chief is advisory; Maverick retains final authority.",
        }

    def prepare_package(
        self,
        name: str,
        *,
        verdict: str = "PASS",
        authorized_untracked: list[str] | None = None,
    ) -> dict:
        envelope_result = prepare_audit(
            self.repository,
            mission_record=self.repository / "docs/missions/example/mission.md",
            base=self.base,
            head=self.base,
            engineer_report=self.engineer,
            evidence_artifacts=[self.evidence],
            test_claims=self.claims,
            profile="standard",
            output_root=self.root / f"{name}-audit",
            include_worktree=True,
            authorized_untracked=authorized_untracked or [],
            expires_in_seconds=3600,
            clock=lambda: FIXED_TIME,
        )
        envelope_path = Path(envelope_result["envelope_path"])
        envelope = verify_envelope(envelope_path)
        report = self.report(envelope, verdict=verdict)
        report_path = self.root / f"{name}-report.json"
        write_canonical_json(report_path, report)
        reconciliation = reconcile_report(
            envelope, report, [], clock=lambda: FIXED_TIME
        )
        reconciliation_path = self.root / f"{name}-reconciliation.json"
        write_canonical_json(reconciliation_path, reconciliation)
        return {
            "envelope": envelope_path,
            "report": report_path,
            "reconciliation": reconciliation_path,
        }

    def prepare_plan(
        self, name: str, *, authorized_untracked: list[str] | None = None
    ) -> dict:
        package = self.prepare_package(name, authorized_untracked=authorized_untracked)
        return prepare_closeout(
            self.repository,
            mission_record=self.repository / "docs/missions/example/mission.md",
            envelope_path=package["envelope"],
            report_path=package["report"],
            reconciliation_path=package["reconciliation"],
            implementation_commit_message="Implement synthetic LSO mission",
            closeout_commit_message="Complete synthetic LSO mission records",
            final_authorization_gate="closed by Maverick",
            next_gate="Maverick selects another mission.",
            final_approval_scope="Approved exact synthetic LSO closeout.",
            output_root=self.root / f"{name}-plan",
            expires_in_seconds=3600,
            clock=lambda: FIXED_TIME,
        )

    def authorize(self, plan_result: dict, name: str) -> Path:
        text = self.root / f"{name}-authorization.txt"
        text.write_text(
            plan_result["required_authorization_text"] + "\n", encoding="utf-8"
        )
        receipt = self.root / f"{name}-receipt.json"
        create_authorization_receipt(
            Path(plan_result["plan_path"]),
            text,
            receipt,
            clock=lambda: FIXED_TIME,
        )
        return receipt

    def generate(self) -> None:
        for path in GENERATED_GOVERNANCE_PATHS:
            self.write(path, f"generated closeout {path}\n")


class LandingSignalOfficerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.fixture = LSOFixture(Path(self.temporary.name))

    def test_disposable_end_to_end_closeout_is_complete(self):
        prepared = self.fixture.prepare_plan("complete")
        receipt = self.fixture.authorize(prepared, "complete")

        result = execute_closeout(
            Path(prepared["plan_path"]),
            receipt,
            generate_governance=self.fixture.generate,
            validate_governance=lambda: [],
            clock=lambda: FIXED_TIME,
        )

        self.assertEqual(result["status"], "COMPLETE")
        self.assertTrue(result["mission_completed"])
        self.assertEqual(result["remote_target_head"], result["closeout_commit"])
        self.assertEqual(result["remote_branch_head"], result["closeout_commit"])
        self.assertEqual(len(result["completed_actions"]), 9)
        mission = (
            self.fixture.repository / "docs/missions/example/mission.md"
        ).read_text()
        self.assertIn('"lifecycle": "completed"', mission)
        self.assertEqual(self.fixture.git("status", "--porcelain").stdout, "")

    def test_precommit_failure_restores_exact_real_index(self):
        prepared = self.fixture.prepare_plan("index-restore")
        receipt = self.fixture.authorize(prepared, "index-restore")
        index_path = Path(
            self.fixture.git(
                "rev-parse", "--path-format=absolute", "--git-path", "index"
            ).stdout.strip()
        )
        before = index_path.read_bytes()

        with patch(
            "tools.lso.controller.changed_path_sets",
            side_effect=LSOError("synthetic post-add verification failure"),
        ):
            result = execute_closeout(
                Path(prepared["plan_path"]),
                receipt,
                generate_governance=self.fixture.generate,
                validate_governance=lambda: [],
                clock=lambda: FIXED_TIME,
            )

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["completed_actions"], [])
        self.assertEqual(result["failed_action"], "stage_exact_audited_paths")
        self.assertIn("post-add verification failure", result["error"])
        self.assertEqual(index_path.read_bytes(), before)
        self.assertEqual(self.fixture.git("diff", "--cached", "--name-only").stdout, "")

    def test_index_restoration_failure_is_reported_partial(self):
        prepared = self.fixture.prepare_plan("index-restore-fails")
        receipt = self.fixture.authorize(prepared, "index-restore-fails")

        with (
            patch(
                "tools.lso.controller.changed_path_sets",
                side_effect=LSOError("synthetic post-add verification failure"),
            ),
            patch(
                "tools.lso.controller.restore_index",
                side_effect=LSOError("synthetic index restoration failure"),
            ),
        ):
            result = execute_closeout(
                Path(prepared["plan_path"]),
                receipt,
                generate_governance=self.fixture.generate,
                validate_governance=lambda: [],
                clock=lambda: FIXED_TIME,
            )

        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual(result["completed_actions"], [])
        self.assertEqual(result["failed_action"], "stage_exact_audited_paths")
        self.assertIn("post-add verification failure", result["error"])
        self.assertIn("index restoration failure", result["error"])
        self.assertNotEqual(
            self.fixture.git("diff", "--cached", "--name-only").stdout, ""
        )

    def test_plan_rejects_worktree_drift(self):
        prepared = self.fixture.prepare_plan("drift")
        self.fixture.write("src/example.py", "VALUE = 3\n")

        with self.assertRaisesRegex(LSOError, "changed|drift|state"):
            verify_plan(Path(prepared["plan_path"]), clock=lambda: FIXED_TIME)

    def test_plan_rejects_untracked_whitespace_before_approval(self):
        relative = "docs/untracked-with-blank-line.md"
        self.fixture.write(relative, "# New audited file\n\n")

        with self.assertRaisesRegex(LSOError, "new blank line at EOF"):
            self.fixture.prepare_plan(
                "untracked-whitespace", authorized_untracked=[relative]
            )

        self.assertEqual(self.fixture.git("diff", "--cached", "--name-only").stdout, "")
        self.assertFalse(
            (Path(self.temporary.name) / "untracked-whitespace-plan").exists()
        )

    def test_non_pass_audit_cannot_prepare_closeout(self):
        package = self.fixture.prepare_package("blocked", verdict="BLOCKED")

        with self.assertRaisesRegex(LSOError, "requires Crew Chief PASS"):
            prepare_closeout(
                self.fixture.repository,
                mission_record=self.fixture.repository
                / "docs/missions/example/mission.md",
                envelope_path=package["envelope"],
                report_path=package["report"],
                reconciliation_path=package["reconciliation"],
                implementation_commit_message="Implement fixture",
                closeout_commit_message="Close fixture",
                final_authorization_gate="closed",
                next_gate="next",
                final_approval_scope="approved",
                output_root=Path(self.temporary.name) / "blocked-plan",
                clock=lambda: FIXED_TIME,
            )

    def test_receipt_requires_exact_authorization_text(self):
        prepared = self.fixture.prepare_plan("wrong-text")
        text = Path(self.temporary.name) / "wrong.txt"
        text.write_text("approve something else\n", encoding="utf-8")

        with self.assertRaisesRegex(LSOError, "does not exactly approve"):
            create_authorization_receipt(
                Path(prepared["plan_path"]),
                text,
                Path(self.temporary.name) / "wrong-receipt.json",
                clock=lambda: FIXED_TIME,
            )

    def test_authorization_text_symlink_is_rejected(self):
        prepared = self.fixture.prepare_plan("symlink-text")
        target = Path(self.temporary.name) / "authorization-target.txt"
        target.write_text(
            prepared["required_authorization_text"] + "\n", encoding="utf-8"
        )
        link = Path(self.temporary.name) / "authorization-link.txt"
        link.symlink_to(target)

        with self.assertRaisesRegex(LSOError, "regular external file"):
            create_authorization_receipt(
                Path(prepared["plan_path"]),
                link,
                Path(self.temporary.name) / "symlink-receipt.json",
                clock=lambda: FIXED_TIME,
            )

    def test_advanced_remote_target_fails_before_consumption(self):
        prepared = self.fixture.prepare_plan("advanced")
        receipt = self.fixture.authorize(prepared, "advanced")
        other = Path(self.temporary.name) / "other-clone"
        LSOFixture.run(
            "git",
            "clone",
            "--branch",
            "main",
            str(self.fixture.remote),
            str(other),
            cwd=Path(self.temporary.name),
        )
        LSOFixture.run("git", "config", "user.name", "Remote Tests", cwd=other)
        LSOFixture.run(
            "git", "config", "user.email", "remote-tests@example.invalid", cwd=other
        )
        (other / "remote-only.txt").write_text("advanced\n", encoding="utf-8")
        LSOFixture.run("git", "add", "remote-only.txt", cwd=other)
        LSOFixture.run("git", "commit", "-m", "remote advance", cwd=other)
        LSOFixture.run("git", "push", "origin", "main", cwd=other)

        result = execute_closeout(
            Path(prepared["plan_path"]),
            receipt,
            generate_governance=self.fixture.generate,
            validate_governance=lambda: [],
            clock=lambda: FIXED_TIME,
        )

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["failed_action"], None)
        self.assertIn("main changed", result["error"])
        receipt_value = read_json(receipt)
        marker = receipt_consumption_directory(
            self.fixture.repository,
            read_json(Path(prepared["plan_path"]))["repository"]["repository_id"],
        )
        self.assertFalse((marker / receipt_value["receipt_id"]).exists())

    def test_copied_plan_cannot_reuse_consumed_receipt_after_pre_mutation_failure(
        self,
    ):
        prepared = self.fixture.prepare_plan("copied-retry")
        plan_path = Path(prepared["plan_path"])
        authorization = plan_path.parent / "authorization.txt"
        authorization.write_text(
            prepared["required_authorization_text"] + "\n", encoding="utf-8"
        )
        receipt = plan_path.parent / "authorization-receipt.json"
        create_authorization_receipt(
            plan_path,
            authorization,
            receipt,
            clock=lambda: FIXED_TIME,
        )
        copied_package = Path(self.temporary.name) / "copied-plan-package"
        shutil.copytree(plan_path.parent, copied_package)

        with patch(
            "tools.lso.controller.git",
            side_effect=LSOError("synthetic post-consumption pre-mutation failure"),
        ):
            first = execute_closeout(
                plan_path,
                receipt,
                generate_governance=self.fixture.generate,
                validate_governance=lambda: [],
                clock=lambda: FIXED_TIME,
            )

        self.assertEqual(first["status"], "FAILED")
        self.assertEqual(first["completed_actions"], [])
        self.assertEqual(first["failed_action"], "stage_exact_audited_paths")
        self.assertIn("pre-mutation failure", first["error"])
        plan = read_json(plan_path)
        receipt_value = read_json(receipt)
        marker = (
            receipt_consumption_directory(
                self.fixture.repository, plan["repository"]["repository_id"]
            )
            / receipt_value["receipt_id"]
        )
        self.assertTrue(marker.is_file())
        self.assertFalse((plan_path.parent / "consumed").exists())
        self.assertFalse((copied_package / "consumed").exists())

        second = execute_closeout(
            copied_package / "closeout-plan.json",
            copied_package / "authorization-receipt.json",
            generate_governance=self.fixture.generate,
            validate_governance=lambda: [],
            clock=lambda: FIXED_TIME,
        )

        self.assertEqual(second["status"], "FAILED")
        self.assertEqual(second["completed_actions"], [])
        self.assertEqual(second["failed_action"], None)
        self.assertIn("already consumed", second["error"])
        self.assertEqual(self.fixture.rev("HEAD"), self.fixture.base)
        self.assertEqual(
            self.fixture.rev("refs/remotes/origin/main"), self.fixture.base
        )

    def test_post_publication_failure_is_partial_and_never_retried(self):
        prepared = self.fixture.prepare_plan("partial")
        receipt = self.fixture.authorize(prepared, "partial")

        def fail_generation() -> None:
            raise RuntimeError("synthetic generation failure")

        result = execute_closeout(
            Path(prepared["plan_path"]),
            receipt,
            generate_governance=fail_generation,
            validate_governance=lambda: [],
            clock=lambda: FIXED_TIME,
        )

        self.assertEqual(result["status"], "PARTIAL")
        self.assertIn("fast_forward_main", result["completed_actions"])
        self.assertEqual(result["failed_action"], "publish_completion_records")
        self.assertIn("synthetic generation failure", result["error"])
        receipt_value = read_json(receipt)
        marker_root = receipt_consumption_directory(
            self.fixture.repository,
            read_json(Path(prepared["plan_path"]))["repository"]["repository_id"],
        )
        marker = marker_root / receipt_value["receipt_id"]
        self.assertTrue(marker.is_file())
        with self.assertRaisesRegex(LSOError, "already consumed"):
            consume_once(marker_root, receipt_value["receipt_id"])


if __name__ == "__main__":
    unittest.main()
