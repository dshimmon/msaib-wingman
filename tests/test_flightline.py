import io
import json
import os
import signal
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from jsonschema import Draft202012Validator

from tools.flightline import guard
from tools.flightline.flightline import (
    CANARY,
    FlightlineError,
    _event_counts,
    _git_metadata_snapshot,
    _sanitized_environment,
    _supervise_process,
    _claim_auditor_authorization,
    _preflight_comparison,
    _redact_command,
    _security_relevant_refs,
    _verify_foreground_preflight,
    _workspace_tree,
    build_launch_environment,
    build_launch_command,
    build_permission_profile,
    issue_auditor_envelope,
    run_auditor_schema_preflight,
    sha256_file,
    validate_envelope,
    verify_auditor_schema_preflight,
    verify_controller_authorization,
)


BASELINE = "4cabb431829a29357c6ead8c00fd7539b7e91fa7"


class FlightlineTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.repo = root / "foreground"
        self.worktree = root / "worktree"
        self.output = root / "output"
        self.schema_root = Path(__file__).resolve().parents[1] / "tools" / "flightline" / "schemas"
        self.repo.mkdir()
        self.worktree.mkdir()
        self.output.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def envelope(self, role="development-engineer"):
        schema_name = "engineer-report.schema.json" if role == "development-engineer" else "auditor-report.schema.json"
        value = {
            "schema_version": "1.1",
            "mission": {
                "number": "SETUP",
                "name": "Flightline",
                "call_sign": "Flightline",
                "objective": "Validate controls",
            },
            "role": role,
            "state": "APPROVED",
            "canary": CANARY,
            "baseline_commit": BASELINE,
            "repository_root": str(self.repo),
            "worktree_path": str(self.worktree),
            "allowed_write_paths": ["src"] if role == "development-engineer" else [],
            "protected_data_paths": [str(self.repo / "data")],
            "credential_paths": [str(self.repo / ".env")],
            "approved_command_prefixes": [["rg"], ["git", "status"]],
            "allowed_tools": ["update_plan"],
            "network_policy": "off",
            "credential_policy": "none-mounted",
            "budgets": {
                "time_seconds": 60,
                "token_budget": 1000,
                "command_budget": 10,
                "max_changed_files": 5,
            },
            "allowed_temp_paths": [str(self.output)],
            "acceptance_criteria": ["safe"],
            "explicit_exclusions": ["commit"],
            "stop_conditions": ["control failure"],
            "authorities": {
                "stage": False,
                "commit": False,
                "push": False,
                "merge": False,
                "rebase": False,
                "tag": False,
                "release": False,
                "deploy": False,
                "destructive": False,
            },
            "report_schema": str(self.schema_root / schema_name),
            "output_root": str(self.output),
            "allow_deletions": False,
        }
        if role == "independent-auditor":
            control = Path(self.temp.name) / "controller"
            value["state"] = "PREFLIGHTED"
            value["prompt_file"] = str(control / "auditor-prompt.md")
            value["prompt_sha256"] = "1" * 64
            value["runtime_paths"] = [str(self.repo / ".venv" / "flightline-py312")]
            value["controller_authorization"] = {
                "issuer": "flightline-controller",
                "authorization_id": "2" * 64,
                "issued_at_epoch_seconds": 1,
                "expires_at_epoch_seconds": 3601,
                "use_policy": "single-use",
                "issuance_record": str(control / "controller-issuance.json"),
                "consumption_record": str(control / "controller-consumed.json"),
            }
            value["frozen_subject"] = {
                name: {"path": str(control / (name + ".json")), "sha256": "3" * 64}
                for name in (
                    "frozen_manifest",
                    "frozen_diff",
                    "evidence_package",
                    "audit_workspace_manifest",
                    "foreground_preflight",
                )
            }
        return value

    def auditor_report(self):
        analysis = {"summary": "schema compatibility fixture", "evidence": []}
        return {
            "canary": CANARY,
            "role": "independent-auditor",
            "baseline_commit": BASELINE,
            "authorization_id": "0" * 64,
            "activation_proof": {
                "controller_issued": True,
                "state": "PREFLIGHTED",
                "unused_at_launch": True,
                "environment_bindings_active": True,
                "repository_write_denied": True,
                "git_mutation_denied": True,
                "credential_access_denied": True,
                "protected_data_access_denied": True,
                "network_access_denied": True,
            },
            "verdict": "BLOCKED",
            "findings": [
                {
                    "severity": "INFORMATIONAL",
                    "summary": "schema compatibility fixture",
                    "evidence": [],
                    "recommendation": "none",
                }
            ],
            "acceptance_criteria": [
                {
                    "criterion": "schema compatibility",
                    "result": "PASS",
                    "evidence": [],
                }
            ],
            "independent_validation": [
                {
                    "command": "none (schema compatibility fixture)",
                    "result": "NOT_RUN",
                    "evidence": "no command was run",
                }
            ],
            "architecture_analysis": dict(analysis),
            "isolation_analysis": dict(analysis),
            "compatibility_analysis": dict(analysis),
            "traceability_and_ledger_safety": dict(analysis),
            "repository_hygiene": dict(analysis),
            "documentation_accuracy": dict(analysis),
            "residual_risks": [],
            "no_fix_confirmation": True,
            "crew_chief_distinction": "This audit is not a Crew Chief audit.",
        }

    def test_valid_engineer_envelope_is_normalized(self):
        envelope = validate_envelope(self.envelope())
        self.assertEqual(envelope["role"], "development-engineer")
        self.assertEqual(envelope["allowed_write_paths"], [str((self.worktree / "src").resolve())])

    def test_auditor_cannot_receive_production_writes(self):
        envelope = self.envelope("independent-auditor")
        envelope["allowed_write_paths"] = ["src"]
        with self.assertRaises(FlightlineError):
            validate_envelope(envelope)

    def test_auditor_requires_controller_issued_preflight_binding(self):
        envelope = self.envelope("independent-auditor")
        for key in ("controller_authorization", "frozen_subject", "runtime_paths"):
            envelope.pop(key)
        with self.assertRaises(FlightlineError):
            validate_envelope(envelope)

    def test_controller_issues_sealed_expiring_single_use_auditor_envelope(self):
        source = validate_envelope(self.envelope())
        root = Path(self.temp.name)
        runtime = self.repo / ".venv" / "flightline-py312"
        runtime_python = runtime / "bin" / "python"
        runtime_python.parent.mkdir(parents=True)
        runtime_python.write_text("fixture\n", encoding="utf-8")
        frozen_diff = root / "frozen.diff"
        frozen_diff.write_text("fixture diff\n", encoding="utf-8")
        frozen_manifest = root / "frozen-manifest.json"
        manifest = {
            "baseline_commit": BASELINE,
            "state": "READY_FOR_AUDIT",
            "entries": [{"path": str(self.repo / "docs" / "proposal.md"), "status": "modified"}],
            "diff": {"path": str(frozen_diff), "sha256": sha256_file(frozen_diff)},
        }
        frozen_manifest.write_text(json.dumps(manifest), encoding="utf-8")
        evidence_package = root / "evidence-package.json"
        evidence_package.write_text(
            json.dumps(
                {
                    "frozen_manifest": {
                        "path": str(frozen_manifest),
                        "sha256": sha256_file(frozen_manifest),
                    }
                }
            ),
            encoding="utf-8",
        )
        audit_workspace = root / "audit-workspace"
        audit_output = root / "audit-output"
        authorization_root = root / "authorization"
        schema_preflight = root / "schema-preflight.json"
        schema_preflight.write_text("{}\n", encoding="utf-8")

        def materialize(_source, _manifest, diff_binding, workspace):
            workspace.mkdir(parents=True)
            (workspace / "proposal.md").write_text("proposal\n", encoding="utf-8")
            return {
                "canary": CANARY,
                "state": "PREFLIGHTED",
                "baseline_commit": BASELINE,
                "workspace_path": str(workspace),
                "frozen_diff_sha256": diff_binding["sha256"],
                "excluded_repository_paths": ["data", ".env"],
                "proposal_entries": [],
                **_workspace_tree(workspace),
            }

        preflight = {
            "baseline_commit": BASELINE,
            "branch": "main",
            "upstream": "origin/main",
            "cached_upstream_divergence": [0, 4],
            "status_porcelain_v2": [],
            "remote_names": ["origin"],
            "metadata": {"head": BASELINE},
            "codex_version": "fixture",
        }
        with mock.patch("tools.flightline.flightline.sys.prefix", str(runtime)), mock.patch(
            "tools.flightline.flightline.collect_preflight", return_value=preflight
        ), mock.patch("tools.flightline.flightline._materialize_audit_workspace", side_effect=materialize), mock.patch(
            "tools.flightline.flightline.AUDITOR_AUTHORIZATION_PARENT", root.resolve()
        ), mock.patch("tools.flightline.flightline.AUDITOR_WORKSPACE_PARENT", root.resolve()), mock.patch(
            "tools.flightline.flightline.verify_auditor_schema_preflight",
            return_value={"expires_at_epoch_seconds": int(time.time()) + 7200},
        ):
            report = issue_auditor_envelope(
                source,
                schema_preflight,
                frozen_manifest,
                evidence_package,
                audit_workspace,
                audit_output,
                authorization_root,
                3600,
                "ISSUE_FRESH_INDEPENDENT_AUDITOR",
            )

        envelope_path = Path(report["envelope"]["path"])
        envelope = validate_envelope(json.loads(envelope_path.read_text(encoding="utf-8")))
        self.assertEqual(envelope["role"], "independent-auditor")
        self.assertEqual(envelope["state"], "PREFLIGHTED")
        self.assertEqual(envelope["allowed_write_paths"], [])
        issuance = json.loads(Path(envelope["controller_authorization"]["issuance_record"]).read_text(encoding="utf-8"))
        self.assertEqual(issuance["schema_preflight"]["sha256"], sha256_file(schema_preflight))
        with mock.patch("tools.flightline.flightline._verify_auditor_schema_preflight_record"):
            verify_controller_authorization(envelope, envelope_path)
            with mock.patch(
                "tools.flightline.flightline.time.time",
                return_value=envelope["controller_authorization"]["expires_at_epoch_seconds"] + 1,
            ):
                with self.assertRaises(FlightlineError):
                    verify_controller_authorization(envelope, envelope_path)
            _claim_auditor_authorization(envelope)
            with self.assertRaises(FlightlineError):
                verify_controller_authorization(envelope, envelope_path)

    def test_model_accepted_schema_preflight_is_non_authorized_and_verifiable(self):
        source = validate_envelope(self.envelope())
        root = Path(self.temp.name)
        runtime = self.repo / ".venv" / "flightline-py312"
        (runtime / "bin").mkdir(parents=True)
        output_root = root / "schema-preflights" / "accepted"
        observed_commands = []

        def accepted(command, **kwargs):
            observed_commands.append(command)
            kwargs["stdout"].write(json.dumps({"type": "thread.started", "thread_id": "fixture-thread"}) + "\n")
            kwargs["stdout"].write(json.dumps({"type": "turn.completed"}) + "\n")
            kwargs["stdout"].flush()
            last_message = Path(command[command.index("-o") + 1])
            last_message.write_text(json.dumps(self.auditor_report()), encoding="utf-8")
            return mock.Mock(returncode=0)

        with mock.patch("tools.flightline.flightline.sys.prefix", str(runtime)), mock.patch(
            "tools.flightline.flightline.AUDITOR_SCHEMA_PREFLIGHT_PARENT", root / "schema-preflights"
        ), mock.patch("tools.flightline.flightline._installed_codex_version", return_value="fixture-codex"), mock.patch(
            "tools.flightline.flightline.subprocess.run", side_effect=accepted
        ):
            record = run_auditor_schema_preflight(source, output_root)
            verified = verify_auditor_schema_preflight(source, output_root / "schema-preflight.json")

        self.assertEqual(record["state"], "MODEL_ACCEPTED")
        self.assertEqual(verified["state"], "MODEL_ACCEPTED")
        self.assertFalse(record["authorization_issued"])
        self.assertFalse(record["authorization_consumed"])
        self.assertEqual(len(observed_commands), 1)
        rendered = " ".join(observed_commands[0])
        self.assertIn("--output-schema", observed_commands[0])
        self.assertIn("hooks.PreToolUse", rendered)
        self.assertIn(str(Path(os.environ["HOME"]).resolve() / ".codex"), rendered)

    def test_failed_schema_preflight_stops_without_retry_or_authorization(self):
        source = validate_envelope(self.envelope())
        root = Path(self.temp.name)
        runtime = self.repo / ".venv" / "flightline-py312"
        (runtime / "bin").mkdir(parents=True)
        output_root = root / "schema-preflights" / "rejected"
        calls = 0

        def rejected(_command, **_kwargs):
            nonlocal calls
            calls += 1
            return mock.Mock(returncode=1)

        with mock.patch("tools.flightline.flightline.sys.prefix", str(runtime)), mock.patch(
            "tools.flightline.flightline.AUDITOR_SCHEMA_PREFLIGHT_PARENT", root / "schema-preflights"
        ), mock.patch("tools.flightline.flightline._installed_codex_version", return_value="fixture-codex"), mock.patch(
            "tools.flightline.flightline.subprocess.run", side_effect=rejected
        ):
            with self.assertRaisesRegex(FlightlineError, "no authorization was issued"):
                run_auditor_schema_preflight(source, output_root)

        record = json.loads((output_root / "schema-preflight.json").read_text(encoding="utf-8"))
        self.assertEqual(calls, 1)
        self.assertEqual(record["state"], "REJECTED")
        self.assertFalse(record["authorization_issued"])

    def test_auditor_launch_environment_contains_controller_bindings(self):
        envelope = validate_envelope(self.envelope("independent-auditor"))
        environment = build_launch_environment(envelope, Path(self.temp.name) / "auditor-envelope.json")
        self.assertEqual(environment["WINGMAN_FLIGHTLINE_ROLE"], "independent-auditor")
        self.assertEqual(
            environment["WINGMAN_FLIGHTLINE_AUTHORIZATION_ID"],
            envelope["controller_authorization"]["authorization_id"],
        )
        self.assertEqual(environment["WINGMAN_FLIGHTLINE_AUDIT_OUTPUT"], str(self.output.resolve()))
        self.assertNotIn("WINGMAN_TEST_SECRET_TOKEN", environment)

    def test_codex_turn_diff_refs_are_excluded_but_other_refs_remain_protected(self):
        main = "a" * 40
        upstream = "b" * 40
        other_codex = "c" * 40
        first = _security_relevant_refs(
            "{} refs/heads/main\n"
            "{} refs/remotes/origin/main\n"
            "{} refs/codex/other-control\n"
            "{} refs/codex/turn-diffs/checkpoints/one\n".format(main, upstream, other_codex, "d" * 40)
        )
        second = _security_relevant_refs(
            "{} refs/heads/main\n"
            "{} refs/remotes/origin/main\n"
            "{} refs/codex/other-control\n"
            "{} refs/codex/turn-diffs/captures/two/base\n".format(main, upstream, other_codex, "e" * 40)
        )
        self.assertEqual(first, second)
        self.assertEqual(
            first,
            {
                "refs/codex/other-control": other_codex,
                "refs/heads/main": main,
                "refs/remotes/origin/main": upstream,
            },
        )
        changed = dict(second)
        changed["refs/remotes/origin/main"] = "f" * 40
        comparison = _preflight_comparison(
            {"metadata": {"security_relevant_refs": first}},
            {"metadata": {"security_relevant_refs": changed}},
        )
        self.assertFalse(comparison["matched"])
        self.assertIn("refs/remotes/origin/main", comparison["security_relevant_ref_changes"])

    def test_metadata_hash_is_stable_for_turn_diffs_and_changes_for_upstream(self):
        index_path = Path(self.temp.name) / "index"
        index_path.write_bytes(b"fixture index")

        def snapshot(show_ref_output):
            def fake_git(_repository, args, check=True):
                outputs = {
                    ("rev-parse", "--absolute-git-dir"): str(Path(self.temp.name) / ".git") + "\n",
                    ("rev-parse", "--git-path", "index"): str(index_path) + "\n",
                    ("show-ref",): show_ref_output,
                    ("config", "--local", "--list", "--show-origin"): "fixture config\n",
                    ("remote",): "origin\n",
                    ("rev-parse", "HEAD"): BASELINE + "\n",
                }
                return mock.Mock(stdout=outputs[tuple(args)], returncode=0, stderr="")

            with mock.patch("tools.flightline.flightline._git", side_effect=fake_git):
                return _git_metadata_snapshot(self.repo)

        base_refs = "{} refs/heads/main\n{} refs/remotes/origin/main\n".format(BASELINE, "a" * 40)
        first = snapshot(base_refs + "{} refs/codex/turn-diffs/checkpoints/one\n".format("b" * 40))
        second = snapshot(base_refs + "{} refs/codex/turn-diffs/captures/two/base\n".format("c" * 40))
        self.assertEqual(first["refs_sha256"], second["refs_sha256"])
        self.assertEqual(first["security_relevant_refs"], second["security_relevant_refs"])

        changed = snapshot(
            "{} refs/heads/main\n{} refs/remotes/origin/main\n".format(BASELINE, "d" * 40)
        )
        self.assertNotEqual(first["refs_sha256"], changed["refs_sha256"])

    def test_foreground_mismatch_records_nested_values_before_consumption(self):
        envelope = self.envelope("independent-auditor")
        control = Path(envelope["controller_authorization"]["consumption_record"]).parent
        control.mkdir(parents=True)
        expected = {
            "baseline_commit": BASELINE,
            "branch": "main",
            "upstream": "origin/main",
            "cached_upstream_divergence": [0, 4],
            "status_porcelain_v2": [],
            "remote_names": ["origin"],
            "metadata": {
                "head": BASELINE,
                "refs_sha256": "1" * 64,
                "security_relevant_refs": {"refs/heads/main": "a" * 40},
            },
            "codex_version": "fixture",
            "captured_at_epoch_seconds": 100,
        }
        current = json.loads(json.dumps(expected))
        current["metadata"]["refs_sha256"] = "2" * 64
        current["metadata"]["security_relevant_refs"]["refs/heads/main"] = "b" * 40
        current["captured_at_epoch_seconds"] = 200
        preflight_path = Path(envelope["frozen_subject"]["foreground_preflight"]["path"])
        preflight_path.write_text(json.dumps(expected), encoding="utf-8")
        envelope["frozen_subject"]["foreground_preflight"]["sha256"] = sha256_file(preflight_path)

        with mock.patch("tools.flightline.flightline.collect_preflight", return_value=current):
            with self.assertRaisesRegex(FlightlineError, "metadata.refs_sha256"):
                _verify_foreground_preflight(envelope)

        record_path = control / "controller-launch-preflight.json"
        record = json.loads(record_path.read_text(encoding="utf-8"))
        self.assertEqual(record["state"], "BLOCKED")
        self.assertEqual(record["authorization_preflight"]["metadata"]["refs_sha256"], "1" * 64)
        self.assertEqual(record["launch_preflight"]["metadata"]["refs_sha256"], "2" * 64)
        self.assertEqual(
            record["comparison"]["security_relevant_ref_changes"]["refs/heads/main"],
            {"authorization": "a" * 40, "launch": "b" * 40},
        )
        self.assertFalse(Path(envelope["controller_authorization"]["consumption_record"]).exists())

    def test_envelope_rejects_foreground_checkout_as_worktree(self):
        envelope = self.envelope()
        envelope["worktree_path"] = envelope["repository_root"]
        with self.assertRaises(FlightlineError):
            validate_envelope(envelope)

    def test_envelope_rejects_network_or_commit_authority(self):
        envelope = self.envelope()
        envelope["network_policy"] = "on"
        with self.assertRaises(FlightlineError):
            validate_envelope(envelope)

    def test_envelope_rejects_unknown_fields_schema_and_mutable_prompt(self):
        envelope = self.envelope()
        envelope["unknown"] = True
        with self.assertRaises(FlightlineError):
            validate_envelope(envelope)
        envelope = self.envelope()
        envelope["report_schema"] = str(self.output / "substitute.json")
        with self.assertRaises(FlightlineError):
            validate_envelope(envelope)
        envelope = self.envelope()
        envelope["prompt_file"] = str(self.output / "prompt.md")
        envelope["prompt_sha256"] = "0" * 64
        with self.assertRaises(FlightlineError):
            validate_envelope(envelope)

    def test_envelope_rejects_temp_root_containing_worktree(self):
        envelope = self.envelope()
        envelope["allowed_temp_paths"] = [str(self.worktree.parent)]
        envelope["output_root"] = str(self.worktree.parent / "output")
        with self.assertRaises(FlightlineError):
            validate_envelope(envelope)
        envelope = self.envelope()
        envelope["authorities"]["commit"] = True
        with self.assertRaises(FlightlineError):
            validate_envelope(envelope)

    def test_profile_is_read_only_with_specific_writes_and_denials(self):
        envelope = validate_envelope(self.envelope())
        profile_id, override = build_permission_profile(envelope)
        self.assertEqual(profile_id, "wingman-engineer")
        self.assertIn('extends=":read-only"', override)
        self.assertIn(json.dumps(str((self.worktree / "src").resolve())) + '="write"', override)
        self.assertIn(json.dumps(str(self.repo.resolve())) + '="deny"', override)
        self.assertIn(json.dumps(str((self.repo / ".git").resolve())) + '="read"', override)

    def test_launch_command_has_fail_closed_controls(self):
        envelope = validate_envelope(self.envelope())
        command = build_launch_command(envelope, Path("/tmp/envelope.json"))
        rendered = " ".join(command)
        self.assertIn("--strict-config", command)
        self.assertIn("--ephemeral", command)
        self.assertIn("--ignore-user-config", command)
        self.assertIn('approval_policy="never"', command)
        self.assertIn('web_search="disabled"', command)
        self.assertIn("hooks.PreToolUse", rendered)
        self.assertIn("hooks.PermissionRequest", rendered)
        self.assertNotIn("dangerously-bypass", rendered)
        self.assertNotIn("--search", command)

    def test_auditor_non_git_launch_uses_skip_option_and_exact_cwd(self):
        auditor = validate_envelope(self.envelope("independent-auditor"))
        command = build_launch_command(auditor, Path("/tmp/auditor-envelope.json"))
        self.assertFalse((self.worktree / ".git").exists())
        self.assertIn("--skip-git-repo-check", command)
        self.assertEqual(command[command.index("-C") + 1], str(self.worktree.resolve()))
        engineer = build_launch_command(validate_envelope(self.envelope()), Path("/tmp/engineer-envelope.json"))
        self.assertNotIn("--skip-git-repo-check", engineer)
        redacted = _redact_command(command)
        self.assertIn("<HOOK_CONFIG>", redacted)
        self.assertIn("<PERMISSION_PROFILE>", redacted)
        self.assertFalse(any(value.startswith("hooks.") for value in redacted))
        self.assertFalse(any(value.startswith("permissions.") for value in redacted))

    def test_guard_blocks_git_mutation_and_allows_approved_read(self):
        envelope = validate_envelope(self.envelope())
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "functions.exec_command",
            "tool_input": {"cmd": "git status --short", "workdir": str(self.worktree)},
        }
        self.assertEqual(guard.evaluate(payload, envelope)["hookSpecificOutput"]["permissionDecision"], "allow")
        payload["tool_input"]["cmd"] = "git commit -m blocked"
        self.assertEqual(guard.evaluate(payload, envelope)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_guard_blocks_git_global_option_bypass_and_self_authorization(self):
        envelope = validate_envelope(self.envelope())
        envelope["approved_command_prefixes"].extend([["git"], [sys.executable]])
        for command in (
            "git -C {} add src/a.py".format(self.worktree),
            "{} -m tools.flightline.flightline issue-auditor source.json".format(sys.executable),
            "{} -m tools.flightline.flightline preflight-auditor-schema source.json".format(
                sys.executable
            ),
        ):
            payload = {
                "hook_event_name": "PreToolUse",
                "tool_name": "functions.exec_command",
                "tool_input": {"cmd": command, "workdir": str(self.worktree)},
            }
            self.assertEqual(guard.evaluate(payload, envelope)["decision"], "block")

    def test_guard_blocks_external_tools_escalation_and_deletion(self):
        envelope = validate_envelope(self.envelope())
        external = {"hook_event_name": "PreToolUse", "tool_name": "web.run", "tool_input": {}}
        self.assertEqual(guard.evaluate(external, envelope)["decision"], "block")
        deletion = {
            "hook_event_name": "PreToolUse",
            "tool_name": "functions.apply_patch",
            "tool_input": {"patch": "*** Begin Patch\n*** Delete File: src/a.py\n*** End Patch"},
        }
        self.assertEqual(guard.evaluate(deletion, envelope)["decision"], "block")
        escalation = {
            "hook_event_name": "PreToolUse",
            "tool_name": "functions.exec_command",
            "tool_input": {"cmd": "rg test", "workdir": str(self.worktree), "sandbox_permissions": "require_escalated"},
        }
        self.assertEqual(guard.evaluate(escalation, envelope)["decision"], "block")

    def test_guard_blocks_absolute_destructive_command_and_shell_interpreter(self):
        envelope = validate_envelope(self.envelope())
        envelope["approved_command_prefixes"].extend([["/bin/rm"], ["/bin/sh"]])
        destructive = {
            "hook_event_name": "PreToolUse",
            "tool_name": "functions.exec_command",
            "tool_input": {"cmd": "/bin/rm file", "workdir": str(self.worktree)},
        }
        interpreter = {
            "hook_event_name": "PreToolUse",
            "tool_name": "functions.exec_command",
            "tool_input": {"cmd": "/bin/sh -c pwd", "workdir": str(self.worktree)},
        }
        self.assertEqual(guard.evaluate(destructive, envelope)["decision"], "block")
        self.assertEqual(guard.evaluate(interpreter, envelope)["decision"], "block")
        for command in ("rg $(id)", "rg `id`", "rg safe\n/bin/rm file"):
            payload = {
                "hook_event_name": "PreToolUse",
                "tool_name": "functions.exec_command",
                "tool_input": {"cmd": command, "workdir": str(self.worktree)},
            }
            self.assertEqual(guard.evaluate(payload, envelope)["decision"], "block")

    def test_guard_allows_scoped_patch(self):
        envelope = validate_envelope(self.envelope())
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "functions.apply_patch",
            "tool_input": {"patch": "*** Begin Patch\n*** Add File: src/a.py\n+x = 1\n*** End Patch"},
        }
        self.assertEqual(guard.evaluate(payload, envelope)["hookSpecificOutput"]["permissionDecision"], "allow")

    def test_permission_request_always_denies(self):
        decision = guard.evaluate({"hook_event_name": "PermissionRequest"}, self.envelope())
        self.assertEqual(decision["hookSpecificOutput"]["decision"]["behavior"], "deny")

    def test_budget_event_counting_is_conservative(self):
        commands, tokens = _event_counts({"type": "command_execution_started", "usage": {"total_tokens": 42}})
        self.assertEqual(commands, 1)
        self.assertEqual(tokens, 42)

    def test_agent_environment_drops_ambient_credentials(self):
        original = dict(os.environ)
        try:
            os.environ["WINGMAN_TEST_SECRET_TOKEN"] = "must-not-pass"
            environment = _sanitized_environment()
            self.assertNotIn("WINGMAN_TEST_SECRET_TOKEN", environment)
            self.assertEqual(environment["GIT_TERMINAL_PROMPT"], "0")
        finally:
            os.environ.clear()
            os.environ.update(original)

    def test_supervisor_timeout_preserves_artifacts(self):
        output = Path(self.temp.name) / "timeout-evidence"
        command = [sys.executable, "-c", "import sys,time; sys.stdin.read(); time.sleep(2)"]
        budgets = {"time_seconds": 1, "token_budget": 100, "command_budget": 5}
        exit_code, summary = _supervise_process(command, "fixture", _sanitized_environment(), output, "test-role", budgets)
        self.assertEqual(exit_code, 2)
        self.assertEqual(summary["stop_reason"]["code"], "time_budget_exceeded")
        self.assertTrue((output / "test-role-supervisor.json").is_file())
        self.assertTrue((output / "test-role-events.jsonl").is_file())
        self.assertTrue((output / "test-role-stderr.log").is_file())

    def test_supervisor_cancellation_preserves_artifacts(self):
        output = Path(self.temp.name) / "cancel-evidence"
        command = [sys.executable, "-c", "import sys,time; sys.stdin.read(); time.sleep(10)"]
        budgets = {"time_seconds": 30, "token_budget": 100, "command_budget": 5}
        timer = threading.Timer(0.25, lambda: os.kill(os.getpid(), signal.SIGINT))
        timer.start()
        try:
            exit_code, summary = _supervise_process(command, "fixture", _sanitized_environment(), output, "test-role", budgets)
        finally:
            timer.cancel()
            timer.join()
        self.assertEqual(exit_code, 2)
        self.assertEqual(summary["stop_reason"]["code"], "operator_cancelled")
        self.assertTrue((output / "test-role-supervisor.json").is_file())

    def test_supervisor_records_activation_handshake_cwd_and_completion(self):
        workspace = Path(self.temp.name) / "frozen-non-git-workspace"
        workspace.mkdir()
        output = Path(self.temp.name) / "activation-evidence"
        command = [
            sys.executable,
            "-c",
            (
                "import json,os,sys; "
                "sys.stdin.read(); "
                "print(json.dumps({'type':'thread.started','thread_id':'fixture-thread'}), flush=True); "
                "print(json.dumps({'type':'turn.completed','cwd':os.getcwd()}), flush=True)"
            ),
        ]
        exit_code, summary = _supervise_process(
            command,
            "fixture",
            _sanitized_environment(),
            output,
            "independent-auditor",
            {"time_seconds": 10, "token_budget": 100, "command_budget": 5},
            working_directory=workspace,
        )
        self.assertEqual(exit_code, 0)
        self.assertEqual(summary["state"], "READY_FOR_AUDIT")
        self.assertEqual(summary["lifecycle_state"], "COMPLETED")
        self.assertTrue(summary["activation"]["verified"])
        self.assertEqual(summary["activation"]["handshake"]["thread_id"], "fixture-thread")
        self.assertEqual(summary["child"]["working_directory"], str(workspace.resolve()))
        startup = json.loads((output / "independent-auditor-startup.json").read_text(encoding="utf-8"))
        self.assertEqual(
            [transition["state"] for transition in startup["transitions"]],
            [
                "CHILD_NOT_CREATED",
                "CHILD_CREATED",
                "AUDITOR_ENVIRONMENT_ACTIVATED",
                "COMPLETED",
            ],
        )
        events = (output / "independent-auditor-events.jsonl").read_text(encoding="utf-8")
        self.assertIn('"cwd": "{}"'.format(workspace.resolve()), events)

    def test_supervisor_startup_rejection_is_structured_and_visible(self):
        workspace = Path(self.temp.name) / "rejected-non-git-workspace"
        workspace.mkdir()
        output = Path(self.temp.name) / "rejected-evidence"
        command = [
            sys.executable,
            "-c",
            "import sys; sys.stdin.read(); print('fixture startup rejected', file=sys.stderr); raise SystemExit(1)",
        ]
        foreground_stderr = io.StringIO()
        with mock.patch("sys.stderr", foreground_stderr):
            exit_code, summary = _supervise_process(
                command,
                "fixture",
                _sanitized_environment(),
                output,
                "independent-auditor",
                {"time_seconds": 10, "token_budget": 100, "command_budget": 5},
                working_directory=workspace,
            )
        self.assertEqual(exit_code, 1)
        self.assertEqual(summary["lifecycle_state"], "STARTUP_REJECTED")
        self.assertFalse(summary["activation"]["verified"])
        self.assertEqual(summary["stop_reason"]["code"], "startup_rejected")
        self.assertEqual(summary["stop_reason"]["phase"], "startup")
        self.assertIn("fixture startup rejected", foreground_stderr.getvalue())
        self.assertEqual(
            (output / "independent-auditor-stderr.log").read_text(encoding="utf-8"),
            "fixture startup rejected\n",
        )
        startup = json.loads((output / "independent-auditor-startup.json").read_text(encoding="utf-8"))
        self.assertNotIn(
            "AUDITOR_ENVIRONMENT_ACTIVATED",
            [transition["state"] for transition in startup["transitions"]],
        )

    def test_supervisor_child_creation_failure_preserves_all_records(self):
        output = Path(self.temp.name) / "missing-child-evidence"
        foreground_stderr = io.StringIO()
        with mock.patch("sys.stderr", foreground_stderr):
            exit_code, summary = _supervise_process(
                ["/definitely/missing/flightline-child"],
                "fixture",
                _sanitized_environment(),
                output,
                "independent-auditor",
                {"time_seconds": 10, "token_budget": 100, "command_budget": 5},
                working_directory=self.worktree,
            )
        self.assertEqual(exit_code, 2)
        self.assertFalse(summary["child"]["created"])
        self.assertEqual(summary["lifecycle_state"], "CHILD_NOT_CREATED")
        self.assertEqual(summary["stop_reason"]["code"], "child_not_created")
        self.assertIn("child_not_created", foreground_stderr.getvalue())
        for name in ("events.jsonl", "stderr.log", "startup.json", "supervisor.json"):
            self.assertTrue((output / ("independent-auditor-" + name)).is_file())

    def test_supervisor_distinguishes_post_activation_termination(self):
        output = Path(self.temp.name) / "terminated-evidence"
        command = [
            sys.executable,
            "-c",
            (
                "import json,sys; sys.stdin.read(); "
                "print(json.dumps({'type':'thread.started','thread_id':'terminated-thread'}), flush=True); "
                "raise SystemExit(3)"
            ),
        ]
        exit_code, summary = _supervise_process(
            command,
            "fixture",
            _sanitized_environment(),
            output,
            "independent-auditor",
            {"time_seconds": 10, "token_budget": 100, "command_budget": 5},
            working_directory=self.worktree,
        )
        self.assertEqual(exit_code, 3)
        self.assertTrue(summary["activation"]["verified"])
        self.assertEqual(summary["lifecycle_state"], "TERMINATED")
        self.assertEqual(summary["stop_reason"]["code"], "child_exit_nonzero")
        self.assertEqual(summary["stop_reason"]["phase"], "execution")

    def test_json_schemas_are_valid_json(self):
        schema_root = Path(__file__).resolve().parents[1] / "tools" / "flightline" / "schemas"
        for path in schema_root.glob("*.json"):
            self.assertIsInstance(json.loads(path.read_text(encoding="utf-8")), dict)

    def test_auditor_schema_uses_only_complete_explicit_report_patterns(self):
        schema = json.loads(
            (self.schema_root / "auditor-report.schema.json").read_text(encoding="utf-8")
        )
        Draft202012Validator.check_schema(schema)
        visited = []

        def inspect(node, location):
            if not isinstance(node, dict):
                return
            visited.append(location)
            if "const" in node:
                self.assertIn("type", node, "const lacks explicit type at {}".format(location))
            if "enum" in node:
                self.assertIn("type", node, "enum lacks explicit type at {}".format(location))
            if node.get("type") == "array":
                self.assertIn("items", node, "array lacks items at {}".format(location))
            if node.get("type") == "object":
                self.assertIs(node.get("additionalProperties"), False, location)
                self.assertIsInstance(node.get("properties"), dict, location)
                self.assertEqual(set(node.get("required", [])), set(node["properties"]), location)
            for keyword in ("$defs", "properties"):
                for name, child in node.get(keyword, {}).items():
                    inspect(child, "{}/{}".format(location, name))
            if isinstance(node.get("items"), dict):
                inspect(node["items"], location + "/items")

        inspect(schema, "auditor-report")
        self.assertGreater(len(visited), 40)

    def test_auditor_schema_strictly_validates_every_corrected_structure(self):
        schema = json.loads(
            (self.schema_root / "auditor-report.schema.json").read_text(encoding="utf-8")
        )
        validator = Draft202012Validator(schema)
        report = self.auditor_report()
        self.assertEqual(list(validator.iter_errors(report)), [])

        extra = json.loads(json.dumps(report))
        extra["architecture_analysis"]["unsupported"] = True
        self.assertTrue(list(validator.iter_errors(extra)))

        incomplete = json.loads(json.dumps(report))
        incomplete["findings"][0].pop("evidence")
        self.assertTrue(list(validator.iter_errors(incomplete)))

        wrong_array_item = json.loads(json.dumps(report))
        wrong_array_item["residual_risks"] = [1]
        self.assertTrue(list(validator.iter_errors(wrong_array_item)))


if __name__ == "__main__":
    unittest.main()
