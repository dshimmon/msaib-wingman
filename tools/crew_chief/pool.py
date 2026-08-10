"""Bounded concurrent orchestration for independent Crew Chief audits."""

from __future__ import annotations

import re
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from tools.crew_chief.controller import verify_envelope
from tools.crew_chief.core import (
    CrewChiefError,
    atomic_write,
    clock_value,
    ensure_external_path,
    isoformat,
    read_json,
    redact_text,
    sha256_file,
    utc_now,
    write_canonical_json,
)
from tools.crew_chief.runner import (
    CodexCapabilities,
    detect_codex_capabilities,
    execute_prepared_review,
    prepare_review_workspace,
)
from tools.crew_chief.validation import validate_instance


_TOKEN_COUNT = re.compile(
    r"(?im)^tokens used\s*(?::|=)?\s*([0-9][0-9,]*)\s*$"
)


@dataclass(frozen=True)
class PoolJob:
    """One fully prevalidated manifest entry."""

    job_id: str
    envelope_path: Path
    envelope: dict[str, Any]
    repository: Path
    workspace: Path
    allow_fresh_session_fallback: bool


def _binding(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise CrewChiefError(f"pool artifact must be a regular file: {path}")
    return {
        "path": str(path.resolve()),
        "size": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def _overlaps(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


def _absolute_path(value: str, label: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        raise CrewChiefError(f"{label} must be an absolute path: {value!r}")
    return path.resolve()


def _preflight(
    manifest_path: Path,
    output_root: Path,
    max_concurrency: int,
    *,
    clock: Callable[[], datetime],
) -> tuple[Path, Path, list[PoolJob]]:
    if max_concurrency < 1 or max_concurrency > 4:
        raise CrewChiefError("pool max concurrency must be between 1 and 4")
    manifest_path = manifest_path.resolve()
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise CrewChiefError(
            f"pool manifest must be a regular file: {manifest_path}"
        )
    manifest = read_json(manifest_path)
    if not isinstance(manifest, dict):
        raise CrewChiefError("pool manifest must be a JSON object")
    validate_instance("pool-manifest-v1.schema.json", manifest)

    if not output_root.is_absolute():
        raise CrewChiefError("pool output root must be an absolute path")
    output_root = output_root.resolve()
    if output_root.exists():
        raise CrewChiefError(f"pool output root already exists: {output_root}")
    if not output_root.parent.is_dir():
        raise CrewChiefError(
            f"pool output parent must already exist: {output_root.parent}"
        )

    identifiers: set[str] = set()
    jobs: list[PoolJob] = []
    workspaces: list[Path] = []
    now = clock_value(clock)
    for index, value in enumerate(manifest["jobs"]):
        job_id = value["job_id"]
        if job_id in identifiers:
            raise CrewChiefError(f"pool job ID is duplicated: {job_id}")
        identifiers.add(job_id)

        envelope_path = _absolute_path(
            value["audit_envelope"], f"pool job {job_id} envelope"
        )
        if envelope_path.is_symlink() or not envelope_path.is_file():
            raise CrewChiefError(
                f"pool job {job_id} envelope must be a regular file: "
                f"{envelope_path}"
            )
        envelope = verify_envelope(envelope_path, clock=lambda: now)
        repository = Path(envelope["repository"]["repository_root"]).resolve()
        ensure_external_path(repository, output_root, "pool output root")

        workspace_value = value.get("workspace")
        if workspace_value is None:
            workspace = output_root / job_id
        else:
            workspace = _absolute_path(
                workspace_value, f"pool job {job_id} workspace"
            )
            if not workspace.parent.is_dir():
                raise CrewChiefError(
                    f"pool job {job_id} workspace parent must already exist: "
                    f"{workspace.parent}"
                )
        workspace = workspace.resolve()
        ensure_external_path(repository, workspace, f"pool job {job_id} workspace")
        if workspace == output_root:
            raise CrewChiefError(
                f"pool job {job_id} workspace cannot be the pool output root"
            )
        if workspace.exists():
            raise CrewChiefError(
                f"pool job {job_id} workspace already exists: {workspace}"
            )
        if _overlaps(workspace, envelope_path):
            raise CrewChiefError(
                f"pool job {job_id} workspace overlaps its audit envelope"
            )
        for other in workspaces:
            if _overlaps(workspace, other):
                raise CrewChiefError(
                    f"pool job workspaces overlap: {other} and {workspace}"
                )
        workspaces.append(workspace)
        jobs.append(
            PoolJob(
                job_id=job_id,
                envelope_path=envelope_path,
                envelope=envelope,
                repository=repository,
                workspace=workspace,
                allow_fresh_session_fallback=value.get(
                    "allow_fresh_session_fallback", False
                ),
            )
        )

    for job in jobs:
        for other in jobs:
            ensure_external_path(
                other.repository,
                job.workspace,
                f"pool job {job.job_id} workspace",
            )
    return manifest_path, output_root, jobs


def _job_record(index: int, job: PoolJob) -> dict[str, Any]:
    return {
        "job_id": job.job_id,
        "input_index": index,
        "audit_id": job.envelope["audit_id"],
        "envelope_id": job.envelope["envelope_id"],
        "envelope_path": str(job.envelope_path),
        "workspace": str(job.workspace),
        "execution_mode": None,
        "status": "QUEUED",
        "attempts": 0,
        "verdict": None,
        "bindings": {
            "envelope": _binding(job.envelope_path),
            "invocation": None,
            "report": None,
            "run_record": None,
        },
        "errors": [],
        "started_at": None,
        "completed_at": None,
        "token_count": None,
    }


def _token_count(stderr_path: Path) -> int | None:
    if stderr_path.is_symlink() or not stderr_path.is_file():
        return None
    match = _TOKEN_COUNT.search(stderr_path.read_text(encoding="utf-8"))
    if match is None:
        return None
    return int(match.group(1).replace(",", ""))


def _totals(records: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "jobs": len(records),
        "queued": sum(item["status"] == "QUEUED" for item in records),
        "pass": sum(item["status"] == "PASS" for item in records),
        "pass_with_advisories": sum(
            item["status"] == "PASS_WITH_ADVISORIES" for item in records
        ),
        "fail": sum(item["status"] == "FAIL" for item in records),
        "blocked": sum(item["status"] == "BLOCKED" for item in records),
        "errors": sum(item["status"] == "ERROR" for item in records),
    }


def _write_report(
    *,
    manifest_path: Path,
    output_root: Path,
    execute: bool,
    requested_concurrency: int,
    effective_concurrency: int,
    maximum_observed_concurrency: int,
    started_at: str,
    completed_at: str,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    totals = _totals(records)
    if not execute and totals["errors"] == 0:
        status = "PREPARED"
    elif all(
        item["status"] in {"PASS", "PASS_WITH_ADVISORIES"}
        for item in records
    ):
        status = "PASS"
    else:
        status = "FAIL"
    report_path = output_root / "pool-report.json"
    report = {
        "schema_version": "1.0",
        "manifest": _binding(manifest_path),
        "output_root": str(output_root),
        "report_path": str(report_path),
        "execute_requested": execute,
        "requested_max_concurrency": requested_concurrency,
        "effective_max_concurrency": effective_concurrency,
        "maximum_observed_concurrency": maximum_observed_concurrency,
        "queue_policy": "bounded-input-order",
        "failure_policy": "continue-independent-jobs",
        "automatic_retries": 0,
        "pool_started_at": started_at,
        "pool_completed_at": completed_at,
        "overall_status": status,
        "totals": totals,
        "jobs": records,
    }
    validate_instance("pool-report-v1.schema.json", report)
    write_canonical_json(report_path, report)
    return report


def run_pool(
    manifest_path: Path,
    output_root: Path,
    *,
    max_concurrency: int = 2,
    execute: bool = False,
    codex_executable: str = "codex",
    detector: Callable[..., CodexCapabilities] = detect_codex_capabilities,
    process_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    job_executor: Callable[..., dict[str, Any]] = execute_prepared_review,
    clock: Callable[[], datetime] = utc_now,
) -> dict[str, Any]:
    """Prepare or execute a fail-independent, zero-retry audit pool."""
    started_at = isoformat(clock_value(clock))
    manifest_path, output_root, jobs = _preflight(
        manifest_path, output_root, max_concurrency, clock=clock
    )
    capabilities = detector(codex_executable)
    effective_concurrency = min(max_concurrency, len(jobs))
    output_root.mkdir(mode=0o700)
    schema_source = (
        Path(__file__).resolve().parent / "schemas" / "pool-report-v1.schema.json"
    )
    atomic_write(output_root / schema_source.name, schema_source.read_bytes())
    records = [_job_record(index, job) for index, job in enumerate(jobs)]

    preparation_failed = False
    invocations: list[dict[str, Any] | None] = [None] * len(jobs)
    for index, job in enumerate(jobs):
        try:
            invocation = prepare_review_workspace(
                job.envelope_path,
                job.workspace,
                codex_executable=codex_executable,
                detector=lambda _executable, value=capabilities: value,
                clock=clock,
            )
            invocations[index] = invocation
            records[index]["execution_mode"] = invocation["execution_mode"]
            records[index]["bindings"]["invocation"] = _binding(
                job.workspace / "invocation.json"
            )
        except CrewChiefError as error:
            preparation_failed = True
            records[index]["status"] = "ERROR"
            records[index]["errors"] = [
                {
                    "category": "PREPARATION_FAILURE",
                    "diagnostic": redact_text(str(error)),
                }
            ]

    if not execute or preparation_failed:
        return _write_report(
            manifest_path=manifest_path,
            output_root=output_root,
            execute=execute,
            requested_concurrency=max_concurrency,
            effective_concurrency=effective_concurrency,
            maximum_observed_concurrency=0,
            started_at=started_at,
            completed_at=isoformat(clock_value(clock)),
            records=records,
        )

    lock = threading.Lock()
    active = 0
    maximum_observed = 0

    def execute_one(index: int, job: PoolJob) -> None:
        nonlocal active, maximum_observed
        with lock:
            active += 1
            maximum_observed = max(maximum_observed, active)
            records[index]["started_at"] = isoformat(clock_value(clock))
            records[index]["attempts"] = 1
        try:
            invocation = invocations[index]
            if invocation is None:
                raise CrewChiefError("pool job has no prepared invocation")
            job_executor(
                job.envelope_path,
                invocation,
                allow_fresh_session_fallback=job.allow_fresh_session_fallback,
                runner=process_runner,
                clock=clock,
            )
            report_path = job.workspace / "output" / "crew-chief-report.json"
            run_record_path = job.workspace / "output" / "run-record.json"
            report = read_json(report_path)
            if not isinstance(report, dict) or report.get("verdict") not in {
                "PASS",
                "PASS_WITH_ADVISORIES",
                "FAIL",
                "BLOCKED",
            }:
                raise CrewChiefError("pool job returned an invalid verdict")
            records[index]["verdict"] = report["verdict"]
            records[index]["status"] = report["verdict"]
            records[index]["bindings"]["report"] = _binding(report_path)
            records[index]["bindings"]["run_record"] = _binding(run_record_path)
            records[index]["token_count"] = _token_count(
                job.workspace / "output" / "codex-stderr.log"
            )
        except CrewChiefError as error:
            records[index]["status"] = "ERROR"
            records[index]["errors"] = [
                {
                    "category": "CONTROL_FAILURE",
                    "diagnostic": redact_text(str(error)),
                }
            ]
        except Exception as error:  # pragma: no cover - defensive runner boundary
            records[index]["status"] = "ERROR"
            records[index]["errors"] = [
                {
                    "category": "RUNNER_FAILURE",
                    "diagnostic": redact_text(str(error)),
                }
            ]
        finally:
            with lock:
                records[index]["completed_at"] = isoformat(clock_value(clock))
                active -= 1

    with ThreadPoolExecutor(max_workers=effective_concurrency) as executor:
        futures = {
            executor.submit(execute_one, index, job): index
            for index, job in enumerate(jobs)
        }
        for future in as_completed(futures):
            future.result()

    return _write_report(
        manifest_path=manifest_path,
        output_root=output_root,
        execute=True,
        requested_concurrency=max_concurrency,
        effective_concurrency=effective_concurrency,
        maximum_observed_concurrency=maximum_observed,
        started_at=started_at,
        completed_at=isoformat(clock_value(clock)),
        records=records,
    )


def pool_exit_code(report: dict[str, Any]) -> int:
    """Return success only for a prepared pool or all accepted job verdicts."""
    return 0 if report.get("overall_status") in {"PREPARED", "PASS"} else 1
