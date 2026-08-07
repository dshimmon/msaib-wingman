# Mission 019 — Wingman Tests Its Retrieval

**Mission Call Sign:** Checkpoint

**Status:** ✅ Complete

---

## Objective

Build a repeatable evaluation system that verifies whether Wingman OS retrieves the correct evidence across its existing retrieval paths.

Before this mission, retrieval behavior was validated through individual manual questions.

Mission 019 converted those successful examples into reusable tests with explicit expected results.

---

## Deliverables

* Created `retrieval_pipeline.py`.
* Extracted retrieval coordination from `main.py`.
* Created one reusable function for retrieving ranked evidence from a natural-language question.
* Preserved the existing terminal application behavior.
* Made the retrieval pipeline reusable by:

  * The terminal interface
  * The automated test runner
  * The future Streamlit cockpit
* Created the `tests/` directory.
* Created `tests/retrieval_cases.json`.
* Defined retrieval expectations separately from the Python test logic.
* Added test cases for:

  * Document-text retrieval
  * Structured-record retrieval
  * Concept-memory retrieval
  * Semantic retrieval
  * Missing-knowledge rejection
* Created `tests/run_retrieval_tests.py`.
* Added automatic checks for:

  * Expected evidence
  * Unexpected evidence
  * Top-result ranking
  * No-evidence expectations
  * Runtime errors
* Added readable PASS and FAIL reporting.
* Added a nonzero terminal exit code when any retrieval test fails.
* Created `requirements.txt`.
* Documented the project’s current Python dependencies:

  * `openai`
  * `python-dotenv`
  * `python-pptx`
* Confirmed dependencies could be installed through one command.
* Updated:

  * `docs/architecture/Current-Architecture.txt`
  * `docs/architecture/Mission-019-Architecture.txt`
* Established the first repeatable Wingman retrieval baseline.
* Successfully passed all five retrieval tests.

---

## Engineering Concepts

* Regression testing
* Test fixtures
* Expected-versus-actual comparison
* Positive tests
* Negative tests
* Test isolation
* Reusable service functions
* Separation of interface and application logic
* Exit codes
* Dependency management
* Reproducible environments
* JSON-based test configuration
* Baseline evaluation
* Retrieval observability
* Failure diagnostics

---

## Key Lessons

* A system that works once has not yet proven that it works reliably.
* Successful manual examples should be converted into repeatable tests.
* Retrieval should be tested independently from final answer generation.
* Expected evidence must be defined explicitly.
* A useful retrieval test should verify more than whether any evidence was returned.
* Ranking matters because the strongest evidence should appear first.
* Unexpected evidence can be as important as missing evidence.
* Negative tests verify that Wingman can admit when knowledge is absent.
* Test data should remain separate from test execution logic.
* Reusable application logic should not live only inside a terminal entry point.
* The terminal, automated tests, and future user interfaces should call the same retrieval pipeline.
* A failing automated test is useful evidence, not merely an error.
* Dependency files make a project easier to reproduce on another machine.
* Small filename differences can cause real execution failures.
* A reliable baseline allows future changes to be evaluated objectively.

---

## Interview Takeaway

Explain how you evaluated the quality of Wingman’s retrieval system.

Wingman’s retrieval process was extracted from the terminal application into a reusable pipeline.

A JSON test set defines natural-language questions and their expected evidence, including the correct source, source location, top-ranked result, whether additional evidence is allowed, and whether no evidence should be returned.

A Python test runner sends each question through the real retrieval pipeline and compares the returned evidence with the expected results.

The first evaluation suite covers document-text retrieval, structured-record retrieval, concept-memory retrieval, semantic retrieval, and missing-knowledge rejection.

All five baseline tests passed.

This provides a repeatable regression suite that can detect whether future changes improve or damage retrieval behavior.

---

## Architectural Decision

**Decision:** Extract retrieval coordination into one reusable pipeline and evaluate it with externally defined JSON test cases.

**Why we made it:**

The retrieval sequence originally lived directly inside `main.py`.

That meant the terminal interface was responsible for both interacting with the user and coordinating retrieval.

Copying that logic into a test runner would have created two versions of the same system.

Instead, Mission 019 created:

`retrieve_question_evidence(question)`

This function now coordinates:

* Query interpretation
* Deterministic retrieval
* Structured-record retrieval
* Concept-memory retrieval
* Semantic fallback
* Evidence ranking

Both the terminal application and the automated evaluator call this same function.

The expected test results were stored in JSON so additional questions can be introduced without rewriting the evaluator.

**Alternatives considered:**

* Leave retrieval logic inside `main.py`.
* Duplicate the retrieval sequence inside the test runner.
* Test only the final LLM-generated answer.
* Hardcode every test case directly in Python.
* Add a large testing framework immediately.
* Check only whether evidence was returned.
* Skip negative tests.
* Judge future retrieval changes manually.

**Tradeoffs:**

Some retrieval questions still depend on OpenAI query interpretation and embeddings.

That means tests can require network access, API credentials, and API usage.

The initial test set contains only five cases and does not represent every possible user question.

The evaluator currently checks evidence identity and order rather than formal precision, recall, or answer quality.

However, the design is intentionally simple, transparent, and easy to expand.

---

## Goose's Notes

Mission 019 changed how we judge Wingman.

Before this mission, we would ask a question, inspect the result, and decide whether it looked correct.

That was useful while building the first retrieval capabilities, but it did not create a permanent checkpoint.

Now Wingman has explicit expectations.

The first test suite asks:

`Orientation`

Expected:

* Slide 7
* Slide 23
* Slide 7 ranked first

---

`What are the Fall Module A courses and times?`

Expected:

* Slide 11

---

`Where has MSAIB Curriculum appeared?`

Expected:

* Slide 8
* Slide 9
* Slide 10

---

`What kind of computer do I need for the program?`

Expected:

* Slide 5

---

`What are the dormitory pet rules?`

Expected:

* No evidence

The completed baseline was:

```text
Passed: 5
Failed: 0
Total:  5
```

That does not prove Atlas can answer every possible question.

It does prove that the retrieval behaviors established through Missions 016, 017, and 018 can now be verified repeatedly.

---

## Mission Debrief

### What We Built

Wingman OS now has:

* A reusable retrieval pipeline
* A structured retrieval test set
* An automated retrieval test runner
* Positive retrieval tests
* A negative missing-knowledge test
* Expected-source validation
* Expected-location validation
* Top-result validation
* Unexpected-evidence detection
* Runtime-error reporting
* A dependency file
* A repeatable five-test retrieval baseline

### Biggest Lesson

Testing should verify the behavior that matters to the product.

For Wingman, the most important question is not simply:

`Did the program return something?`

The important questions are:

* Did it retrieve the correct source?
* Did it retrieve the correct location?
* Did it rank the strongest source first?
* Did it avoid unsupported evidence?
* Did it correctly return nothing when the knowledge was absent?

A retrieval system must be evaluated on both what it finds and what it refuses to claim.

### Architecture Impact

Before Mission 019:

```text
Terminal Interface
        |
        v
main.py
        |
        +-- Query interpretation
        +-- Retrieval
        +-- Semantic fallback
        +-- Evidence ranking
        +-- Answer generation
        +-- Terminal output
```

After Mission 019:

```text
Terminal Interface --------+
                           |
Automated Test Runner -----+
                           |
Future Streamlit UI -------+
                           |
                           v
                retrieval_pipeline.py
                           |
                           +-- Query interpretation
                           +-- Deterministic retrieval
                           +-- Concept memory
                           +-- Semantic fallback
                           +-- Evidence ranking
                           |
                           v
                    Ranked Evidence
```

The retrieval test architecture is:

```text
retrieval_cases.json
        |
        v
run_retrieval_tests.py
        |
        v
retrieval_pipeline.py
        |
        v
Actual Evidence
        |
        v
Expected-versus-Actual Comparison
        |
        v
PASS / FAIL REPORT
```

### Validated Baseline

**Document-Text Retrieval**

Question:

`Orientation`

Result:

Passed.

Retrieved:

* Slide 7
* Slide 23

Slide 7 ranked first.

---

**Structured-Record Retrieval**

Question:

`What are the Fall Module A courses and times?`

Result:

Passed.

Retrieved:

* Slide 11

---

**Concept-Memory Retrieval**

Question:

`Where has MSAIB Curriculum appeared?`

Result:

Passed.

Retrieved:

* Slide 8
* Slide 9
* Slide 10

---

**Semantic Retrieval**

Question:

`What kind of computer do I need for the program?`

Result:

Passed.

Retrieved:

* Slide 5

---

**Missing-Knowledge Rejection**

Question:

`What are the dormitory pet rules?`

Result:

Passed.

Retrieved:

* No evidence

### Accepted Limitations

* The initial suite contains only five retrieval cases.
* Tests currently use one onboarding document.
* OpenAI-dependent tests require credentials and network access.
* The suite evaluates retrieval evidence rather than final-answer quality.
* The suite does not yet calculate formal precision, recall, or ranking metrics.
* Query interpretation may still exhibit model variability.
* The dependency versions are not yet pinned.
* The test runner is custom Python rather than a formal framework such as `pytest`.

These are appropriate limitations for the first retrieval checkpoint.

### Next Mission

**Mission 020 — 🛫 Ready for Takeoff**

**Atlas Gets a Cockpit**

Wingman OS will receive its first browser-based user interface through Streamlit.

Mission 020 will:

* Preserve the existing retrieval engine
* Create a reusable question-answer service
* Add the Atlas browser interface
* Display questions and answers conversationally
* Preserve visible session history
* Display supporting evidence through expandable source sections

Mission 019 proved the engine still works.

Mission 020 puts the pilot in the cockpit.
