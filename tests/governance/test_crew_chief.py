"""Credential-free tests for the Crew Chief independent-audit workflow."""

from __future__ import annotations

import json
import os
import ast
import copy
import shutil
import subprocess
import tempfile
import tomllib
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from tools.crew_chief.bootstrap_authorization import (
    AuthorizationExpectation,
    create_authorization_receipt,
    execute_authorized_bootstrap,
    prepare_authorized_bootstrap_invocation,
    validate_authorization_receipt,
)
from tools.crew_chief.controller import (
    prepare_audit,
    reconcile_report,
    verify_envelope,
)
from tools.crew_chief.core import (
    CANARY,
    PROFILE_FOCUS,
    CrewChiefError,
    bind_file,
    canonical_json_bytes,
    read_json,
    sha256_bytes,
    sha256_file,
    write_canonical_json,
)
from tools.crew_chief.runner import (
    _DISABLED_REVIEW_FEATURES,
    _PERMITTED_REVIEW_FEATURES,
    _REQUIRED_EXEC_FLAGS,
    CodexCapabilities,
    build_ordinary_bootstrap_launch_command,
    build_launch_command,
    detect_codex_capabilities,
    execute_prepared_review,
    prepare_review_workspace,
)
from tools.crew_chief.service_schema import (
    bind_bootstrap_service_schema,
    bundle_report_schema,
    canonical_to_service_output,
    normalize_service_output,
    project_service_schema,
    validate_service_instance,
    validate_service_schema,
)
from tools.crew_chief.validation import (
    validate_instance,
    validate_reconciliation,
    validate_report,
)
from tools.governance import repository as governance


ROOT = Path(__file__).resolve().parents[2]
FIXED_TIME = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)


def bundled_report_schema() -> dict:
    return bundle_report_schema(ROOT / "tools/crew_chief/schemas")


class FixtureRepository:
    """Disposable Git subject; tests never mutate the real repository."""

    def __init__(self, root: Path):
        self.root = root
        self.repo = root / "repository"
        self.inputs = root / "inputs"
        self.repo.mkdir()
        self.inputs.mkdir()
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Crew Chief Tests")
        self.git("config", "user.email", "crew-chief-tests@example.invalid")
        self.git("config", "commit.gpgsign", "false")

        self.write("docs/missions/example/mission.md", "# Example mission\n")
        self.write("src/example.py", "VALUE = 1\n")
        self.write("src/deleted.py", "REMOVED = True\n")
        self.write_bytes("assets/payload.bin", b"\x00\xffbase\n")
        self.copy(ROOT / "AGENTS.md", "AGENTS.md")
        agent = ROOT / ".codex" / "agents" / "crew-chief.toml"
        self.copy(agent, ".codex/agents/crew-chief.toml")
        schema_source = ROOT / "tools" / "crew_chief" / "schemas"
        for schema in sorted(schema_source.glob("*.json")):
            self.copy(schema, f"tools/crew_chief/schemas/{schema.name}")
        self.git("add", ".")
        self.git("commit", "-m", "fixture baseline")
        self.base = self.rev("HEAD")

        self.write("src/example.py", "VALUE = 2\n")
        (self.repo / "src/deleted.py").unlink()
        self.write_bytes("assets/payload.bin", b"\x00\xffhead\n")
        self.write("scripts/check.sh", "#!/bin/sh\nexit 0\n")
        os.chmod(self.repo / "scripts" / "check.sh", 0o755)
        self.git("add", ".")
        self.git("commit", "-m", "fixture implementation")
        self.head = self.rev("HEAD")

        self.engineer_report = self.inputs / "engineer-report.json"
        self.engineer_report.write_text(
            json.dumps({"outcome": "implemented", "validation": ["tests passed"]}),
            encoding="utf-8",
        )
        self.evidence = self.inputs / "validation.log"
        self.evidence.write_text("2 tests passed\n", encoding="utf-8")
        self.claims = {
            "claims": [
                {
                    "command": "python -m unittest tests.example",
                    "result": "PASS",
                }
            ]
        }

    def git(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *arguments],
            cwd=self.repo,
            check=True,
            capture_output=True,
            text=True,
        )

    def rev(self, revision: str) -> str:
        return self.git("rev-parse", revision).stdout.strip()

    def write(self, relative: str, content: str) -> Path:
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def write_bytes(self, relative: str, content: bytes) -> Path:
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def copy(self, source: Path, relative: str) -> Path:
        target = self.repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        return target

    def prepare(
        self,
        name: str,
        *,
        base: str | None = None,
        head: str | None = None,
        include_worktree: bool = False,
        authorized_untracked: tuple[str, ...] = (),
        profile: str = "standard",
        justification: str | None = None,
        claims: dict | None = None,
    ) -> dict:
        return prepare_audit(
            self.repo,
            mission_record=self.repo / "docs/missions/example/mission.md",
            base=base or self.base,
            head=head or self.head,
            engineer_report=self.engineer_report,
            evidence_artifacts=[self.evidence],
            test_claims=claims or self.claims,
            profile=profile,
            profile_justification=justification,
            output_root=self.root / name,
            include_worktree=include_worktree,
            authorized_untracked=authorized_untracked,
            expires_in_seconds=3600,
            clock=lambda: FIXED_TIME,
        )


def report_for(
    envelope: dict,
    findings=None,
    *,
    verdict="PASS",
    blocked=None,
    scope=None,
):
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
        "blocked_reasons": blocked or [],
        "findings": findings or [],
        "audit_scope": scope
        if scope is not None
        else list(envelope["risk_profile"]["required_focus"]),
        "validation_evidence": ["frozen/validation.log"],
        "generated_at": "2026-08-09T12:30:00Z",
        "authority_statement": (
            "Crew Chief is advisory; Maverick retains final authority."
        ),
    }


def finding(
    finding_id="CC-0001",
    *,
    severity="high",
    blocking=True,
    rationale=None,
):
    value = {
        "finding_id": finding_id,
        "severity": severity,
        "blocking": blocking,
        "category": "correctness",
        "evidence": [
            {
                "kind": "source",
                "path": "src/example.py",
                "state": "head",
                "line_start": 1,
                "line_end": 1,
                "detail": "exact failing line",
            }
        ],
        "why_it_matters": "The behavior can regress.",
        "action_kind": "required" if blocking else "recommended",
        "action": "Correct and rerun the focused validation.",
    }
    if rationale is not None:
        value["blocking_rationale"] = rationale
    return value


class BootstrapAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repository = self.root / "repository"
        self.repository.mkdir()
        self.package = self.root / "bootstrap-package.md"
        self.schema = self.root / "bootstrap-report.schema.json"
        self.receipt_path = self.root / "authorization-receipt.json"
        self.codex = self.root / "codex"
        self.codex.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        self.codex.chmod(0o755)
        self.capabilities = CodexCapabilities(
            executable=str(self.codex.resolve()),
            version="codex-cli test",
            exec_flags=tuple(sorted(_REQUIRED_EXEC_FLAGS)),
            features=("shell_tool",),
            shell_tool_control=True,
            custom_agent_selector=True,
        )
        capability_patch = mock.patch(
            "tools.crew_chief.bootstrap_authorization.detect_codex_capabilities",
            return_value=self.capabilities,
        )
        capability_patch.start()
        self.addCleanup(capability_patch.stop)
        self.package.write_text("frozen implementation evidence\n", encoding="utf-8")
        self.schema.write_text(
            '{"additionalProperties":false,"properties":{},"required":[],"type":"object"}\n',
            encoding="utf-8",
        )
        self.authorization_text = "Maverick authorizes this exact package."
        self.expectation = AuthorizationExpectation(
            subject_head="1" * 40,
            package_size=self.package.stat().st_size,
            package_sha256=sha256_file(self.package),
            service_schema_size=self.schema.stat().st_size,
            service_schema_sha256=sha256_file(self.schema),
            audit_id="a" * 64,
            envelope_id="b" * 64,
            package_expires_at="2026-08-09T14:00:00Z",
            authorization_text_sha256=sha256_bytes(
                self.authorization_text.encode("utf-8")
            ),
            ordinary_bootstrap_invocations=1,
            conditional_crew_chief_fixture_audits=2,
            automatic_retries_permitted=False,
        )
        self.receipt = create_authorization_receipt(
            self.expectation,
            authorization_text=self.authorization_text,
            authorized_at=FIXED_TIME,
            expires_at=FIXED_TIME + timedelta(hours=1),
        )
        write_canonical_json(self.receipt_path, self.receipt)

    def prepare(self, name="review"):
        return prepare_authorized_bootstrap_invocation(
            self.repository,
            self.package,
            self.schema,
            self.receipt_path,
            self.root / name,
            expectation=self.expectation,
            clock=lambda: FIXED_TIME,
        )

    def assert_command_rejected_before_consumption(
        self,
        name,
        mutate,
        *,
        message="canonical contract|binding|capability evidence",
    ):
        invocation = self.prepare(name)
        invocation_path = Path(invocation["workspace"]) / "invocation.json"
        persisted = read_json(invocation_path)
        mutate(persisted)
        write_canonical_json(invocation_path, persisted)
        marker = self.receipt_path.with_name(
            f".{self.receipt_path.name}.{self.receipt['receipt_id']}.consumed.json"
        )
        runner = mock.Mock()
        with self.assertRaisesRegex(CrewChiefError, message):
            execute_authorized_bootstrap(
                invocation_path,
                runner=runner,
                clock=lambda: FIXED_TIME,
            )
        runner.assert_not_called()
        self.assertFalse(marker.exists())

    def test_valid_receipt_binds_exact_authorized_subject(self):
        validated = validate_authorization_receipt(
            self.receipt,
            self.expectation,
            clock=lambda: FIXED_TIME,
        )
        self.assertEqual(validated["canary"], CANARY)
        self.assertEqual(validated["authority"]["identity"], "Maverick")
        self.assertEqual(
            validated["subject"],
            {
                "head_commit": self.expectation.subject_head,
                "package": {
                    "size": self.expectation.package_size,
                    "sha256": self.expectation.package_sha256,
                },
                "service_schema": {
                    "size": self.expectation.service_schema_size,
                    "sha256": self.expectation.service_schema_sha256,
                },
                "audit_id": self.expectation.audit_id,
                "envelope_id": self.expectation.envelope_id,
                "package_expires_at": self.expectation.package_expires_at,
            },
        )

    def test_missing_malformed_expired_altered_and_mismatched_receipts_fail(self):
        self.receipt_path.unlink()
        with self.assertRaisesRegex(CrewChiefError, "invalid JSON artifact"):
            self.prepare("missing")

        with self.assertRaisesRegex(CrewChiefError, "JSON object"):
            validate_authorization_receipt(
                [], self.expectation, clock=lambda: FIXED_TIME
            )

        with self.assertRaisesRegex(CrewChiefError, "expired"):
            validate_authorization_receipt(
                self.receipt,
                self.expectation,
                clock=lambda: FIXED_TIME + timedelta(hours=2),
            )

        altered = json.loads(json.dumps(self.receipt))
        altered["subject"]["package"]["size"] += 1
        with self.assertRaisesRegex(CrewChiefError, "ID does not match"):
            validate_authorization_receipt(
                altered, self.expectation, clock=lambda: FIXED_TIME
            )

        mismatched = json.loads(json.dumps(self.receipt))
        mismatched["subject"]["head_commit"] = "2" * 40
        unsigned = dict(mismatched)
        unsigned.pop("receipt_id")
        mismatched["receipt_id"] = sha256_bytes(canonical_json_bytes(unsigned))
        with self.assertRaisesRegex(CrewChiefError, "subject is mismatched"):
            validate_authorization_receipt(
                mismatched, self.expectation, clock=lambda: FIXED_TIME
            )

    def test_receipt_cannot_authorize_extra_invocations_or_retries(self):
        extra = AuthorizationExpectation(
            **{**self.expectation.__dict__, "ordinary_bootstrap_invocations": 2}
        )
        with self.assertRaisesRegex(CrewChiefError, "exactly one"):
            create_authorization_receipt(
                extra,
                authorization_text=self.authorization_text,
                authorized_at=FIXED_TIME,
                expires_at=FIXED_TIME + timedelta(hours=1),
            )
        retry = AuthorizationExpectation(
            **{**self.expectation.__dict__, "automatic_retries_permitted": True}
        )
        with self.assertRaisesRegex(CrewChiefError, "automatic retries"):
            create_authorization_receipt(
                retry,
                authorization_text=self.authorization_text,
                authorized_at=FIXED_TIME,
                expires_at=FIXED_TIME + timedelta(hours=1),
            )

    def test_receipt_is_consumed_once_across_prepared_workspaces(self):
        first = self.prepare("first")
        second = self.prepare("second")
        runner = mock.Mock(
            return_value=subprocess.CompletedProcess(
                ["codex", "exec", "-"], 0, stdout="{}\n", stderr=""
            )
        )
        execute_authorized_bootstrap(
            Path(first["workspace"]) / "invocation.json",
            runner=runner,
            clock=lambda: FIXED_TIME,
        )
        with self.assertRaisesRegex(CrewChiefError, "already consumed"):
            execute_authorized_bootstrap(
                Path(second["workspace"]) / "invocation.json",
                runner=runner,
                clock=lambda: FIXED_TIME,
            )
        self.assertEqual(runner.call_count, 1)

    def test_bootstrap_command_is_internally_constructed_for_ordinary_reviewer(self):
        invocation = self.prepare()
        workspace = Path(invocation["workspace"])
        expected = build_ordinary_bootstrap_launch_command(
            self.capabilities,
            workspace,
            workspace / "frozen/bootstrap-report.schema.json",
            workspace / "output/bootstrap-report.json",
        )
        self.assertEqual(invocation["argv"], expected)
        self.assertEqual(invocation["argv"][0], str(self.codex.resolve()))
        self.assertEqual(invocation["argv"][-1], "-")
        self.assertNotIn("--agent", invocation["argv"])
        self.assertNotIn("crew_chief", invocation["argv"])
        self.assertEqual(
            invocation["command_contract"]["role"],
            "ordinary_codex_bootstrap_reviewer",
        )

    def test_every_command_token_omission_fails_before_receipt_consumption(self):
        template = self.prepare("omission-template")["argv"]
        for index, token in enumerate(template):
            with self.subTest(index=index, token=token):
                self.assert_command_rejected_before_consumption(
                    f"omission-{index}",
                    lambda value, index=index: value["argv"].pop(index),
                )

    def test_duplicate_added_reordered_and_weakened_controls_fail_closed(self):
        def duplicate_ephemeral(value):
            index = value["argv"].index("--ephemeral")
            value["argv"].insert(index, "--ephemeral")

        def add_control(value):
            value["argv"].insert(-1, "--dangerously-added-control")

        def reorder_control(value):
            value["argv"][0], value["argv"][1] = (
                value["argv"][1],
                value["argv"][0],
            )

        def replace_value(flag, replacement):
            def mutate(value):
                index = value["argv"].index(flag)
                value["argv"][index + 1] = replacement

            return mutate

        alterations = [
            ("duplicate", duplicate_ephemeral),
            ("added", add_control),
            ("reordered", reorder_control),
            ("executable", lambda value: value["argv"].__setitem__(0, "/bin/false")),
            ("approval", replace_value("--config", 'approval_policy="on-request"')),
            ("sandbox", replace_value("--sandbox", "workspace-write")),
            ("schema", replace_value("--output-schema", "/tmp/other.schema.json")),
            ("output", replace_value("--output-last-message", "/tmp/other.json")),
            ("workspace", replace_value("--cd", "/tmp/other-workspace")),
            ("color", replace_value("--color", "always")),
            ("disable", replace_value("--disable", "apps")),
            ("stdin", lambda value: value["argv"].__setitem__(-1, "prompt.txt")),
        ]
        for name, mutate in alterations:
            with self.subTest(alteration=name):
                self.assert_command_rejected_before_consumption(name, mutate)

    def test_command_binding_and_capability_tampering_fail_closed(self):
        self.assert_command_rejected_before_consumption(
            "command-binding",
            lambda value: value["command_contract"].__setitem__(
                "argv_sha256", "0" * 64
            ),
            message="command binding",
        )
        self.assert_command_rejected_before_consumption(
            "capabilities",
            lambda value: value["command_contract"]["capabilities"].__setitem__(
                "version", "tampered"
            ),
            message="capability evidence changed",
        )

    def test_approved_executable_change_fails_before_receipt_consumption(self):
        invocation = self.prepare("executable-change")
        invocation_path = Path(invocation["workspace"]) / "invocation.json"
        self.codex.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        runner = mock.Mock()
        marker = self.receipt_path.with_name(
            f".{self.receipt_path.name}.{self.receipt['receipt_id']}.consumed.json"
        )
        with self.assertRaisesRegex(CrewChiefError, "executable binding hash changed"):
            execute_authorized_bootstrap(
                invocation_path,
                runner=runner,
                clock=lambda: FIXED_TIME,
            )
        runner.assert_not_called()
        self.assertFalse(marker.exists())

    def test_receipt_creation_and_preparation_do_not_change_subject_files(self):
        package_before = (self.package.stat().st_size, sha256_file(self.package))
        schema_before = (self.schema.stat().st_size, sha256_file(self.schema))
        self.prepare()
        self.assertEqual(
            package_before, (self.package.stat().st_size, sha256_file(self.package))
        )
        self.assertEqual(
            schema_before, (self.schema.stat().st_size, sha256_file(self.schema))
        )

    def test_exact_receipt_is_bound_into_invocation_and_run_record(self):
        invocation = self.prepare()
        binding = invocation["source_bindings"]["authorization_receipt"]
        self.assertEqual(binding["path"], str(self.receipt_path.resolve()))
        self.assertEqual(binding["size"], self.receipt_path.stat().st_size)
        self.assertEqual(binding["sha256"], sha256_file(self.receipt_path))
        runner = mock.Mock(
            return_value=subprocess.CompletedProcess(
                ["codex", "exec", "-"], 0, stdout="{}\n", stderr=""
            )
        )
        record = execute_authorized_bootstrap(
            Path(invocation["workspace"]) / "invocation.json",
            runner=runner,
            clock=lambda: FIXED_TIME,
        )
        self.assertEqual(record["authorization_receipt"], binding)
        self.assertEqual(
            record["frozen_authorization_receipt"]["sha256"], binding["sha256"]
        )
        self.assertEqual(record["automatic_retry_attempts"], 0)
        persisted = read_json(Path(invocation["run_record_path"]))
        self.assertEqual(persisted, record)

    def test_invalid_receipt_prevents_process_runner_call(self):
        invocation = self.prepare()
        self.receipt_path.write_bytes(self.receipt_path.read_bytes() + b" ")
        runner = mock.Mock()
        with self.assertRaisesRegex(CrewChiefError, "binding (size|hash) changed"):
            execute_authorized_bootstrap(
                Path(invocation["workspace"]) / "invocation.json",
                runner=runner,
                clock=lambda: FIXED_TIME,
            )
        runner.assert_not_called()

    def test_ordinary_reviewer_receives_validated_receipt_as_frozen_evidence(self):
        invocation = self.prepare()
        runner = mock.Mock(
            return_value=subprocess.CompletedProcess(
                ["codex", "exec", "-"], 0, stdout="{}\n", stderr=""
            )
        )
        execute_authorized_bootstrap(
            Path(invocation["workspace"]) / "invocation.json",
            runner=runner,
            clock=lambda: FIXED_TIME,
        )
        prompt = runner.call_args.kwargs["input"]
        self.assertIn("BEGIN FROZEN authorization-receipt.json", prompt)
        self.assertIn(self.receipt["receipt_id"], prompt)
        self.assertIn("Return BLOCKED", prompt)
        self.assertIn("not a Crew Chief audit", prompt)


class CrewChiefAgentTests(unittest.TestCase):
    def test_custom_agent_toml_parses_with_required_read_only_fields(self):
        path = ROOT / ".codex" / "agents" / "crew-chief.toml"
        with path.open("rb") as handle:
            agent = tomllib.load(handle)
        self.assertEqual(agent["name"], "crew_chief")
        self.assertIn("independent", agent["description"].lower())
        self.assertEqual(agent["sandbox_mode"], "read-only")
        self.assertEqual(agent["model_reasoning_effort"], "high")
        self.assertNotIn("model", agent)
        self.assertIn("File length alone is not a defect", agent["developer_instructions"])

    def test_role_identity_is_distinct_from_goose_and_flightline(self):
        text = (ROOT / ".codex/agents/crew-chief.toml").read_text(encoding="utf-8")
        self.assertIn("not\nMaverick, Goose, Mission Control", text)
        self.assertIn("Development Flightline Independent\nAuditor", text)
        self.assertIn("cannot approve lifecycle gates", text)


class CrewChiefEnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.fixture = FixtureRepository(Path(self.temporary.name))

    def tearDown(self):
        self.temporary.cleanup()

    def test_committed_range_is_frozen_and_verifiable(self):
        result = self.fixture.prepare("envelope")
        envelope = verify_envelope(
            Path(result["envelope_path"]), clock=lambda: FIXED_TIME
        )
        manifest = read_json(Path(result["manifest_path"]))
        self.assertEqual(envelope["subject"]["base_commit"], self.fixture.base)
        self.assertEqual(envelope["subject"]["head_commit"], self.fixture.head)
        self.assertEqual(envelope["subject"]["mode"], "committed-range")
        self.assertEqual(
            {item["path"] for item in manifest["subject"]["changed_files"]},
            {
                "assets/payload.bin",
                "scripts/check.sh",
                "src/deleted.py",
                "src/example.py",
            },
        )
        script = next(
            item for item in manifest["subject"]["changed_files"]
            if item["path"] == "scripts/check.sh"
        )
        self.assertEqual(script["file_type"], "executable")
        self.assertEqual(script["modes"]["head"], "100755")
        self.assertEqual(
            manifest["controls"]["repository_instructions"]["path"],
            "controls/AGENTS.md",
        )

    def test_complete_changed_content_is_frozen_with_exact_state_metadata(self):
        result = self.fixture.prepare("envelope")
        root = Path(result["output_root"])
        manifest = read_json(Path(result["manifest_path"]))
        material = {
            (item["repository_path"], item["state"]): item
            for item in manifest["subject"]["source_material"]
        }
        base = material[("src/example.py", "base")]
        head = material[("src/example.py", "head")]
        self.assertEqual(base["revision"], self.fixture.base)
        self.assertEqual(head["revision"], self.fixture.head)
        self.assertEqual(base["encoding"], "utf-8")
        self.assertEqual(base["line_count"], 1)
        self.assertEqual(
            (root / base["frozen"]["path"]).read_text(encoding="utf-8"),
            "VALUE = 1\n",
        )
        self.assertEqual(
            (root / head["frozen"]["path"]).read_text(encoding="utf-8"),
            "VALUE = 2\n",
        )
        deleted_base = material[("src/deleted.py", "base")]
        deleted_head = material[("src/deleted.py", "head")]
        self.assertEqual(deleted_base["presence"], "present")
        self.assertEqual(deleted_head["presence"], "absent")
        self.assertIsNone(deleted_head["frozen"])
        binary = material[("assets/payload.bin", "head")]
        self.assertEqual(binary["encoding"], "base64")
        self.assertIsNone(binary["line_count"])
        self.assertEqual(
            (root / binary["frozen"]["path"]).read_bytes(), b"\x00\xffhead\n"
        )

    def test_identical_source_content_is_deduplicated(self):
        result = self.fixture.prepare("envelope")
        root = Path(result["output_root"]) / "source-content" / "sha256"
        manifest = read_json(Path(result["manifest_path"]))
        references = [
            item["frozen"]["path"]
            for item in manifest["subject"]["source_material"]
            if item["frozen"] is not None
        ]
        self.assertEqual(len(list(root.iterdir())), len(set(references)))

    def test_manifest_is_deterministic_with_fixed_clock(self):
        first = self.fixture.prepare("first")
        second = self.fixture.prepare("second")
        first_manifest = Path(first["manifest_path"]).read_bytes()
        second_manifest = Path(second["manifest_path"]).read_bytes()
        self.assertEqual(first_manifest, second_manifest)
        self.assertEqual(first["audit_id"], second["audit_id"])
        self.assertEqual(first["envelope_id"], second["envelope_id"])

    def test_fixed_clock_controls_creation_and_expiration(self):
        result = self.fixture.prepare("envelope")
        envelope = read_json(Path(result["envelope_path"]))
        self.assertEqual(envelope["created_at"], "2026-08-09T12:00:00Z")
        self.assertEqual(envelope["expires_at"], "2026-08-09T13:00:00Z")

    def test_envelope_identifier_binds_time_window(self):
        result = self.fixture.prepare("envelope")
        envelope_path = Path(result["envelope_path"])
        envelope = read_json(envelope_path)
        envelope["envelope_id"] = "c" * 64
        unhashed = dict(envelope)
        unhashed.pop("envelope_hash")
        envelope["envelope_hash"] = sha256_bytes(canonical_json_bytes(unhashed))
        envelope_path.write_text(json.dumps(envelope), encoding="utf-8")
        with self.assertRaisesRegex(CrewChiefError, "identifier"):
            verify_envelope(envelope_path, clock=lambda: FIXED_TIME)

    def test_staged_unstaged_and_authorized_untracked_are_bound(self):
        self.fixture.write("src/example.py", "VALUE = 3\n")
        self.fixture.git("add", "src/example.py")
        self.fixture.write("src/example.py", "VALUE = 4\n")
        self.fixture.write("notes.txt", "authorized untracked evidence\n")
        result = self.fixture.prepare(
            "working",
            base=self.fixture.head,
            head=self.fixture.head,
            include_worktree=True,
            authorized_untracked=("notes.txt",),
        )
        manifest = read_json(Path(result["manifest_path"]))
        entries = {
            item["path"]: item for item in manifest["subject"]["changed_files"]
        }
        self.assertEqual(entries["src/example.py"]["sources"], ["staged", "unstaged"])
        self.assertEqual(entries["notes.txt"]["sources"], ["untracked"])
        self.assertNotEqual(
            entries["src/example.py"]["sha256"]["index"],
            entries["src/example.py"]["sha256"]["worktree"],
        )
        self.assertEqual(
            [item["name"] for item in manifest["diffs"]],
            ["committed.diff", "staged.diff", "unstaged.diff"],
        )

    def test_unbound_untracked_file_is_rejected(self):
        self.fixture.write("unbound.txt", "not authorized\n")
        with self.assertRaisesRegex(CrewChiefError, "untracked allowlist"):
            self.fixture.prepare(
                "working",
                base=self.fixture.head,
                head=self.fixture.head,
                include_worktree=True,
            )

    def test_secret_path_is_rejected_without_reading_it(self):
        self.fixture.write(".env.local", "DO_NOT_READ=this-value\n")
        with self.assertRaisesRegex(CrewChiefError, "secret-bearing path"):
            self.fixture.prepare(
                "working",
                base=self.fixture.head,
                head=self.fixture.head,
                include_worktree=True,
                authorized_untracked=(".env.local",),
            )

    def test_secret_bearing_external_parent_is_rejected(self):
        secret_parent = self.fixture.inputs / "credentials"
        secret_parent.mkdir()
        engineer = secret_parent / "report.json"
        engineer.write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(CrewChiefError, "secret-bearing path"):
            prepare_audit(
                self.fixture.repo,
                mission_record=self.fixture.repo / "docs/missions/example/mission.md",
                base=self.fixture.base,
                head=self.fixture.head,
                engineer_report=engineer,
                evidence_artifacts=[self.fixture.evidence],
                test_claims=self.fixture.claims,
                output_root=Path(self.temporary.name) / "secret-parent",
                clock=lambda: FIXED_TIME,
            )

    def test_live_data_evidence_parent_is_rejected(self):
        live_parent = self.fixture.inputs / "live-data"
        live_parent.mkdir()
        evidence = live_parent / "validation.log"
        evidence.write_text("not live fixture data\n", encoding="utf-8")
        with self.assertRaisesRegex(CrewChiefError, "live-data path"):
            prepare_audit(
                self.fixture.repo,
                mission_record=self.fixture.repo / "docs/missions/example/mission.md",
                base=self.fixture.base,
                head=self.fixture.head,
                engineer_report=self.fixture.engineer_report,
                evidence_artifacts=[evidence],
                test_claims=self.fixture.claims,
                output_root=Path(self.temporary.name) / "live-evidence",
                clock=lambda: FIXED_TIME,
            )

    def test_live_data_path_is_rejected(self):
        self.fixture.write("data/live.json", "{}\n")
        with self.assertRaisesRegex(CrewChiefError, "live-data path"):
            self.fixture.prepare(
                "working",
                base=self.fixture.head,
                head=self.fixture.head,
                include_worktree=True,
                authorized_untracked=("data/live.json",),
            )

    def test_mission_path_outside_repository_is_rejected(self):
        outside = self.fixture.inputs / "mission.md"
        outside.write_text("# outside\n", encoding="utf-8")
        with self.assertRaisesRegex(CrewChiefError, "outside the authorized repository"):
            prepare_audit(
                self.fixture.repo,
                mission_record=outside,
                base=self.fixture.base,
                head=self.fixture.head,
                engineer_report=self.fixture.engineer_report,
                evidence_artifacts=[self.fixture.evidence],
                test_claims=self.fixture.claims,
                output_root=Path(self.temporary.name) / "outside-mission",
                clock=lambda: FIXED_TIME,
            )

    def test_missing_engineer_report_is_rejected(self):
        self.fixture.engineer_report.unlink()
        with self.assertRaisesRegex(CrewChiefError, "engineer report"):
            self.fixture.prepare("missing-engineer")

    def test_tampered_frozen_evidence_is_rejected(self):
        result = self.fixture.prepare("envelope")
        diff = Path(result["output_root"]) / "diffs" / "committed.diff"
        diff.write_bytes(diff.read_bytes() + b"tamper")
        with self.assertRaisesRegex(CrewChiefError, "(size|hash) changed"):
            verify_envelope(Path(result["envelope_path"]), clock=lambda: FIXED_TIME)

    def test_tampered_frozen_source_content_is_rejected(self):
        result = self.fixture.prepare("envelope")
        manifest = read_json(Path(result["manifest_path"]))
        source = next(
            item
            for item in manifest["subject"]["source_material"]
            if item["repository_path"] == "src/example.py"
            and item["state"] == "head"
        )
        frozen = Path(result["output_root"]) / source["frozen"]["path"]
        frozen.write_bytes(frozen.read_bytes() + b"tamper")
        with self.assertRaisesRegex(CrewChiefError, "(size|hash) changed"):
            verify_envelope(Path(result["envelope_path"]), clock=lambda: FIXED_TIME)

    def test_missing_frozen_mission_is_rejected(self):
        result = self.fixture.prepare("envelope")
        (Path(result["output_root"]) / "evidence" / "mission-record.md").unlink()
        with self.assertRaisesRegex(CrewChiefError, "frozen mission record"):
            verify_envelope(Path(result["envelope_path"]), clock=lambda: FIXED_TIME)

    def test_missing_evidence_artifact_is_rejected(self):
        result = self.fixture.prepare("envelope")
        (Path(result["output_root"]) / "evidence" / "artifact-001.log").unlink()
        with self.assertRaisesRegex(CrewChiefError, "frozen evidence"):
            verify_envelope(Path(result["envelope_path"]), clock=lambda: FIXED_TIME)

    def test_expired_envelope_is_rejected(self):
        result = self.fixture.prepare("envelope")
        expired = FIXED_TIME + timedelta(hours=1)
        with self.assertRaisesRegex(CrewChiefError, "expired"):
            verify_envelope(Path(result["envelope_path"]), clock=lambda: expired)

    def test_git_drift_after_freezing_is_rejected(self):
        result = self.fixture.prepare("envelope")
        self.fixture.write("src/example.py", "VALUE = 99\n")
        with self.assertRaisesRegex(CrewChiefError, "Git state drifted"):
            verify_envelope(Path(result["envelope_path"]), clock=lambda: FIXED_TIME)

    def test_standard_deep_and_exempt_profiles(self):
        standard = read_json(Path(self.fixture.prepare("standard")["envelope_path"]))
        deep = read_json(Path(self.fixture.prepare("deep", profile="deep")["envelope_path"]))
        exempt = read_json(
            Path(
                self.fixture.prepare(
                    "exempt",
                    profile="exempt",
                    justification="generated status-only refresh",
                    claims={"governance_validation": ["repository validate passed"]},
                )["envelope_path"]
            )
        )
        self.assertEqual(standard["risk_profile"]["name"], "standard")
        self.assertIn("security", deep["risk_profile"]["required_focus"])
        self.assertEqual(exempt["risk_profile"]["name"], "exempt")

    def test_exempt_profile_requires_justification_and_governance_evidence(self):
        with self.assertRaisesRegex(CrewChiefError, "justification"):
            self.fixture.prepare("exempt", profile="exempt")
        with self.assertRaisesRegex(CrewChiefError, "governance validation"):
            self.fixture.prepare(
                "exempt-2", profile="exempt", justification="status only"
            )


class CrewChiefReportTests(unittest.TestCase):
    def setUp(self):
        self.envelope = {
            "audit_id": "a" * 64,
            "envelope_id": "b" * 64,
            "risk_profile": {
                "name": "standard",
                "justification": "",
                "required_focus": list(PROFILE_FOCUS["standard"]),
            },
            "_verified_evidence": {
                "sources": [
                    {
                        "path": "src/example.py",
                        "state": "head",
                        "revision": "1" * 40,
                        "file_type": "regular",
                        "encoding": "utf-8",
                        "line_count": 1,
                        "reference": "source-content/sha256/" + "c" * 64,
                    },
                    {
                        "path": "assets/payload.bin",
                        "state": "head",
                        "revision": "1" * 40,
                        "file_type": "regular",
                        "encoding": "base64",
                        "line_count": None,
                        "reference": "source-content/sha256/" + "d" * 64,
                    },
                ],
                "artifacts": [
                    {
                        "artifact": "mission_record",
                        "reference": "evidence/mission-record.md",
                    },
                    {
                        "artifact": "engineer_report",
                        "reference": "evidence/engineer-report.json",
                    },
                    {
                        "artifact": "test_claims",
                        "reference": "evidence/test-claims.json",
                    },
                    {
                        "artifact": "diff:committed.diff",
                        "reference": "diffs/committed.diff",
                    },
                    {
                        "artifact": "evidence:001",
                        "reference": "evidence/artifact-001.log",
                    },
                ],
                "exempt_governance_validation": False,
            },
        }

    def test_schema_accepts_pass_report_and_individual_finding(self):
        report = report_for(self.envelope)
        validate_report(self.envelope, report)
        validate_instance("finding-v1.schema.json", finding())

    def test_schema_rejects_missing_exact_evidence(self):
        bad = finding()
        bad["evidence"] = []
        report = report_for(self.envelope, [bad], verdict="FAIL")
        with self.assertRaisesRegex(CrewChiefError, "schema validation"):
            validate_report(self.envelope, report)

    def test_source_evidence_rejects_reversed_line_range(self):
        bad = finding()
        bad["evidence"][0]["line_start"] = 2
        bad["evidence"][0]["line_end"] = 1
        with self.assertRaisesRegex(CrewChiefError, "line range"):
            validate_report(
                self.envelope,
                report_for(self.envelope, [bad], verdict="FAIL"),
            )

    def test_all_risk_profiles_require_complete_declared_coverage(self):
        for name in ("standard", "deep"):
            with self.subTest(profile=name):
                envelope = dict(self.envelope)
                envelope["risk_profile"] = {
                    "name": name,
                    "justification": "",
                    "required_focus": list(PROFILE_FOCUS[name]),
                }
                validate_report(envelope, report_for(envelope))
        exempt = dict(self.envelope)
        exempt["risk_profile"] = {
            "name": "exempt",
            "justification": "Maverick-approved status-only subject",
            "required_focus": list(PROFILE_FOCUS["exempt"]),
        }
        exempt["_verified_evidence"] = {
            **self.envelope["_verified_evidence"],
            "exempt_governance_validation": True,
        }
        validate_report(exempt, report_for(exempt))

    def test_deep_profile_rejects_narrow_scope(self):
        envelope = dict(self.envelope)
        envelope["risk_profile"] = {
            "name": "deep",
            "justification": "",
            "required_focus": list(PROFILE_FOCUS["deep"]),
        }
        with self.assertRaisesRegex(CrewChiefError, "missing required deep"):
            validate_report(envelope, report_for(envelope, scope=["scope"]))

    def test_scope_rejects_missing_duplicate_malformed_and_unrecognized_values(self):
        with self.assertRaisesRegex(CrewChiefError, "missing required standard"):
            validate_report(
                self.envelope,
                report_for(self.envelope, scope=["scope"]),
            )
        duplicate = list(PROFILE_FOCUS["standard"]) + ["scope"]
        with self.assertRaisesRegex(CrewChiefError, "schema validation"):
            validate_report(
                self.envelope,
                report_for(self.envelope, scope=duplicate),
            )
        with self.assertRaisesRegex(CrewChiefError, "schema validation"):
            validate_report(
                self.envelope,
                report_for(
                    self.envelope,
                    scope=[*PROFILE_FOCUS["standard"], "Scope"],
                ),
            )
        malformed = dict(self.envelope)
        malformed["risk_profile"] = {
            **self.envelope["risk_profile"],
            "required_focus": ["scope"],
        }
        with self.assertRaisesRegex(CrewChiefError, "malformed required focus"):
            validate_report(malformed, report_for(malformed, scope=["scope"]))

    def test_exempt_profile_requires_justification_and_bound_evidence(self):
        envelope = dict(self.envelope)
        envelope["risk_profile"] = {
            "name": "exempt",
            "justification": "",
            "required_focus": list(PROFILE_FOCUS["exempt"]),
        }
        with self.assertRaisesRegex(CrewChiefError, "requires a justification"):
            validate_report(envelope, report_for(envelope))
        envelope["risk_profile"]["justification"] = "approved exemption"
        with self.assertRaisesRegex(CrewChiefError, "governance validation"):
            validate_report(envelope, report_for(envelope))

    def test_finding_citations_accept_bound_sources_and_artifacts(self):
        bound = finding()
        bound["evidence"].extend(
            [
                {
                    "kind": "artifact",
                    "artifact": "mission_record",
                    "reference": "evidence/mission-record.md",
                },
                {
                    "kind": "artifact",
                    "artifact": "engineer_report",
                    "reference": "evidence/engineer-report.json",
                },
                {
                    "kind": "artifact",
                    "artifact": "diff:committed.diff",
                    "reference": "diffs/committed.diff",
                },
                {
                    "kind": "artifact",
                    "artifact": "test_claims",
                    "reference": "evidence/test-claims.json",
                },
                {
                    "kind": "artifact",
                    "artifact": "evidence:001",
                    "reference": "evidence/artifact-001.log",
                },
            ]
        )
        validate_report(
            self.envelope,
            report_for(self.envelope, [bound], verdict="FAIL"),
        )

    def test_finding_citations_reject_unfrozen_paths_states_and_lines(self):
        for label, mutation, message in (
            (
                "path",
                lambda item: item.update(path="src/missing.py"),
                "unfrozen source",
            ),
            (
                "state",
                lambda item: item.update(state="base"),
                "unfrozen source",
            ),
            (
                "line",
                lambda item: item.update(line_end=2),
                "exceeds frozen content",
            ),
            (
                "binary",
                lambda item: item.update(path="assets/payload.bin"),
                "requires frozen text",
            ),
        ):
            with self.subTest(case=label):
                bad = finding()
                mutation(bad["evidence"][0])
                with self.assertRaisesRegex(CrewChiefError, message):
                    validate_report(
                        self.envelope,
                        report_for(self.envelope, [bad], verdict="FAIL"),
                    )

    def test_finding_citations_reject_unknown_artifact_identifiers(self):
        bad = finding()
        bad["evidence"] = [
            {
                "kind": "artifact",
                "artifact": "evidence:999",
                "reference": "evidence/artifact-999.log",
            }
        ]
        with self.assertRaisesRegex(CrewChiefError, "unknown frozen artifact"):
            validate_report(
                self.envelope,
                report_for(self.envelope, [bad], verdict="FAIL"),
            )

    def test_pass_requires_no_findings(self):
        report = report_for(self.envelope, [finding()], verdict="PASS")
        with self.assertRaisesRegex(CrewChiefError, "verdict must be FAIL"):
            validate_report(self.envelope, report)

    def test_low_and_advisory_findings_are_non_blocking_advisories(self):
        findings = [
            finding("CC-0001", severity="low", blocking=False),
            finding("CC-0002", severity="advisory", blocking=False),
        ]
        report = report_for(
            self.envelope, findings, verdict="PASS_WITH_ADVISORIES"
        )
        validate_report(self.envelope, report)

    def test_medium_finding_requires_rationale_and_fail_verdict(self):
        no_rationale = finding(severity="medium", blocking=False)
        with self.assertRaisesRegex(CrewChiefError, "blocking rationale"):
            validate_report(
                self.envelope,
                report_for(self.envelope, [no_rationale], verdict="FAIL"),
            )
        explained = finding(
            severity="medium",
            blocking=False,
            rationale="Non-blocking because the path is not executed, but medium remains FAIL.",
        )
        validate_report(
            self.envelope,
            report_for(self.envelope, [explained], verdict="FAIL"),
        )

    def test_critical_and_high_are_always_blocking(self):
        for severity in ("critical", "high"):
            with self.subTest(severity=severity):
                report = report_for(
                    self.envelope,
                    [finding(severity=severity, blocking=False)],
                    verdict="FAIL",
                )
                with self.assertRaisesRegex(CrewChiefError, "must be blocking"):
                    validate_report(self.envelope, report)

    def test_blocked_requires_control_reason(self):
        validate_report(
            self.envelope,
            report_for(
                self.envelope,
                verdict="BLOCKED",
                blocked=["mission evidence was missing"],
            ),
        )
        with self.assertRaisesRegex(CrewChiefError, "verdict must be PASS"):
            validate_report(
                self.envelope,
                report_for(self.envelope, verdict="BLOCKED"),
            )

    def test_every_finding_requires_exactly_one_disposition(self):
        report = report_for(
            self.envelope, [finding()], verdict="FAIL"
        )
        with self.assertRaisesRegex(CrewChiefError, "exactly one disposition"):
            reconcile_report(self.envelope, report, [], clock=lambda: FIXED_TIME)

    def test_resolved_blocking_finding_is_approval_ready(self):
        report = report_for(self.envelope, [finding()], verdict="FAIL")
        package = reconcile_report(
            self.envelope,
            report,
            [
                {
                    "finding_id": "CC-0001",
                    "disposition": "resolved",
                    "summary": "Corrected the defect.",
                    "correction_evidence": ["src/example.py:1"],
                    "validation_results": ["focused test passed"],
                }
            ],
            clock=lambda: FIXED_TIME,
        )
        self.assertTrue(package["reconciliation_complete"])
        self.assertTrue(package["approval_ready"])
        validate_reconciliation(package, report)

    def test_disputed_blocking_finding_is_deliverable_but_not_approval_ready(self):
        report = report_for(self.envelope, [finding()], verdict="FAIL")
        package = reconcile_report(
            self.envelope,
            report,
            [
                {
                    "finding_id": "CC-0001",
                    "disposition": "disputed_with_evidence",
                    "summary": "The cited path is unreachable.",
                    "counter_evidence": ["tests/example.py:10"],
                    "reasoning": "The exact test proves the branch cannot execute.",
                }
            ],
            clock=lambda: FIXED_TIME,
        )
        self.assertTrue(package["reconciliation_complete"])
        self.assertFalse(package["approval_ready"])

    def test_escalated_blocking_finding_is_not_approval_ready(self):
        report = report_for(self.envelope, [finding()], verdict="FAIL")
        package = reconcile_report(
            self.envelope,
            report,
            [
                {
                    "finding_id": "CC-0001",
                    "disposition": "escalated_to_maverick",
                    "summary": "A scope decision is reserved.",
                    "unresolved_issue": "Compatibility behavior is ambiguous.",
                    "impact": "Approval could preserve or remove the surface.",
                    "decision_requested": "Select the intended compatibility policy.",
                }
            ],
            clock=lambda: FIXED_TIME,
        )
        self.assertFalse(package["approval_ready"])

    def test_resolved_disposition_requires_correction_and_validation_evidence(self):
        report = report_for(self.envelope, [finding()], verdict="FAIL")
        with self.assertRaisesRegex(CrewChiefError, "correction evidence"):
            reconcile_report(
                self.envelope,
                report,
                [
                    {
                        "finding_id": "CC-0001",
                        "disposition": "resolved",
                        "summary": "Claimed resolution without proof.",
                    }
                ],
                clock=lambda: FIXED_TIME,
            )


class CrewChiefServiceSchemaTests(unittest.TestCase):
    def setUp(self):
        self.canonical_report = bundled_report_schema()
        self.service_report = project_service_schema(self.canonical_report)
        self.envelope = {
            "audit_id": "a" * 64,
            "envelope_id": "b" * 64,
            "risk_profile": {
                "name": "standard",
                "justification": "",
                "required_focus": list(PROFILE_FOCUS["standard"]),
            },
            "_verified_evidence": {
                "sources": [
                    {
                        "path": "src/example.py",
                        "state": "head",
                        "revision": "1" * 40,
                        "file_type": "regular",
                        "encoding": "utf-8",
                        "line_count": 1,
                        "reference": "source-content/sha256/" + "c" * 64,
                    }
                ],
                "artifacts": [],
                "exempt_governance_validation": False,
            },
        }

    @staticmethod
    def schema_keywords(value):
        if isinstance(value, dict):
            for name, child in value.items():
                yield name
                yield from CrewChiefServiceSchemaTests.schema_keywords(child)
        elif isinstance(value, list):
            for child in value:
                yield from CrewChiefServiceSchemaTests.schema_keywords(child)

    def service_round_trip(self, canonical):
        service_value = canonical_to_service_output(
            canonical, self.canonical_report
        )
        validate_service_instance(self.service_report, service_value)
        normalized = normalize_service_output(
            service_value, self.canonical_report
        )
        self.assertEqual(normalized, canonical)
        validate_report(self.envelope, normalized)
        return service_value

    def test_projection_types_consts_enums_and_supported_composition(self):
        validate_service_schema(self.service_report)
        self.assertEqual(
            self.service_report["properties"]["schema_version"],
            {"type": "string", "const": "1.0"},
        )
        context = self.service_report["properties"]["reviewer_context"]
        self.assertEqual(
            context["properties"]["fresh_session"],
            {"type": "boolean", "const": True},
        )
        self.assertEqual(
            self.service_report["properties"]["verdict"]["type"], "string"
        )
        scope_items = self.service_report["properties"]["audit_scope"]["items"]
        self.assertEqual(scope_items["type"], "string")
        keywords = set(self.schema_keywords(self.service_report))
        self.assertNotIn("oneOf", keywords)
        self.assertNotIn("uniqueItems", keywords)
        self.assertIn("anyOf", keywords)

    def test_optional_fields_are_required_nullable_and_normalize_safely(self):
        finding_schema = self.service_report["$defs"]["finding"]
        self.assertIn("blocking_rationale", finding_schema["required"])
        self.assertEqual(
            finding_schema["properties"]["blocking_rationale"]["type"],
            ["null", "string"],
        )
        source_schema = self.service_report["$defs"]["sourceEvidence"]
        self.assertIn("detail", source_schema["required"])
        canonical = report_for(
            self.envelope,
            [finding(severity="low", blocking=False)],
            verdict="PASS_WITH_ADVISORIES",
        )
        canonical["findings"][0]["evidence"][0].pop("detail")
        service_value = self.service_round_trip(canonical)
        self.assertIsNone(service_value["findings"][0]["blocking_rationale"])
        self.assertIsNone(service_value["findings"][0]["evidence"][0]["detail"])

    def test_pass_blocking_and_nonblocking_reports_round_trip(self):
        reports = (
            report_for(self.envelope),
            report_for(self.envelope, [finding()], verdict="FAIL"),
            report_for(
                self.envelope,
                [finding(severity="advisory", blocking=False)],
                verdict="PASS_WITH_ADVISORIES",
            ),
        )
        for report in reports:
            with self.subTest(verdict=report["verdict"]):
                self.service_round_trip(report)

    def test_bootstrap_schema_binds_exact_dynamic_values(self):
        canonical = read_json(
            ROOT / "tools/crew_chief/schemas/bootstrap-report-v1.schema.json"
        )
        schema = bind_bootstrap_service_schema(
            canonical,
            audit_id="a" * 64,
            envelope_id="b" * 64,
            reviewed_commit="c" * 40,
        )
        validate_service_schema(schema)
        for name, expected in (
            ("audit_id", "a" * 64),
            ("envelope_id", "b" * 64),
            ("reviewed_commit", "c" * 40),
        ):
            self.assertEqual(schema["properties"][name]["type"], "string")
            self.assertEqual(schema["properties"][name]["const"], expected)
        keywords = set(self.schema_keywords(schema))
        self.assertNotIn("uniqueItems", keywords)
        self.assertNotIn("pattern", keywords)
        self.assertNotIn("minLength", keywords)

    def test_preflight_rejects_old_and_malformed_service_schemas(self):
        valid = {
            "type": "object",
            "additionalProperties": False,
            "required": ["statement"],
            "properties": {
                "statement": {
                    "const": "This bootstrap audit is not a Crew Chief audit."
                }
            },
        }
        cases = {
            "untyped const": valid,
            "untyped enum": {
                **valid,
                "properties": {"statement": {"enum": ["PASS", "FAIL"]}},
            },
            "missing required": {
                **valid,
                "required": [],
                "properties": {"statement": {"type": "string"}},
            },
            "additional properties": {
                **valid,
                "additionalProperties": True,
                "properties": {"statement": {"type": "string"}},
            },
            "oneOf": {
                **valid,
                "properties": {
                    "statement": {
                        "oneOf": [{"type": "string"}, {"type": "null"}]
                    }
                },
            },
            "uniqueItems": {
                **valid,
                "properties": {
                    "statement": {
                        "type": "array",
                        "uniqueItems": True,
                        "items": {"type": "string"},
                    }
                },
            },
            "invalid ref": {
                **valid,
                "properties": {"statement": {"$ref": "#/$defs/missing"}},
            },
            "malformed": {
                **valid,
                "properties": {"statement": {"type": 7}},
            },
        }
        for label, schema in cases.items():
            with self.subTest(case=label):
                with self.assertRaises(CrewChiefError):
                    validate_service_schema(schema)

    def test_service_projection_does_not_weaken_canonical_invariants(self):
        duplicate_scope = report_for(
            self.envelope,
            scope=[*PROFILE_FOCUS["standard"], "scope"],
        )
        duplicate_findings = report_for(
            self.envelope,
            [finding(), finding()],
            verdict="FAIL",
        )
        for label, report, message in (
            ("scope", duplicate_scope, "schema validation"),
            ("finding", duplicate_findings, "finding IDs must be unique"),
        ):
            with self.subTest(case=label):
                service_value = canonical_to_service_output(
                    report, self.canonical_report
                )
                validate_service_instance(self.service_report, service_value)
                normalized = normalize_service_output(
                    service_value, self.canonical_report
                )
                with self.assertRaisesRegex(CrewChiefError, message):
                    validate_report(self.envelope, normalized)


class CrewChiefRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.fixture = FixtureRepository(Path(self.temporary.name))
        self.prepared = self.fixture.prepare("envelope")
        self.envelope_path = Path(self.prepared["envelope_path"])

    def tearDown(self):
        self.temporary.cleanup()

    def capabilities(self, selector=False):
        return CodexCapabilities(
            executable="/fixture/codex",
            version="codex-cli fixture",
            exec_flags=(
                *sorted(_REQUIRED_EXEC_FLAGS),
            ),
            features=(
                "apps",
                "browser_use",
                "computer_use",
                "image_generation",
                "multi_agent",
                "personality",
                "plugins",
                "shell_snapshot",
                "shell_tool",
            ),
            shell_tool_control=True,
            custom_agent_selector=selector,
        )

    def test_launch_command_is_an_argument_array_with_read_only_controls(self):
        workspace = Path(self.temporary.name) / "workspace with spaces"
        schema = workspace / "schema.json"
        report = workspace / "report.json"
        command = build_launch_command(self.capabilities(), workspace, schema, report)
        self.assertIsInstance(command, list)
        self.assertIn("--ephemeral", command)
        self.assertIn("--skip-git-repo-check", command)
        self.assertIn("--ignore-user-config", command)
        self.assertIn("read-only", command)
        self.assertIn('approval_policy="never"', command)
        self.assertEqual(
            command[
                command.index(
                    "--disable", command.index('approval_policy="never"')
                )
                + 1
            ],
            "apps",
        )
        self.assertIn("shell_tool", command)
        self.assertIn(str(workspace), command)
        self.assertNotIn("--agent", command)
        self.assertNotIn(";", command)

    def test_bootstrap_uses_the_same_trusted_directory_control(self):
        command = build_ordinary_bootstrap_launch_command(
            self.capabilities(),
            Path("/tmp/frozen-non-git-workspace"),
            Path("/tmp/schema.json"),
            Path("/tmp/report.json"),
        )
        self.assertEqual(command[0:3], [
            "/fixture/codex",
            "exec",
            "--skip-git-repo-check",
        ])
        self.assertNotIn("--agent", command)

    def test_normal_command_tampering_fails_before_process_runner(self):
        invocation = prepare_review_workspace(
            self.envelope_path,
            Path(self.temporary.name) / "tampered-command-review",
            detector=lambda _: self.capabilities(selector=True),
            clock=lambda: FIXED_TIME,
        )

        def omit(value):
            value["argv"].remove("--skip-git-repo-check")

        def duplicate(value):
            position = value["argv"].index("--skip-git-repo-check")
            value["argv"].insert(position, "--skip-git-repo-check")

        def add(value):
            value["argv"].insert(-1, "--future-control")

        def reorder(value):
            position = value["argv"].index("--ephemeral")
            value["argv"][position], value["argv"][position + 1] = (
                value["argv"][position + 1],
                value["argv"][position],
            )

        def weaken(value):
            position = value["argv"].index("read-only")
            value["argv"][position] = "workspace-write"

        def alter_executable(value):
            value["capabilities"]["executable"] = "/fixture/altered-codex"

        for label, mutation in (
            ("omitted", omit),
            ("duplicated", duplicate),
            ("added", add),
            ("reordered", reorder),
            ("weakened", weaken),
            ("altered executable", alter_executable),
        ):
            with self.subTest(case=label):
                candidate = copy.deepcopy(invocation)
                mutation(candidate)
                fake_runner = mock.Mock()
                with self.assertRaisesRegex(
                    CrewChiefError, "invocation argv changed after preparation"
                ):
                    execute_prepared_review(
                        self.envelope_path,
                        candidate,
                        runner=fake_runner,
                        clock=lambda: FIXED_TIME,
                    )
                fake_runner.assert_not_called()

    def test_every_known_prohibited_feature_is_explicitly_disabled(self):
        capabilities = self.capabilities()
        capabilities = CodexCapabilities(
            **{
                **capabilities.__dict__,
                "features": _DISABLED_REVIEW_FEATURES,
            }
        )
        command = build_launch_command(
            capabilities,
            Path("/tmp/workspace"),
            Path("/tmp/schema.json"),
            Path("/tmp/report.json"),
        )
        disabled = {
            command[index + 1]
            for index, value in enumerate(command[:-1])
            if value == "--disable"
        }
        self.assertEqual(disabled, set(_DISABLED_REVIEW_FEATURES))

    def test_permitted_inventory_is_empty_and_personality_is_disabled(self):
        capabilities = CodexCapabilities(
            executable="/fixture/codex",
            version="codex-cli fixture",
            exec_flags=self.capabilities().exec_flags,
            features=("personality", "shell_tool"),
            shell_tool_control=True,
            custom_agent_selector=False,
        )
        command = build_launch_command(
            capabilities,
            Path("/tmp/workspace"),
            Path("/tmp/schema.json"),
            Path("/tmp/report.json"),
        )
        self.assertEqual(_PERMITTED_REVIEW_FEATURES, ())
        self.assertIn("personality", command)
        self.assertIn("shell_tool", command)

    def test_tampered_prepared_capabilities_fail_before_process_runner(self):
        invocation = prepare_review_workspace(
            self.envelope_path,
            Path(self.temporary.name) / "tampered-capabilities-review",
            detector=lambda _: self.capabilities(selector=True),
            clock=lambda: FIXED_TIME,
        )
        invocation["capabilities"]["features"] = tuple(
            feature
            for feature in invocation["capabilities"]["features"]
            if feature != "shell_tool"
        )
        fake_runner = mock.Mock()
        with self.assertRaisesRegex(
            CrewChiefError, "invocation argv changed after preparation"
        ):
            execute_prepared_review(
                self.envelope_path,
                invocation,
                runner=fake_runner,
                clock=lambda: FIXED_TIME,
            )
        fake_runner.assert_not_called()

    def test_unknown_enabled_feature_fails_before_process_runner(self):
        invocation = prepare_review_workspace(
            self.envelope_path,
            Path(self.temporary.name) / "review",
            detector=lambda _: self.capabilities(selector=True),
            clock=lambda: FIXED_TIME,
        )
        invocation["capabilities"]["features"] = (
            *invocation["capabilities"]["features"],
            "future_remote_tool",
        )
        fake_runner = mock.Mock()
        with self.assertRaisesRegex(
            CrewChiefError, "unsupported enabled features: future_remote_tool"
        ):
            execute_prepared_review(
                self.envelope_path,
                invocation,
                runner=fake_runner,
                clock=lambda: FIXED_TIME,
            )
        fake_runner.assert_not_called()

    def test_supported_selector_uses_project_agent(self):
        command = build_launch_command(
            self.capabilities(selector=True),
            Path("/tmp/workspace"),
            Path("/tmp/schema.json"),
            Path("/tmp/report.json"),
        )
        self.assertEqual(command[command.index("--agent") + 1], "crew_chief")

    def test_unsupported_selector_records_honest_fallback(self):
        invocation = prepare_review_workspace(
            self.envelope_path,
            Path(self.temporary.name) / "review",
            detector=lambda _: self.capabilities(selector=False),
            clock=lambda: FIXED_TIME,
        )
        self.assertEqual(invocation["execution_mode"], "fresh-session-fallback")
        self.assertFalse(invocation["live_audit_performed"])
        self.assertIn("No supported", invocation["automation_limitation"])
        prompt = Path(invocation["prompt_path"]).read_text(encoding="utf-8")
        self.assertIn("shell tool is disabled", prompt)
        self.assertIn("diff --git", prompt)
        self.assertIn("source-content/sha256/", prompt)
        self.assertIn("encoding=base64", prompt)
        self.assertIn("AP9oZWFkCg==", prompt)

    def test_oversize_payload_fails_before_model_invocation(self):
        detector = mock.Mock(return_value=self.capabilities(selector=True))
        with mock.patch(
            "tools.crew_chief.runner._MAX_EMBEDDED_EVIDENCE_BYTES", 64
        ):
            with self.assertRaisesRegex(CrewChiefError, "16 MiB"):
                prepare_review_workspace(
                    self.envelope_path,
                    Path(self.temporary.name) / "oversize-review",
                    detector=detector,
                    clock=lambda: FIXED_TIME,
                )
        detector.assert_called_once_with("codex")

    def test_tampered_review_workspace_control_is_rejected(self):
        invocation = prepare_review_workspace(
            self.envelope_path,
            Path(self.temporary.name) / "review",
            detector=lambda _: self.capabilities(selector=True),
            clock=lambda: FIXED_TIME,
        )
        (Path(invocation["workspace"]) / "AGENTS.md").write_text(
            "tampered\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(CrewChiefError, "binding size changed"):
            execute_prepared_review(
                self.envelope_path,
                invocation,
                runner=lambda *_args, **_kwargs: subprocess.CompletedProcess(
                    [], 0, "", ""
                ),
                clock=lambda: FIXED_TIME,
            )

    def test_bundled_output_schema_accepts_a_valid_report(self):
        invocation = prepare_review_workspace(
            self.envelope_path,
            Path(self.temporary.name) / "review",
            detector=lambda _: self.capabilities(selector=True),
            clock=lambda: FIXED_TIME,
        )
        schema_path = Path(invocation["schema_path"])
        schema = read_json(schema_path)
        canonical_schema = read_json(Path(invocation["canonical_schema_path"]))
        envelope = read_json(self.envelope_path)
        service_value = canonical_to_service_output(
            report_for(envelope, [finding()], verdict="FAIL"),
            canonical_schema,
        )
        validate_service_instance(schema, service_value)
        self.assertEqual(
            normalize_service_output(service_value, canonical_schema),
            report_for(envelope, [finding()], verdict="FAIL"),
        )
        self.assertEqual(
            invocation["argv"][invocation["argv"].index("--output-schema") + 1],
            str(schema_path),
        )
        binding = next(
            item
            for item in invocation["workspace_bindings"]
            if item["path"] == "schemas/crew-chief-report.schema.json"
        )
        self.assertEqual(binding["sha256"], sha256_file(schema_path))

    def test_incompatible_final_schema_fails_before_process_runner(self):
        invocation = prepare_review_workspace(
            self.envelope_path,
            Path(self.temporary.name) / "incompatible-schema-review",
            detector=lambda _: self.capabilities(selector=True),
            clock=lambda: FIXED_TIME,
        )
        schema_path = Path(invocation["schema_path"])
        schema = read_json(schema_path)
        schema["properties"]["schema_version"].pop("type")
        write_canonical_json(schema_path, schema)
        invocation["workspace_bindings"] = [
            bind_file(schema_path, "schemas/crew-chief-report.schema.json")
            if item["path"] == "schemas/crew-chief-report.schema.json"
            else item
            for item in invocation["workspace_bindings"]
        ]
        fake_runner = mock.Mock()
        with self.assertRaisesRegex(CrewChiefError, "const lacks"):
            execute_prepared_review(
                self.envelope_path,
                invocation,
                runner=fake_runner,
                clock=lambda: FIXED_TIME,
            )
        fake_runner.assert_not_called()

    def test_missing_codex_is_reported_clearly(self):
        with mock.patch(
            "tools.crew_chief.runner.shutil.which", return_value=None
        ):
            with self.assertRaisesRegex(CrewChiefError, "unavailable"):
                detect_codex_capabilities("/missing/codex")

    def test_capability_detection_uses_help_only(self):
        calls = []

        def fake_runner(arguments, **_kwargs):
            calls.append(arguments)
            if arguments[-1] == "--version":
                return subprocess.CompletedProcess(arguments, 0, "codex-cli fixture\n", "")
            if arguments[-2:] == ["features", "list"]:
                return subprocess.CompletedProcess(
                    arguments,
                    0,
                    "apps stable true\nshell_tool stable true\n",
                    "",
                )
            help_text = " ".join(sorted({
                *_REQUIRED_EXEC_FLAGS,
                "--agent",
            }))
            return subprocess.CompletedProcess(arguments, 0, help_text, "")

        with mock.patch(
            "tools.crew_chief.runner.shutil.which", return_value="/fixture/codex"
        ):
            capabilities = detect_codex_capabilities(
                "codex", runner=fake_runner
            )
        self.assertTrue(capabilities.custom_agent_selector)
        self.assertEqual(
            [call[1:] for call in calls],
            [["--version"], ["exec", "--help"], ["features", "list"]],
        )
        self.assertTrue(all("exec" not in call[1:2] or "--help" in call for call in calls))

    def test_missing_shell_disable_control_fails_closed(self):
        def fake_runner(arguments, **_kwargs):
            if arguments[-1] == "--version":
                return subprocess.CompletedProcess(arguments, 0, "codex-cli fixture\n", "")
            if arguments[-2:] == ["features", "list"]:
                return subprocess.CompletedProcess(
                    arguments, 0, "apps stable true\n", ""
                )
            return subprocess.CompletedProcess(
                arguments,
                0,
                " ".join(sorted({
                    *_REQUIRED_EXEC_FLAGS,
                })),
                "",
            )

        with mock.patch(
            "tools.crew_chief.runner.shutil.which", return_value="/fixture/codex"
        ):
            with self.assertRaisesRegex(CrewChiefError, "shell-tool"):
                detect_codex_capabilities("codex", runner=fake_runner)

    def test_missing_trusted_directory_control_fails_closed(self):
        def fake_runner(arguments, **_kwargs):
            if arguments[-1] == "--version":
                return subprocess.CompletedProcess(
                    arguments, 0, "codex-cli fixture\n", ""
                )
            if arguments[-2:] == ["features", "list"]:
                return subprocess.CompletedProcess(
                    arguments, 0, "shell_tool stable true\n", ""
                )
            flags = _REQUIRED_EXEC_FLAGS - {"--skip-git-repo-check"}
            return subprocess.CompletedProcess(
                arguments, 0, " ".join(sorted(flags)), ""
            )

        with mock.patch(
            "tools.crew_chief.runner.shutil.which", return_value="/fixture/codex"
        ):
            with self.assertRaisesRegex(
                CrewChiefError, "--skip-git-repo-check"
            ):
                detect_codex_capabilities("codex", runner=fake_runner)

    def test_trusted_directory_capability_requires_the_exact_flag(self):
        def fake_runner(arguments, **_kwargs):
            if arguments[-1] == "--version":
                return subprocess.CompletedProcess(
                    arguments, 0, "codex-cli fixture\n", ""
                )
            if arguments[-2:] == ["features", "list"]:
                return subprocess.CompletedProcess(
                    arguments, 0, "shell_tool stable true\n", ""
                )
            flags = _REQUIRED_EXEC_FLAGS - {"--skip-git-repo-check"}
            help_text = " ".join(
                [*sorted(flags), "--skip-git-repo-check-unsafe"]
            )
            return subprocess.CompletedProcess(arguments, 0, help_text, "")

        with mock.patch(
            "tools.crew_chief.runner.shutil.which", return_value="/fixture/codex"
        ):
            with self.assertRaisesRegex(
                CrewChiefError, "--skip-git-repo-check"
            ):
                detect_codex_capabilities("codex", runner=fake_runner)

    def test_failed_or_malformed_feature_detection_fails_closed(self):
        for label, result in (
            (
                "failed",
                subprocess.CompletedProcess([], 1, "", "unsupported"),
            ),
            (
                "malformed",
                subprocess.CompletedProcess([], 0, "shell_tool stable maybe\n", ""),
            ),
        ):
            with self.subTest(case=label):
                def fake_runner(arguments, **_kwargs):
                    if arguments[-1] == "--version":
                        return subprocess.CompletedProcess(
                            arguments, 0, "codex-cli fixture\n", ""
                        )
                    if arguments[-2:] == ["features", "list"]:
                        return result
                    return subprocess.CompletedProcess(
                        arguments,
                        0,
                        " ".join(sorted({
                            *_REQUIRED_EXEC_FLAGS,
                        })),
                        "",
                    )

                with mock.patch(
                    "tools.crew_chief.runner.shutil.which",
                    return_value="/fixture/codex",
                ):
                    with self.assertRaisesRegex(
                        CrewChiefError, "feature.*(failed|malformed)"
                    ):
                        detect_codex_capabilities("codex", runner=fake_runner)

    def test_duplicate_feature_inventory_fails_closed(self):
        def fake_runner(arguments, **_kwargs):
            if arguments[-1] == "--version":
                return subprocess.CompletedProcess(
                    arguments, 0, "codex-cli fixture\n", ""
                )
            if arguments[-2:] == ["features", "list"]:
                return subprocess.CompletedProcess(
                    arguments,
                    0,
                    "shell_tool stable true\nshell_tool stable true\n",
                    "",
                )
            return subprocess.CompletedProcess(
                arguments, 0, " ".join(sorted(_REQUIRED_EXEC_FLAGS)), ""
            )

        with mock.patch(
            "tools.crew_chief.runner.shutil.which", return_value="/fixture/codex"
        ):
            with self.assertRaisesRegex(CrewChiefError, "duplicated"):
                detect_codex_capabilities("codex", runner=fake_runner)

    @unittest.skipUnless(shutil.which("codex"), "installed Codex CLI unavailable")
    def test_installed_codex_completes_preparation_without_model(self):
        invocation = prepare_review_workspace(
            self.envelope_path,
            Path(self.temporary.name) / "installed-cli-review",
            clock=lambda: FIXED_TIME,
        )
        self.assertFalse(invocation["live_audit_performed"])
        self.assertEqual(invocation["execution_mode"], "fresh-session-fallback")
        features = set(invocation["capabilities"]["features"])
        command = invocation["argv"]
        disabled = {
            command[index + 1]
            for index, value in enumerate(command[:-1])
            if value == "--disable"
        }
        self.assertEqual(disabled, features)
        self.assertFalse(Path(invocation["report_path"]).exists())

    def test_missing_authentication_fails_without_consuming(self):
        invocation = prepare_review_workspace(
            self.envelope_path,
            Path(self.temporary.name) / "review",
            detector=lambda _: self.capabilities(selector=True),
            clock=lambda: FIXED_TIME,
        )

        def unauthenticated(arguments, **_kwargs):
            return subprocess.CompletedProcess(arguments, 1, "", "not logged in")

        with self.assertRaisesRegex(CrewChiefError, "authentication"):
            execute_prepared_review(
                self.envelope_path,
                invocation,
                runner=unauthenticated,
                clock=lambda: FIXED_TIME,
            )
        self.assertFalse(
            (Path(invocation["workspace"]) / ".crew-chief-consumed.json").exists()
        )

    def test_invalid_retention_controls_fail_before_authentication_or_consumption(self):
        invocation = prepare_review_workspace(
            self.envelope_path,
            Path(self.temporary.name) / "invalid-retention-review",
            detector=lambda _: self.capabilities(selector=True),
            clock=lambda: FIXED_TIME,
        )
        runner = mock.Mock()
        with self.assertRaisesRegex(CrewChiefError, "at least one"):
            execute_prepared_review(
                self.envelope_path,
                invocation,
                max_retained_reports=0,
                runner=runner,
                clock=lambda: FIXED_TIME,
            )
        runner.assert_not_called()
        self.assertFalse(
            (Path(invocation["workspace"]) / ".crew-chief-consumed.json").exists()
        )

    def test_malformed_retention_report_id_fails_before_process(self):
        invocation = prepare_review_workspace(
            self.envelope_path,
            Path(self.temporary.name) / "malformed-report-id-review",
            detector=lambda _: self.capabilities(selector=True),
            clock=lambda: FIXED_TIME,
        )
        invocation["report_id"] = "../escape"
        runner = mock.Mock()
        with self.assertRaisesRegex(CrewChiefError, "ID is malformed"):
            execute_prepared_review(
                self.envelope_path,
                invocation,
                runner=runner,
                clock=lambda: FIXED_TIME,
            )
        runner.assert_not_called()

    def test_atomic_consumption_prevents_reuse(self):
        invocation = prepare_review_workspace(
            self.envelope_path,
            Path(self.temporary.name) / "review",
            detector=lambda _: self.capabilities(selector=True),
            clock=lambda: FIXED_TIME,
        )
        envelope = read_json(self.envelope_path)

        def successful(arguments, **_kwargs):
            if arguments[-2:] == ["login", "status"]:
                return subprocess.CompletedProcess(arguments, 0, "logged in", "")
            self.assertTrue(Path(invocation["report_path"]).parent.is_dir())
            canonical_schema = read_json(Path(invocation["canonical_schema_path"]))
            Path(invocation["report_path"]).write_text(
                json.dumps(
                    canonical_to_service_output(
                        report_for(envelope), canonical_schema
                    )
                ),
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(arguments, 0, "{}", "")

        record = execute_prepared_review(
            self.envelope_path,
            invocation,
            runner=successful,
            clock=lambda: FIXED_TIME,
        )
        self.assertTrue(record["live_audit_performed"])
        with self.assertRaisesRegex(CrewChiefError, "already consumed"):
            execute_prepared_review(
                self.envelope_path,
                invocation,
                runner=successful,
                clock=lambda: FIXED_TIME,
            )

    def test_failed_run_record_write_never_triggers_retention(self):
        invocation = prepare_review_workspace(
            self.envelope_path,
            Path(self.temporary.name) / "failed-write-review",
            detector=lambda _: self.capabilities(selector=True),
            clock=lambda: FIXED_TIME,
        )
        envelope = read_json(self.envelope_path)

        def successful(arguments, **_kwargs):
            if arguments[-2:] == ["login", "status"]:
                return subprocess.CompletedProcess(arguments, 0, "logged in", "")
            canonical_schema = read_json(Path(invocation["canonical_schema_path"]))
            Path(invocation["report_path"]).write_text(
                json.dumps(
                    canonical_to_service_output(
                        report_for(envelope), canonical_schema
                    )
                ),
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(arguments, 0, "{}", "")

        def fail_run_record(path, value):
            if path.name == "run-record.json":
                raise OSError("synthetic run-record write failure")
            write_canonical_json(path, value)

        with (
            mock.patch(
                "tools.crew_chief.runner.write_canonical_json",
                side_effect=fail_run_record,
            ),
            mock.patch("tools.crew_chief.runner.prune_reports") as prune,
        ):
            with self.assertRaisesRegex(OSError, "run-record write failure"):
                execute_prepared_review(
                    self.envelope_path,
                    invocation,
                    runner=successful,
                    clock=lambda: FIXED_TIME,
                )
        prune.assert_not_called()
        bundle = Path(invocation["output_bundle"])
        self.assertFalse((bundle / "run-record.json").exists())
        self.assertEqual(read_json(bundle / "retention-report.json")["state"], "running")

    def test_repository_mutation_during_review_is_rejected(self):
        invocation = prepare_review_workspace(
            self.envelope_path,
            Path(self.temporary.name) / "review",
            detector=lambda _: self.capabilities(selector=True),
            clock=lambda: FIXED_TIME,
        )

        def mutating(arguments, **_kwargs):
            if arguments[-2:] == ["login", "status"]:
                return subprocess.CompletedProcess(arguments, 0, "logged in", "")
            self.fixture.write("unexpected.txt", "mutation\n")
            return subprocess.CompletedProcess(arguments, 0, "{}", "")

        with self.assertRaisesRegex(CrewChiefError, "unexpected repository mutation"):
            execute_prepared_review(
                self.envelope_path,
                invocation,
                runner=mutating,
                clock=lambda: FIXED_TIME,
            )

    def test_timeout_is_consumed_and_preserves_redacted_diagnostic(self):
        invocation = prepare_review_workspace(
            self.envelope_path,
            Path(self.temporary.name) / "review",
            detector=lambda _: self.capabilities(selector=True),
            clock=lambda: FIXED_TIME,
        )

        def timing_out(arguments, **_kwargs):
            if arguments[-2:] == ["login", "status"]:
                return subprocess.CompletedProcess(arguments, 0, "logged in", "")
            raise subprocess.TimeoutExpired(
                arguments, 1, stderr="token=do-not-preserve"
            )

        with self.assertRaisesRegex(CrewChiefError, "time limit"):
            execute_prepared_review(
                self.envelope_path,
                invocation,
                runner=timing_out,
                clock=lambda: FIXED_TIME,
            )
        workspace = Path(invocation["workspace"])
        self.assertTrue((workspace / ".crew-chief-consumed.json").is_file())
        diagnostic = (
            Path(invocation["output_bundle"]) / "codex-stderr.log"
        ).read_text(
            encoding="utf-8"
        )
        self.assertNotIn("do-not-preserve", diagnostic)
        self.assertIn("[REDACTED]", diagnostic)


class CrewChiefGovernanceTests(unittest.TestCase):
    def test_schemas_and_governance_are_discoverable(self):
        self.assertEqual(governance.validate_schemas_and_first_reads(), [])
        self.assertTrue((ROOT / "tools/crew_chief/schemas/report-v1.schema.json").is_file())
        self.assertTrue(
            (
                ROOT
                / "tools/crew_chief/schemas/bootstrap-report-v1.schema.json"
            ).is_file()
        )
        self.assertTrue((ROOT / ".codex/agents/crew-chief.toml").is_file())

    def test_no_test_invokes_a_real_model_or_network(self):
        source = Path(__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_roots = {
            alias.name.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in (
                node.names
                if isinstance(node, ast.Import)
                else [ast.alias(name=node.module or "")]
            )
        }
        self.assertNotRegex(
            source,
            r"subprocess\.run\(\s*\[\s*['\"]codex['\"]\s*,\s*['\"]exec['\"]",
        )
        self.assertTrue({"requests", "urllib", "httpx"}.isdisjoint(imported_roots))

    def test_canonical_json_hashing_is_sorted_and_compact(self):
        left = canonical_json_bytes({"b": 2, "a": 1})
        right = canonical_json_bytes({"a": 1, "b": 2})
        self.assertEqual(left, b'{"a":1,"b":2}')
        self.assertEqual(sha256_bytes(left), sha256_bytes(right))


if __name__ == "__main__":
    unittest.main()
