"""Repository-native Atlas folder-ingestion command-line entry point."""

import argparse

from batch_ingestion import (
    execute_batch,
    folder_file_inputs,
    preview_batch,
    report_counts,
    resume_plan,
)
from folder_intake import collect_folder_entries
from product_config import create_atlas_context


def parse_overrides(values, option_name):
    """Parse repeatable safe-relative-path=value options."""
    result = {}
    for value in values or ():
        relative_path, separator, assigned_value = value.partition("=")
        if not separator or not relative_path or not assigned_value.strip():
            raise ValueError(
                f"{option_name} values must use RELATIVE_PATH=VALUE."
            )
        if relative_path in result:
            raise ValueError(f"Duplicate {option_name} path: {relative_path}")
        result[relative_path] = assigned_value
    return result


def build_argument_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Preview or execute one bounded, sequential Atlas folder import. "
            "The default is a non-mutating preview."
        )
    )
    parser.add_argument("root", help="One explicitly selected local folder root.")
    parser.add_argument("--course-id", help="Confirmed batch course assignment.")
    parser.add_argument(
        "--course-override",
        action="append",
        default=[],
        metavar="RELATIVE_PATH=COURSE_ID",
    )
    parser.add_argument(
        "--display-name-override",
        action="append",
        default=[],
        metavar="RELATIVE_PATH=NAME",
    )
    parser.add_argument("--program")
    parser.add_argument("--academic-year")
    parser.add_argument("--domain")
    parser.add_argument("--recursive", action="store_true")
    parser.add_argument("--include-hidden", action="store_true")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Confirm the preview assignments and perform persistent ingestion.",
    )
    parser.add_argument("--manifest", help="Operational manifest output path.")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume the supplied --manifest after reselecting the same root.",
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Explicitly retry hash-matched failed files while resuming.",
    )
    return parser


def render_preview(plan):
    lines = [
        f"Batch preview: {plan.manifest['batch_id']}",
        f"Files considered: {len(plan.manifest['files'])}",
    ]
    for record in plan.manifest["files"]:
        state = record.get("reason_code") or "ready"
        assignment = record.get("course_id") or "REQUIRED"
        lines.append(
            f"- {record['relative_path']} | {state} | course_id={assignment}"
        )
    return "\n".join(lines)


def main(arguments=None):
    parser = build_argument_parser()
    options = parser.parse_args(arguments)
    if options.resume and not options.manifest:
        parser.error("--resume requires --manifest.")
    if options.retry_failed and not options.resume:
        parser.error("--retry-failed requires --resume.")

    try:
        entries = collect_folder_entries(
            options.root,
            recursive=options.recursive,
            include_hidden=options.include_hidden,
        )
        inputs = folder_file_inputs(entries)
        context = create_atlas_context()
        if options.resume:
            plan = resume_plan(
                options.manifest,
                inputs,
                product_context=context,
            )
        else:
            plan = preview_batch(
                inputs,
                product_context=context,
                input_mode="folder",
                default_course_id=options.course_id,
                course_overrides=parse_overrides(
                    options.course_override, "--course-override"
                ),
                display_name_overrides=parse_overrides(
                    options.display_name_override,
                    "--display-name-override",
                ),
                product_metadata={
                    "program": options.program,
                    "academic_year": options.academic_year,
                },
                domain=options.domain,
                assignments_confirmed=options.execute,
            )
        print(render_preview(plan))
        if not options.execute:
            print("Preview only. Re-run with --execute to ingest this batch.")
            return 0

        result = execute_batch(
            plan,
            product_context=context,
            manifest_path=options.manifest,
            retry_failed=options.retry_failed,
        )
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        parser.error(str(error))

    counts = report_counts(result["manifest"])
    print(
        "Completed: "
        + ", ".join(
            f"{name}={counts[name]}"
            for name in ("succeeded", "skipped", "duplicate", "needs_ocr", "failed")
        )
    )
    print(f"Manifest: {result['manifest_path']}")
    print(f"Report: {result['report_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
