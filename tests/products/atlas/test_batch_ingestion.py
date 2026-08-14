"""Focused sequential batch, manifest, retry, and report coverage."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from products.atlas.batch_ingestion import (  # noqa: E402
    MANIFEST_VERSION,
    BatchValidationError,
    browser_file_input,
    execute_batch,
    folder_file_inputs,
    load_manifest,
    preview_batch,
    report_path_for,
    render_import_report,
    reset_assignment_confirmation_if_changed,
    resume_plan,
    write_manifest,
)
import products.atlas.batch_ingestion as batch_ingestion  # noqa: E402
from wingman.core.document_errors import NoExtractableTextError  # noqa: E402
from wingman.core.folder_intake import collect_folder_entries  # noqa: E402
from products.atlas.product_config import create_atlas_context  # noqa: E402


def verified_error(error):
    error.cleanup_verified = True
    error.failure_stage = "extracting"
    return error


class BatchIngestionTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.context = create_atlas_context()
        self.clock_values = iter(
            f"2026-08-07T12:00:{second:02d}+00:00" for second in range(60)
        )

    def clock(self):
        return next(self.clock_values)

    def plan(self, inputs, **kwargs):
        return preview_batch(
            inputs,
            product_context=self.context,
            input_mode="browser",
            default_course_id="AI-101",
            assignments_confirmed=True,
            batch_id="batch-focused",
            clock=self.clock,
            **kwargs,
        )

    def test_preview_is_deterministic_and_requires_explicit_assignments(self):
        plan = preview_batch(
            [
                browser_file_input("zeta.txt", b"Zeta"),
                browser_file_input("alpha.md", b"# Alpha"),
                browser_file_input("empty.csv", b""),
                browser_file_input("unsupported.rtf", b"text"),
            ],
            product_context=self.context,
            input_mode="browser",
            default_course_id=" AI-101 ",
            course_overrides={"alpha.md": "", "zeta.txt": "AI-202"},
            product_metadata={
                "program": "MSAIB",
                "academic_year": "2026-2027",
            },
            product_metadata_overrides={
                "alpha.md": {
                    "course_name": "AI Foundations",
                    "material_type": "syllabus",
                },
                "zeta.txt": {
                    "course_name": "Advanced AI",
                    "material_type": "notes",
                },
            },
            assignments_confirmed=True,
            batch_id="batch-preview",
            clock=self.clock,
        )
        records = plan.manifest["files"]
        self.assertEqual(
            [record["relative_path"] for record in records],
            ["alpha.md", "empty.csv", "unsupported.rtf", "zeta.txt"],
        )
        self.assertEqual(records[0]["course_id"], "AI-101")
        self.assertEqual(records[-1]["course_id"], "AI-202")
        self.assertEqual(records[0]["product_metadata"]["program"], "MSAIB")
        self.assertEqual(
            records[0]["product_metadata"]["course_name"],
            "AI Foundations",
        )
        self.assertEqual(
            records[0]["product_metadata"]["material_type"],
            "syllabus",
        )
        self.assertEqual(records[1]["terminal_result"], "skipped")
        self.assertEqual(records[1]["reason_code"], "empty_file")
        self.assertEqual(records[2]["reason_code"], "unsupported_format")

        unassigned = preview_batch(
            [browser_file_input("notes.txt", b"Notes")],
            product_context=self.context,
            input_mode="browser",
            assignments_confirmed=True,
            batch_id="batch-unassigned",
            clock=self.clock,
        )
        self.assertEqual(
            unassigned.manifest["files"][0]["reason_code"],
            "course_assignment_required",
        )
        with self.assertRaisesRegex(BatchValidationError, "missing"):
            execute_batch(
                unassigned,
                product_context=self.context,
                manifest_path=self.root / "unassigned.json",
                ingestor=Mock(),
                registry_loader=lambda: {},
                clock=self.clock,
            )

    def test_unconfirmed_preview_blocks_before_manifest_or_ingestor(self):
        plan = preview_batch(
            [browser_file_input("notes.txt", b"Notes")],
            product_context=self.context,
            input_mode="browser",
            default_course_id="AI-101",
            assignments_confirmed=False,
            batch_id="batch-unconfirmed",
            clock=self.clock,
        )
        manifest_path = self.root / "unconfirmed.json"
        ingestor = Mock()
        with self.assertRaisesRegex(BatchValidationError, "explicitly confirmed"):
            execute_batch(
                plan,
                product_context=self.context,
                manifest_path=manifest_path,
                ingestor=ingestor,
                registry_loader=lambda: {},
                clock=self.clock,
            )
        self.assertFalse(manifest_path.exists())
        ingestor.assert_not_called()

    def test_per_file_course_folder_metadata_reaches_intake(self):
        plan = self.plan(
            [browser_file_input("syllabus.txt", b"Course syllabus")],
            product_metadata_overrides={
                "syllabus.txt": {
                    "course_name": "AI Foundations",
                    "material_type": "syllabus",
                }
            },
        )
        ingestor = Mock(
            return_value={
                "status": "ingested",
                "source_id": "syllabus-source",
                "knowledge_object_count": 1,
            }
        )

        execute_batch(
            plan,
            product_context=self.context,
            manifest_path=self.root / "syllabus.json",
            ingestor=ingestor,
            registry_loader=lambda: {},
            clock=self.clock,
        )

        metadata = ingestor.call_args.kwargs["product_metadata"]
        self.assertEqual(metadata["course_id"], "AI-101")
        self.assertEqual(metadata["course_name"], "AI Foundations")
        self.assertEqual(metadata["material_type"], "syllabus")

    def test_changed_course_assignment_resets_browser_confirmation(self):
        state = {
            "batch_assignment_signature": ("AI-101",),
            "batch_assignments_confirmed": True,
            "batch_id": "old-batch",
            "batch_result": {"completed": True},
        }

        changed = reset_assignment_confirmation_if_changed(
            state,
            ("AI-202",),
            batch_id_factory=lambda: "new-batch",
        )

        self.assertTrue(changed)
        self.assertFalse(state["batch_assignments_confirmed"])
        self.assertEqual(state["batch_assignment_signature"], ("AI-202",))
        self.assertEqual(state["batch_id"], "new-batch")
        self.assertIsNone(state["batch_result"])

        state["batch_assignments_confirmed"] = True
        self.assertFalse(
            reset_assignment_confirmation_if_changed(
                state,
                ("AI-202",),
                batch_id_factory=lambda: "unexpected-batch",
            )
        )
        self.assertTrue(state["batch_assignments_confirmed"])
        self.assertEqual(state["batch_id"], "new-batch")

    def test_sequential_results_continue_only_after_verified_cleanup(self):
        plan = self.plan(
            [
                browser_file_input("01-success.txt", b"one"),
                browser_file_input("02-failure.txt", b"two"),
                browser_file_input("03-ocr.pdf", b"three"),
                browser_file_input("04-success.md", b"four"),
            ]
        )
        order = []
        progress = []

        def ingestor(**kwargs):
            name = kwargs["file_name"]
            order.append(name)
            kwargs["progress_callback"]("extracting")
            if name == "02-failure.txt":
                raise verified_error(RuntimeError("recoverable failure"))
            if name == "03-ocr.pdf":
                raise verified_error(
                    NoExtractableTextError("no extractable text")
                )
            kwargs["progress_callback"]("indexing")
            kwargs["progress_callback"]("registering")
            return {
                "status": "ingested",
                "source_id": f"source-{name}",
                "knowledge_object_count": 1,
            }

        result = execute_batch(
            plan,
            product_context=self.context,
            manifest_path=self.root / "batch.json",
            ingestor=ingestor,
            registry_loader=lambda: {},
            progress_callback=lambda batch_id, record: progress.append(
                (record["relative_path"], record["progress_stage"])
            ),
            clock=self.clock,
        )
        self.assertEqual(
            order,
            [
                "01-success.txt",
                "02-failure.txt",
                "03-ocr.pdf",
                "04-success.md",
            ],
        )
        self.assertEqual(
            [record["terminal_result"] for record in result["manifest"]["files"]],
            ["succeeded", "failed", "needs_ocr", "succeeded"],
        )
        self.assertTrue(result["manifest"]["files"][1]["retryable"])
        self.assertFalse(result["manifest"]["cleanup_failure_stopped_batch"])
        self.assertIn(("01-success.txt", "indexing"), progress)
        self.assertIn("requires OCR", result["report"])

    def test_unverified_cleanup_stops_without_claiming_later_files(self):
        plan = self.plan(
            [
                browser_file_input("01-ok.txt", b"one"),
                browser_file_input("02-stop.txt", b"two"),
                browser_file_input("03-never.txt", b"three"),
            ]
        )

        def ingestor(**kwargs):
            if kwargs["file_name"] == "02-stop.txt":
                raise RuntimeError("cleanup unknown")
            return {
                "status": "ingested",
                "source_id": kwargs["file_name"],
                "knowledge_object_count": 1,
            }

        result = execute_batch(
            plan,
            product_context=self.context,
            manifest_path=self.root / "stop.json",
            ingestor=ingestor,
            registry_loader=lambda: {},
            clock=self.clock,
        )
        records = result["manifest"]["files"]
        self.assertEqual(records[0]["terminal_result"], "succeeded")
        self.assertEqual(records[1]["reason_code"], "ingestion_failed")
        self.assertIsNone(records[2]["terminal_result"])
        self.assertTrue(result["manifest"]["cleanup_failure_stopped_batch"])
        self.assertEqual(result["manifest"]["stopped_file"], "02-stop.txt")

    def test_exact_duplicate_and_possible_revision_are_distinct(self):
        duplicate_bytes = b"identical"
        revision_bytes = b"new revision"
        plan = self.plan(
            [
                browser_file_input("renamed.txt", duplicate_bytes),
                browser_file_input("same-name.txt", revision_bytes),
            ]
        )
        duplicate_hash = plan.manifest["files"][0]["content_hash"]
        registry = {
            "existing-duplicate": {
                "file_name": "old-name.txt",
                "content_hash": duplicate_hash,
            },
            "existing-revision": {
                "file_name": "same-name.txt",
                "content_hash": "0" * 64,
            },
        }

        def ingestor(**kwargs):
            return {
                "status": "ingested",
                "source_id": "new-revision",
                "knowledge_object_count": 2,
            }

        result = execute_batch(
            plan,
            product_context=self.context,
            manifest_path=self.root / "duplicates.json",
            ingestor=ingestor,
            registry_loader=lambda: registry,
            clock=self.clock,
        )
        records = result["manifest"]["files"]
        self.assertEqual(records[0]["terminal_result"], "duplicate")
        self.assertEqual(records[0]["duplicate_source_id"], "existing-duplicate")
        self.assertEqual(records[1]["terminal_result"], "succeeded")
        self.assertEqual(records[1]["possible_revision_of"], ["existing-revision"])
        self.assertIn("No lineage was inferred or changed", result["report"])

    def test_resume_hash_validation_registered_recovery_and_explicit_retry(self):
        original = browser_file_input("resume.txt", b"stable")
        plan = self.plan([original])
        record = plan.manifest["files"][0]
        record["attempt_count"] = 1
        record["progress_stage"] = "indexing"
        manifest_path = self.root / "resume.json"
        write_manifest(plan.manifest, manifest_path, clock=self.clock)

        resumed = resume_plan(
            manifest_path,
            [original],
            product_context=self.context,
        )
        cleanup = Mock(return_value={"registered": False, "source_id": "resume"})
        ingestor = Mock(
            return_value={
                "status": "ingested",
                "source_id": "resume-source",
                "knowledge_object_count": 1,
            }
        )
        result = execute_batch(
            resumed,
            product_context=self.context,
            manifest_path=manifest_path,
            ingestor=ingestor,
            interrupted_cleanup=cleanup,
            registry_loader=lambda: {},
            clock=self.clock,
        )
        cleanup.assert_called_once()
        self.assertEqual(result["manifest"]["files"][0]["terminal_result"], "succeeded")

        retry_plan = self.plan([browser_file_input("retry.txt", b"retry")])
        failure = verified_error(RuntimeError("try again"))
        first_ingestor = Mock(side_effect=failure)
        retry_path = self.root / "retry.json"
        execute_batch(
            retry_plan,
            product_context=self.context,
            manifest_path=retry_path,
            ingestor=first_ingestor,
            registry_loader=lambda: {},
            clock=self.clock,
        )
        no_retry_ingestor = Mock()
        execute_batch(
            retry_plan,
            product_context=self.context,
            manifest_path=retry_path,
            ingestor=no_retry_ingestor,
            registry_loader=lambda: {},
            clock=self.clock,
        )
        no_retry_ingestor.assert_not_called()
        retry_ingestor = Mock(
            return_value={
                "status": "ingested",
                "source_id": "retried",
                "knowledge_object_count": 1,
            }
        )
        execute_batch(
            retry_plan,
            product_context=self.context,
            manifest_path=retry_path,
            retry_failed=True,
            ingestor=retry_ingestor,
            interrupted_cleanup=lambda *args: {
                "registered": False,
                "source_id": "retry",
            },
            registry_loader=lambda: {},
            clock=self.clock,
        )
        retry_ingestor.assert_called_once()

    def test_changed_reselected_content_is_rejected(self):
        plan = self.plan([browser_file_input("changed.txt", b"before")])
        plan.inputs["changed.txt"] = browser_file_input("changed.txt", b"after")
        ingestor = Mock()
        result = execute_batch(
            plan,
            product_context=self.context,
            manifest_path=self.root / "changed.json",
            ingestor=ingestor,
            registry_loader=lambda: {},
            clock=self.clock,
        )
        self.assertEqual(
            result["manifest"]["files"][0]["reason_code"],
            "content_changed",
        )
        ingestor.assert_not_called()

    def test_folder_symlink_swap_after_preview_is_not_read_or_ingested(self):
        selected_root = self.root / "selected"
        selected_root.mkdir()
        selected = selected_root / "notes.txt"
        selected.write_bytes(b"previewed content")
        plan = preview_batch(
            folder_file_inputs(collect_folder_entries(selected_root)),
            product_context=self.context,
            input_mode="folder",
            default_course_id="AI-101",
            assignments_confirmed=True,
            batch_id="batch-folder-swap",
            clock=self.clock,
        )
        outside = self.root / "outside.txt"
        outside.write_bytes(b"outside content")
        selected.unlink()
        try:
            selected.symlink_to(outside)
        except OSError as error:
            self.skipTest(f"Symlinks are unavailable: {error}")

        ingestor = Mock()
        result = execute_batch(
            plan,
            product_context=self.context,
            manifest_path=self.root / "folder-swap.json",
            ingestor=ingestor,
            registry_loader=lambda: {},
            clock=self.clock,
        )

        record = result["manifest"]["files"][0]
        self.assertEqual(record["reason_code"], "unsafe_input_changed")
        self.assertFalse(record["retryable"])
        ingestor.assert_not_called()

    def test_manifest_is_versioned_atomic_and_report_exposes_no_contents_or_paths(self):
        plan = self.plan([browser_file_input("safe.txt", b"secret document body")])
        manifest_path = self.root / "operations" / "manifest.json"
        write_manifest(plan.manifest, manifest_path, clock=self.clock)
        loaded = load_manifest(manifest_path)
        self.assertEqual(loaded["manifest_version"], MANIFEST_VERSION)
        serialized = manifest_path.read_text(encoding="utf-8")
        self.assertNotIn("secret document body", serialized)
        self.assertNotIn(str(self.root), serialized)
        self.assertEqual(list(manifest_path.parent.glob("*.tmp")), [])
        report = render_import_report(loaded)
        self.assertNotIn("secret document body", report)
        self.assertNotIn(str(self.root), report)

        loaded["manifest_version"] = 999
        manifest_path.write_text(json.dumps(loaded), encoding="utf-8")
        with self.assertRaisesRegex(BatchValidationError, "version"):
            load_manifest(manifest_path)

        loaded["manifest_version"] = MANIFEST_VERSION
        loaded["files"][0]["document_contents"] = "forbidden"
        manifest_path.write_text(json.dumps(loaded), encoding="utf-8")
        with self.assertRaisesRegex(BatchValidationError, "unknown"):
            load_manifest(manifest_path)

    def test_markdown_manifest_uses_distinct_report_and_remains_resumable(self):
        original = browser_file_input("safe.txt", b"safe")
        plan = self.plan([original])
        manifest_path = self.root / "batch-state.md"
        ingestor = Mock(
            return_value={
                "status": "ingested",
                "source_id": "safe-source",
                "knowledge_object_count": 1,
            }
        )

        result = execute_batch(
            plan,
            product_context=self.context,
            manifest_path=manifest_path,
            ingestor=ingestor,
            registry_loader=lambda: {},
            clock=self.clock,
        )

        self.assertEqual(
            Path(result["report_path"]),
            self.root / "batch-state.report.md",
        )
        self.assertEqual(
            report_path_for(manifest_path),
            self.root / "batch-state.report.md",
        )
        self.assertEqual(load_manifest(manifest_path)["batch_id"], "batch-focused")
        resumed = resume_plan(
            manifest_path,
            [original],
            product_context=self.context,
        )
        self.assertEqual(resumed.manifest["batch_id"], "batch-focused")
        self.assertTrue(Path(result["report_path"]).read_text(encoding="utf-8").startswith(
            "# Document Import Report"
        ))

        collision_plan = self.plan([browser_file_input("other.txt", b"other")])
        colliding_path = self.root / "collision.md"
        collision_ingestor = Mock()
        with self.assertRaisesRegex(BatchValidationError, "must be distinct"):
            execute_batch(
                collision_plan,
                product_context=self.context,
                manifest_path=colliding_path,
                report_path=colliding_path,
                ingestor=collision_ingestor,
                registry_loader=lambda: {},
                clock=self.clock,
            )
        self.assertFalse(colliding_path.exists())
        collision_ingestor.assert_not_called()

    def test_manifest_persistence_failure_stops_before_the_next_file(self):
        plan = self.plan(
            [
                browser_file_input("01-first.txt", b"first"),
                browser_file_input("02-second.txt", b"second"),
            ]
        )
        ingested = []

        def ingestor(**kwargs):
            ingested.append(kwargs["file_name"])
            return {
                "status": "ingested",
                "source_id": kwargs["file_name"],
                "knowledge_object_count": 1,
            }

        real_writer = batch_ingestion.write_manifest
        writes = 0

        def fail_third_write(*args, **kwargs):
            nonlocal writes
            writes += 1
            if writes == 3:
                raise batch_ingestion.ManifestPersistenceError(
                    "injected manifest failure"
                )
            return real_writer(*args, **kwargs)

        with patch.object(
            batch_ingestion,
            "write_manifest",
            side_effect=fail_third_write,
        ):
            with self.assertRaisesRegex(
                batch_ingestion.ManifestPersistenceError,
                "injected manifest failure",
            ):
                execute_batch(
                    plan,
                    product_context=self.context,
                    manifest_path=self.root / "manifest-failure.json",
                    ingestor=ingestor,
                    registry_loader=lambda: {},
                    clock=self.clock,
                )
        self.assertEqual(ingested, ["01-first.txt"])

    def test_report_persistence_failure_is_visible_after_canonical_successes(self):
        plan = self.plan([browser_file_input("source.txt", b"source")])
        real_writer = batch_ingestion.write_text_atomic

        def fail_report(path, content):
            if Path(path).suffix == ".md":
                raise batch_ingestion.ManifestPersistenceError(
                    "injected report failure"
                )
            return real_writer(path, content)

        with patch.object(
            batch_ingestion,
            "write_text_atomic",
            side_effect=fail_report,
        ):
            with self.assertRaisesRegex(
                batch_ingestion.ManifestPersistenceError,
                "injected report failure",
            ):
                execute_batch(
                    plan,
                    product_context=self.context,
                    manifest_path=self.root / "report-failure.json",
                    ingestor=lambda **kwargs: {
                        "status": "ingested",
                        "source_id": "source-id",
                        "knowledge_object_count": 1,
                    },
                    registry_loader=lambda: {},
                    clock=self.clock,
                )
        persisted = load_manifest(self.root / "report-failure.json")
        self.assertEqual(persisted["files"][0]["terminal_result"], "succeeded")


if __name__ == "__main__":
    unittest.main()
