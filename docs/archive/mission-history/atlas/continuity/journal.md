<!-- wingman-archive-metadata
{
  "schema_version": 1,
  "classification": "historical_noncanonical",
  "canonical_replacement": "docs/missions/atlas/continuity/mission.md",
  "archived_from": "docs/missions/atlas/continuity/journal.md"
}
-->

> [!WARNING]
> **HISTORICAL / NONCANONICAL MISSION EVIDENCE.** The sole canonical
> mission record is [`docs/missions/atlas/continuity/mission.md`](../../../../missions/atlas/continuity/mission.md).
> Every lifecycle, approval, commit, publication, and next-gate claim in
> the preserved body below is time-bound historical evidence and is not
> authoritative current status.

# Mission 024 — Atlas Understands Conversations

**Mission Call Sign:** Continuity

**Status:** ✅ Complete

---

## Objective

Allow Academic Wingman — Atlas to understand conversational follow-up questions without allowing chat history to replace source-grounded retrieval.

Before Mission 024, Atlas preserved visible chat history in Streamlit, but each new question was interpreted independently.

Mission 024 converted recent conversation turns into compact, source-grounded interpretation context while continuing to retrieve fresh evidence for every answer.

---

## Deliverables

* Updated `src/wingman_service.py`.
* Added optional conversation history to `ask_wingman()`.
* Added `compact_evidence_item()`.
* Added `build_conversation_context()`.
* Converted Streamlit message history into structured conversation turns.
* Paired each previous user question with the evidence returned for that turn.
* Excluded previous assistant answer text from retrieval context.
* Preserved prior:

  * Source IDs
  * Source locations
  * Headings
  * Sections
  * Concepts
  * Structured records
  * Limited text excerpts
* Limited conversation context to:

  * Three recent turns
  * Five evidence items per turn
  * Five hundred characters per evidence excerpt
* Returned the compact conversation context inside the Wingman service result for visibility and testing.
* Updated `src/retrieval_pipeline.py`.
* Added optional conversation context to `retrieve_question_evidence()`.
* Forwarded conversation context into query interpretation.
* Preserved all deterministic, structured-record, concept-memory, semantic, and ranking behavior.
* Updated `src/query_interpreter.py`.
* Added optional conversation context to `interpret_query()`.
* Preserved deterministic bare-topic handling when no conversation context exists.
* Required contextual short phrases such as `Tuesday?` to pass through natural-language interpretation.
* Added explicit prompt rules for conversational context.
* Allowed context to resolve:

  * Pronouns
  * Omitted subjects
  * Prior entity references
  * Follow-up scope
* Required the query interpreter to prefer the most recent relevant turn.
* Required it to ignore prior context when the current question is self-contained or changes topics.
* Required fresh Wingman retrieval for every conversational turn.
* Updated `src/streamlit_app.py`.
* Passed existing Streamlit session history into `ask_wingman()`.
* Preserved visible conversation history.
* Preserved the existing Chat and Library workspaces.
* Confirmed a follow-up question could use prior curriculum evidence to retrieve new schedule evidence.
* Confirmed a topic change ignored irrelevant curriculum context.
* Confirmed Atlas rejected a false conversational premise.
* Created:

  * `tests/test_conversation_context.py`
  * `tests/test_query_interpreter.py`
* Expanded:

  * `tests/test_retrieval_pipeline.py`
* Added isolated tests covering:

  * Evidence compaction
  * Concept-name normalization
  * Text-excerpt limits
  * User and assistant message pairing
  * Orphan-message handling
  * Unanswered-user-message handling
  * Recent-turn limits
  * Evidence-item limits
  * Assistant-prose exclusion
  * Context forwarding
  * No-history behavior
  * Bare-topic behavior without context
  * Contextual short follow-ups
  * Query-interpreter prompt rules
  * Fresh-evidence requirements
  * Topic changes
  * Retrieval-pipeline forwarding
* Reached:

  * 79 passing isolated unit tests
  * 7 passing live retrieval tests
  * 0 live retrieval failures
* Updated:

  * `docs/architecture/Current-Architecture.txt`
  * `docs/architecture/Mission-024-Architecture.txt`

---

## Engineering Concepts

* Conversational context
* Follow-up resolution
* Pronoun resolution
* Context windows
* Context compaction
* Evidence grounding
* Retrieval augmentation
* Stateless services
* Stateful interfaces
* Source-grounded memory
* Context limits
* Prompt boundaries
* False-premise rejection
* Topic-change detection
* Context forwarding
* Mocked integration testing
* Interface and service separation

---

## Key Lessons

* Visible chat history and conversational understanding are different capabilities.
* Conversation history should help Atlas understand what the user means.
* Conversation history should not become evidence.
* Previous assistant prose may contain summarization, interpretation, or error and should not be treated as authoritative knowledge.
* Previous retrieved evidence is safer context than previous generated language.
* Every follow-up question must still produce a fresh retrieval plan.
* Every answer must still be supported by fresh Wingman evidence.
* Recent context is usually more useful than the full conversation.
* Context limits reduce irrelevant information and uncontrolled prompt growth.
* A short phrase may be a standalone topic or a conversational follow-up depending on whether context exists.
* Self-contained questions should not inherit irrelevant filters from earlier turns.
* Conversational assumptions may be false and must be verified through retrieval.
* Atlas should correct unsupported premises rather than agree conversationally.
* A knowledge operating system should remain source-grounded even when the interface feels conversational.

---

## Interview Takeaway

Explain how Atlas supports conversational follow-up questions without trusting previous model answers.

Atlas stores visible chat messages in Streamlit session state.

Before interpreting a new question, the Wingman service converts recent messages into compact conversation turns.

Each turn contains the user’s previous question and the evidence retrieved for that question.

The assistant’s generated answer text is intentionally excluded.

The query interpreter may use this evidence to understand references such as `those courses`, `which of them`, or `the second module`.

It then creates a new retrieval plan.

Wingman executes that plan against the knowledge base and produces fresh evidence before generating the answer.

This means conversation helps determine the user’s intent, but only source evidence determines the facts.

---

## Architectural Decision

**Decision:** Pass compact prior evidence into query interpretation while excluding previous assistant prose and requiring fresh retrieval for every turn.

**Why we made it:**

The Streamlit cockpit already displayed earlier messages, but the backend did not receive them.

A follow-up such as:

`Which of those meet on Tuesday?`

could not be interpreted because `those` had no standalone meaning.

Passing the complete chat transcript into the model would have introduced unnecessary text and could have allowed previous generated answers to influence future facts.

Instead, Mission 024 introduced a controlled context structure containing:

* The prior user question
* The evidence retrieved for that question
* Limited source metadata
* Structured records
* Limited source-text excerpts

This provides enough information to resolve conversational references while preserving Wingman’s source-grounded architecture.

**Alternatives considered:**

* Pass the complete chat transcript into every prompt.
* Pass only previous assistant answers.
* Allow the LLM to answer follow-ups from memory.
* Store conversational summaries as permanent knowledge.
* Reuse previous evidence without running retrieval again.
* Build a separate conversational vector database.
* Ignore follow-up questions and require users to restate every subject.
* Allow unlimited conversation history.

**Tradeoffs:**

The query-interpreter prompt becomes larger when conversation context exists.

Only the three most recent complete turns are retained.

Only five evidence items per turn are preserved.

Text excerpts are truncated.

Complex references spanning older conversations may not resolve.

Conversation history remains limited to the active Streamlit session.

The current implementation does not create persistent conversations across browser sessions.

However, these limits reduce prompt growth, stale context, and accidental reliance on irrelevant history.

---

## Goose's Notes

Mission 024 made Atlas feel conversational without weakening its evidence rules.

The first validated conversation was:

```text
User:
What classes will I take in the fall?

Atlas:
Lists the Fall 2026 curriculum.

User:
Which of those meet on Tuesday?
```

Atlas used the previous curriculum records to identify the relevant course set.

It then created a fresh `course_schedule` retrieval plan using:

* Tuesday as the requested day
* Fall Mod A and Mod B as accepted module values
* The course names from the previous curriculum evidence

Fresh schedule evidence from Slide 11 showed that Decision Models was the Tuesday course, with two meeting options.

A second test changed topics:

```text
What kind of computer do I need for the program?
```

Atlas ignored the curriculum context and retrieved Laptop Recommendations from Slide 5.

The adversarial test asked:

```text
Those all meet on Tuesday, correct?
```

Atlas rejected the false premise.

It retrieved the schedule evidence again and explained that only Decision Models had Tuesday meeting options.

This proved the mission’s central principle:

> Conversation provides context. Sources provide truth.

---

## Mission Debrief

### What We Built

Atlas now has:

* Source-grounded conversational context
* Follow-up reference resolution
* Pronoun and omitted-subject resolution
* Recent-turn context limits
* Evidence-item limits
* Text-excerpt limits
* Previous-answer exclusion
* Fresh retrieval on every turn
* Topic-change handling
* False-premise rejection
* Contextual short-question interpretation
* Seventy-nine passing isolated tests
* Seven passing live retrieval tests

### Biggest Lesson

A conversational system does not need to trust its own prior language.

It needs to understand what the user is referring to and then verify the answer against its sources.

### Architecture Impact

Before Mission 024:

```text
Visible Chat History
        |
        v
Streamlit Display Only


New Question
        |
        v
Independent Query Interpretation
        |
        v
Retrieval
```

After Mission 024:

```text
Recent Session Messages
        |
        v
Source-Grounded Context Builder
        |
        v
Compact Conversation Context
        |
        +----------------------+
        |                      |
        v                      v
Current Question       Prior Evidence
        |                      |
        +----------+-----------+
                   |
                   v
          Query Interpretation
                   |
                   v
          Fresh Retrieval Plan
                   |
                   v
             Fresh Evidence
                   |
                   v
            Grounded Answer
```

### Validated Continuity Tests

**Relevant Follow-Up**

First question:

`What classes will I take in the fall?`

Follow-up:

`Which of those meet on Tuesday?`

Result:

Passed.

Atlas retrieved fresh schedule records from Slide 11 and identified Decision Models.

---

**Topic Change**

Previous topic:

Fall curriculum.

New question:

`What kind of computer do I need for the program?`

Result:

Passed.

Atlas ignored the course context and retrieved Laptop Recommendations from Slide 5.

---

**Misleading Conversational Premise**

Question:

`Those all meet on Tuesday, correct?`

Result:

Passed.

Atlas rejected the premise and explained that only Decision Models had Tuesday schedule records.

---

**Testing Baseline**

```text
Isolated unit tests:
79 passed

Live retrieval tests:
7 passed
0 failed
```

### Accepted Limitations

* Conversation context is stored only in the active Streamlit session.
* Conversations do not persist after the session ends.
* Only three recent completed turns are used.
* Only five evidence items are retained per turn.
* Evidence excerpts are limited to five hundred characters.
* Complex references to older turns may not resolve.
* Follow-up interpretation still depends partly on an LLM.
* Context increases query-interpreter token usage.
* Atlas does not yet summarize or compress very long conversations dynamically.
* Chat history is not tied to user accounts.
* Removing a source does not remove its old message from visible history.
* Atlas does not yet support named, saved, or searchable conversations.

These limitations preserve a controlled first implementation.

### Next Mission

**Mission 025 — 🛫 Ready for Takeoff**

**Atlas Plans Study Actions**

**Mission Call Sign:** Briefing

Mission 025 will move Atlas beyond question answering and introduce source-grounded academic actions.

Potential first actions include:

* Creating a study briefing from selected sources
* Producing a course or module overview
* Identifying upcoming academic obligations
* Generating a source-linked study checklist
* Creating a preparation brief for a class or assignment

Mission 024 gave Atlas conversational continuity.

Mission 025 will begin turning grounded knowledge into useful academic workflows.
