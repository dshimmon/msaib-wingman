<!-- wingman-archive-metadata
{
  "schema_version": 1,
  "classification": "historical_noncanonical",
  "canonical_replacement": "docs/missions/atlas/cockpit/mission.md",
  "archived_from": "docs/missions/atlas/cockpit/journal.md"
}
-->

> [!WARNING]
> **HISTORICAL / NONCANONICAL MISSION EVIDENCE.** The sole canonical
> mission record is [`docs/missions/atlas/cockpit/mission.md`](../../../../missions/atlas/cockpit/mission.md).
> Every lifecycle, approval, commit, publication, and next-gate claim in
> the preserved body below is time-bound historical evidence and is not
> authoritative current status.

# Mission 020 — Atlas Gets a Cockpit

**Mission Call Sign:** Cockpit

**Status:** ✅ Complete

---

## Objective

Give Academic Wingman — Atlas its first browser-based user interface while preserving the existing Wingman OS retrieval and reasoning engine.

Mission 020 separated the complete question-answer process from the terminal interface, allowing both the terminal and Streamlit browser application to use the same underlying service.

---

## Deliverables

* Created `src/wingman_service.py`.
* Added the reusable `ask_wingman(question)` function.
* Centralized the complete question-answer process:

  * Retrieval
  * Evidence ranking
  * Answer generation
  * Result packaging
* Returned one organized result object containing:

  * Original question
  * Structured retrieval plan
  * Generated answer
  * Supporting evidence
* Updated `src/main.py`.
* Removed answer-generation coordination from the terminal interface.
* Connected the terminal interface to `wingman_service.py`.
* Confirmed the existing terminal experience remained functional.
* Added `streamlit` to `requirements.txt`.
* Installed and verified Streamlit version `1.51.0`.
* Created `src/streamlit_app.py`.
* Added Atlas’s first browser-based interface.
* Added:

  * Atlas page title
  * Atlas call sign
  * Chat input
  * User-message display
  * Assistant-message display
  * Processing spinner
  * Expandable supporting sources
* Added `st.session_state` conversation storage.
* Preserved visible chat history across Streamlit reruns.
* Preserved supporting evidence with each assistant message.
* Added reusable source-display logic.
* Confirmed separate source sections remained attached to the appropriate answers.
* Confirmed missing-knowledge responses did not display unsupported sources.
* Confirmed Atlas did not invent an answer when relevant knowledge was absent.
* Ran the complete retrieval regression suite after the interface changes.
* Preserved the Mission 019 retrieval baseline:

  * 5 passed
  * 0 failed
* Updated:

  * `docs/architecture/Current-Architecture.txt`
  * `docs/architecture/Mission-020-Architecture.txt`

---

## Engineering Concepts

* User interfaces
* Browser applications
* Streamlit
* Application services
* Shared business logic
* Separation of concerns
* Interface independence
* Service-layer architecture
* Session state
* Stateful user experience
* Stateless script reruns
* Chat interfaces
* Expandable interface components
* Dependency management
* Regression testing
* Result objects
* Local development servers
* Reusable display functions

---

## Key Lessons

* A user interface should present the system rather than become the system.
* Retrieval and reasoning logic should not be duplicated inside each interface.
* Multiple interfaces can safely use the same application service.
* A service layer creates a stable boundary between the user experience and the underlying engine.
* The terminal and browser should produce answers from the same code path.
* Returning one organized result object makes interfaces simpler.
* Streamlit reruns the application script after user interaction.
* Session state preserves information that would otherwise disappear during reruns.
* Visible conversation history is different from conversational reasoning memory.
* Supporting evidence should remain attached to the answer it supports.
* Missing knowledge should produce an honest no-evidence response.
* A browser interface should not weaken the system’s source-preservation rules.
* Regression tests should be run after interface changes, even when retrieval code was not intentionally modified.
* Building a functional cockpit before visual polish keeps product development focused.
* Shared capabilities should remain in Wingman OS while product-specific experiences belong in the individual Wingman interface.

---

## Interview Takeaway

Explain how you turned a terminal-based AI system into a browser application without duplicating its logic.

Wingman’s complete question-answer process was placed inside a reusable service function called:

`ask_wingman(question)`

That service coordinates retrieval, evidence ranking, and answer generation, then returns one structured result containing the answer, supporting evidence, and retrieval plan.

The terminal application and the Streamlit browser interface both call the same service.

This means the interface layer does not need to understand or reproduce the internal retrieval process.

The Streamlit application adds chat input, answer display, expandable supporting sources, and visible session history through `st.session_state`.

After the browser interface was added, the existing five-case retrieval regression suite still passed with zero failures.

---

## Architectural Decision

**Decision:** Introduce a shared Wingman service between the interfaces and the retrieval-and-reasoning engine.

**Why we made it:**

Before Mission 020, `main.py` was the only complete application entry point.

It collected a terminal question, called retrieval, generated the answer, and printed the result.

A browser interface could have duplicated this sequence, but that would have created separate implementations for the same behavior.

Instead, Mission 020 introduced:

`ask_wingman(question)`

This function creates one reusable question-answer pathway.

The terminal interface now handles terminal presentation.

The Streamlit interface handles browser presentation.

The Wingman service handles the shared application process.

This creates the structure:

```text
Terminal Interface --------+
                           |
Browser Interface ---------+
                           |
                           v
                wingman_service.py
                           |
                           +-- Retrieval
                           +-- Reasoning
                           |
                           v
               Answer + Evidence
```

**Alternatives considered:**

* Move the existing `main.py` logic directly into Streamlit.
* Duplicate retrieval and reasoning inside the browser application.
* Remove the terminal interface after creating the browser.
* Build a separate web backend immediately.
* Introduce React and JavaScript before Atlas had a functional interface.
* Build the complete multi-Wingman website during the first browser mission.
* Add uploads, authentication, source navigation, and visual polish simultaneously.
* Store only answer text in session history without preserving evidence.

**Tradeoffs:**

The Streamlit interface currently runs locally rather than as a deployed public application.

Visible session history exists only during the active browser session.

Previous messages are displayed, but they are not yet used as context for follow-up questions.

The first cockpit has limited visual styling.

Atlas does not yet support document uploads through the interface.

Supporting sources are expandable, but they do not yet have friendly document metadata or links to the original source.

However, the design proves the browser experience while preserving clean architectural boundaries.

---

## Goose's Notes

Mission 020 is the moment Atlas became visible as a product.

Before this mission, Atlas worked through Terminal:

```text
Question
    |
    v
Terminal Output
```

After this mission, the same engine can be reached from two interfaces:

```text
Terminal ------------------+
                           |
Streamlit Browser ---------+
                           |
                           v
                   Wingman Service
                           |
                           v
                  Retrieval Pipeline
                           |
                           v
                 Answer + Evidence
```

The important achievement was not simply displaying Atlas in a browser.

The important achievement was doing so without rebuilding the engine inside the cockpit.

The browser successfully handled:

* A document-text question
* A semantic question
* A missing-knowledge question
* Multiple visible conversation turns
* Separate supporting sources for each answer

For the missing-knowledge test, Atlas responded:

`I couldn't find any notes related to 'What are the dormitory pet rules?'. Try another topic or expand the knowledge base.`

No supporting-source section appeared because no evidence had been retrieved.

That preserved one of Wingman’s central responsibilities:

> Wingman should not present unsupported information as knowledge.

---

## Mission Debrief

### What We Built

Atlas now has:

* A reusable question-answer service
* A working terminal interface
* A working Streamlit browser interface
* A browser-based chat input
* User and assistant message containers
* A processing indicator
* Expandable supporting evidence
* Visible session history
* Evidence preserved with historical answers
* Honest missing-knowledge behavior
* A shared engine across both interfaces
* A verified five-test retrieval baseline

### Biggest Lesson

The cockpit and the engine should remain separate.

The cockpit determines how users interact with Wingman.

The engine determines how Wingman retrieves evidence and creates grounded answers.

Keeping those responsibilities separate means the interface can change without rewriting the system underneath it.

It also means future interfaces can reuse the same service.

Atlas, Radar, a terminal, a browser, or a future mobile experience should not each require a different retrieval engine.

### Architecture Impact

Before Mission 020:

```text
Terminal User
      |
      v
main.py
      |
      +-- Retrieval
      +-- Reasoning
      +-- Terminal display
```

After Mission 020:

```text
Terminal User                     Browser User
      |                                |
      v                                v
   main.py                    streamlit_app.py
      |                                |
      +---------------+----------------+
                      |
                      v
             wingman_service.py
                      |
                      +-- retrieval_pipeline.py
                      +-- reasoning.py
                      |
                      v
       Answer + Evidence + Retrieval Plan
```

The Streamlit session flow is:

```text
Page Loads
    |
    v
Check st.session_state
    |
    +-- No history --> Create empty message list
    |
    +-- History exists --> Render previous messages
    |
    v
Receive Chat Input
    |
    v
Save User Message
    |
    v
Call Wingman Service
    |
    v
Display Answer and Sources
    |
    v
Save Assistant Message and Evidence
    |
    v
Streamlit Reruns
    |
    v
Conversation Restored
```

### Validated Browser Tests

**Document-Text Retrieval**

Question:

`Orientation`

Result:

Passed.

Atlas displayed the expected answer and supporting evidence from:

* Slide 7
* Slide 23

---

**Semantic Retrieval**

Question:

`What kind of computer do I need for the program?`

Result:

Passed.

Atlas displayed the expected answer and supporting evidence from:

* Slide 5

---

**Visible Session History**

Test:

Ask two separate questions during the same Streamlit session.

Result:

Passed.

Both user questions, Atlas answers, and their supporting-source sections remained visible.

---

**Missing-Knowledge Handling**

Question:

`What are the dormitory pet rules?`

Result:

Passed.

Atlas explained that no related notes were available.

No supporting-source section was displayed.

---

**Retrieval Regression Suite**

Result:

```text
Passed: 5
Failed: 0
Total:  5
```

### Accepted Limitations

* Atlas currently runs on a local Streamlit development server.
* The cockpit has not yet been deployed.
* Conversation history is stored only in the active Streamlit session.
* Refreshing or closing the session may remove the visible conversation.
* Earlier messages are not yet passed into retrieval or reasoning as conversational context.
* There is no user authentication.
* There is no multi-user data separation.
* There is no Wingman product-selection page.
* Atlas does not yet accept document uploads through the browser.
* Supporting sources are not yet clickable.
* Internal filenames are still displayed instead of friendly source names.
* The interface has minimal visual branding and styling.

These are intentional limitations of the first functional cockpit.

### Next Mission

**Mission 021 — 🛫 Ready for Takeoff**

**Atlas Opens Its Sources**

**Mission Call Sign:** Traceback

Mission 021 will strengthen Wingman’s source-preservation promise.

Atlas will begin separating internal document identifiers from user-friendly source information.

The mission will introduce richer document metadata and improve how supporting evidence is presented.

The target experience is:

```text
MSAIB Onboarding 2026
Slide 7
Open Original Source
```

instead of:

```text
msaib-onboarding-2026
Slide 7
```

Mission 020 gave Atlas a cockpit.

Mission 021 will give the pilot a clear path back to the evidence.
