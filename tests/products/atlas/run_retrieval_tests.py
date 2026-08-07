# Runs Wingman's repeatable retrieval evaluation suite.

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIRECTORY = PROJECT_ROOT / "src"
TEST_CASES_PATH = Path(__file__).with_name(
    "retrieval_cases.json"
)

sys.path.insert(0, str(SRC_DIRECTORY))

from products.atlas.retrieval_pipeline import retrieve_question_evidence


def load_test_cases():
    """
    Load retrieval expectations from JSON.
    """
    with TEST_CASES_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def format_evidence(item):
    """
    Create a readable label for one evidence item.
    """
    source = item.get("source") or "Unknown source"
    location = item.get("location") or "Unknown location"

    return f"{source} — {location}"


def evaluate_case(test_case, evidence):
    """
    Compare retrieved evidence with one test case.
    """
    failures = []

    expect_no_evidence = test_case.get(
        "expect_no_evidence",
        False,
    )

    if expect_no_evidence:
        if evidence:
            returned_evidence = [
                format_evidence(item)
                for item in evidence
            ]

            failures.append(
                "Expected no evidence, but received: "
                + ", ".join(returned_evidence)
            )

        return failures

    expected_source = test_case.get("expected_source")

    expected_locations = set(
        test_case.get("expected_locations", [])
    )

    expected_pairs = {
        (expected_source, location)
        for location in expected_locations
    }

    actual_pairs = {
        (
            item.get("source"),
            item.get("location"),
        )
        for item in evidence
    }

    missing_pairs = expected_pairs - actual_pairs

    if missing_pairs:
        missing_labels = [
            f"{source} — {location}"
            for source, location in sorted(missing_pairs)
        ]

        failures.append(
            "Missing expected evidence: "
            + ", ".join(missing_labels)
        )

    allow_additional_locations = test_case.get(
        "allow_additional_locations",
        False,
    )

    if not allow_additional_locations:
        unexpected_pairs = actual_pairs - expected_pairs

        if unexpected_pairs:
            unexpected_labels = [
                f"{source} — {location}"
                for source, location in sorted(
                    unexpected_pairs,
                    key=lambda pair: (
                        str(pair[0]),
                        str(pair[1]),
                    ),
                )
            ]

            failures.append(
                "Unexpected evidence returned: "
                + ", ".join(unexpected_labels)
            )

    expected_top_location = test_case.get(
        "expected_top_location"
    )

    if expected_top_location:
        if not evidence:
            failures.append(
                "Expected ranked evidence, but none was returned."
            )
        else:
            top_item = evidence[0]
            top_source = top_item.get("source")
            top_location = top_item.get("location")

            if (
                top_source != expected_source
                or top_location != expected_top_location
            ):
                failures.append(
                    "Incorrect top result. Expected "
                    f"{expected_source} — "
                    f"{expected_top_location}, but received "
                    f"{top_source} — {top_location}."
                )

    return failures


def run_test_case(test_case):
    """
    Run and display one retrieval test.
    """
    question = test_case["question"]

    print()
    print("=" * 60)
    print(f"TEST: {test_case['id']}")
    print(f"QUESTION: {question}")
    print("=" * 60)

    query_plan, evidence = retrieve_question_evidence(
        question
    )

    failures = evaluate_case(
        test_case,
        evidence,
    )

    if failures:
        print("RESULT: FAIL")

        for failure in failures:
            print(f"- {failure}")

        print()
        print("Query Plan:")
        print(
            json.dumps(
                query_plan,
                indent=2,
            )
        )

        print()
        print("Retrieved Evidence:")

        if evidence:
            for item in evidence:
                print(f"- {format_evidence(item)}")
        else:
            print("- None")

        return False

    print("RESULT: PASS")

    if evidence:
        print("Retrieved Evidence:")

        for item in evidence:
            print(f"- {format_evidence(item)}")
    else:
        print("Retrieved Evidence: None")

    return True


def main():
    """
    Run the complete retrieval test suite.
    """
    test_cases = load_test_cases()

    passed_tests = 0

    for test_case in test_cases:
        try:
            passed = run_test_case(test_case)
        except Exception as error:
            passed = False

            print()
            print("=" * 60)
            print(f"TEST: {test_case['id']}")
            print("RESULT: ERROR")
            print(f"- {type(error).__name__}: {error}")

        if passed:
            passed_tests += 1

    total_tests = len(test_cases)
    failed_tests = total_tests - passed_tests

    print()
    print("=" * 60)
    print("RETRIEVAL TEST SUMMARY")
    print("=" * 60)
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Total:  {total_tests}")

    if failed_tests:
        sys.exit(1)


if __name__ == "__main__":
    main()