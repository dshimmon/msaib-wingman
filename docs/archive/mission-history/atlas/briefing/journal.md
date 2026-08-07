<!-- wingman-archive-metadata
{
  "schema_version": 1,
  "classification": "historical_noncanonical",
  "canonical_replacement": "docs/missions/atlas/briefing/mission.md",
  "archived_from": "docs/missions/atlas/briefing/journal.md"
}
-->

> [!WARNING]
> **HISTORICAL / NONCANONICAL MISSION EVIDENCE.** The sole canonical
> mission record is [`docs/missions/atlas/briefing/mission.md`](../../../../missions/atlas/briefing/mission.md).
> Every lifecycle, approval, commit, publication, and next-gate claim in
> the preserved body below is time-bound historical evidence and is not
> authoritative current status.

# Mission 025 — Atlas Plans Study Actions

**Call Sign:** Briefing
**Product:** Academic Wingman — Atlas
**Status:** Complete
**Date:** July 27, 2026

## Objective

Mission 025 extends Atlas beyond answering individual academic questions.

Before this mission, Atlas could answer questions such as:

* What courses are in Fall Module A?
* Which classes meet on Tuesday?
* What laptop does the program recommend?
* When does the fall term begin?

Each question moved through the standard Chat pipeline and produced a source-grounded answer.

The new target request was broader:

> Prepare me for Fall Module A.

This request does not ask for one fact. It requires Atlas to determine which facts matter, retrieve evidence across several source categories, organize the verified situation, recommend practical actions, and identify information that is still unknown.

Mission 025 therefore introduced a dedicated Briefing pipeline.

The objective was to enable Atlas to:

1. Interpret a broad academic preparation request.
2. Determine which evidence categories are required.
3. Retrieve the strongest evidence for each category.
4. Separate verified source facts from Atlas-generated recommendations.
5. Identify important unresolved questions without guessing.
6. Restrict generated citations to evidence actually supplied.
7. Preserve access to the complete original evidence.
8. Present the result in a dedicated Briefing workspace.

The mission principle is:

> **Sources establish the situation. Atlas proposes the action.**

---

## Deliverables

### 1. Briefing Planner

Created:

```text
src/briefing_planner.py
```

The briefing planner converts a natural-language preparation request into focused retrieval questions.

It supports two planning paths:

* Deterministic planning for recognized academic module requests
* Structured LLM planning for general briefing requests

A recognized request such as:

> Prepare me for Fall Module A.

receives a deterministic five-category plan:

1. curriculum
2. schedule
3. dates
4. preparation
5. technology

The deterministic module path does not call OpenAI.

General briefing requests continue through a structured LLM planner that returns:

* A briefing title
* A limited set of focused retrieval questions
* A category for each retrieval question

### 2. Deterministic Module Briefing Plan

Mission 025 added a pattern-based module planner for requests containing terms such as:

* Fall Module A
* Spring Module B
* Mod A
* Module B

The module planner guarantees that the same essential evidence categories are investigated every time.

It does not hardcode the answer.

The documents remain authoritative for:

* Course names
* Credit hours
* Meeting times
* Start dates
* Preparation guidance
* Technology requirements

The planner only guarantees that Atlas asks the necessary questions.

For the validated Fall Module A preparation briefing, the preparation query uses the canonical source label:

```text
Summer Work
```

### 3. Briefing Service

Created:

```text
src/briefing_service.py
```

The briefing service coordinates the complete briefing workflow.

It:

* Creates the briefing plan
* Executes each retrieval question
* Records retrieval metadata
* Keeps the strongest evidence item for each category
* Deduplicates evidence returned by multiple retrievals
* Calls the structured briefing generator
* Enriches evidence through the source registry
* Returns one complete briefing result

Evidence is deduplicated using:

* Evidence ID
* Source
* Source location

The service reuses the existing retrieval pipeline rather than creating a separate briefing search engine.

### 4. Structured Briefing Generator

Created:

```text
src/briefing_generator.py
```

The generator converts selected evidence into a structured briefing.

It creates stable evidence references:

```text
E1
E2
E3
...
```

Each reference preserves:

* Source
* Location
* Heading

The generated briefing contains:

* Title
* Overview
* Verified facts
* Recommended actions
* Open questions

Each verified fact must cite at least one supplied evidence reference.

Each recommended action must cite the evidence that motivated it.

Open questions identify important information that the available evidence does not establish.

### 5. Citation Reference Control

The structured-output schema dynamically restricts the evidence references the model may use.

For example, when the supplied evidence catalog contains:

```text
E1
E2
E3
E4
E5
```

the model may cite only those five references.

It cannot cite:

```text
E6
E7
```

or another invented source identity.

This creates deterministic citation containment around probabilistic model generation.

### 6. Briefing Output Limits

The first complete briefing was accurate but too long.

It produced:

* Too many verified facts
* Too many recommended actions
* Too many open questions
* Recommendations that extended beyond the supplied evidence

Mission 025 therefore introduced structured output limits:

```text
Verified Facts       Maximum 10
Recommended Actions  Maximum 6
Open Questions       Maximum 5
```

The generator prompt also prohibits:

* Inferring course content from course titles
* Assuming the user can select a class section
* Assuming international-student status
* Presenting recommendations as official requirements
* Including unrelated semesters or programs
* Creating an exhaustive list of speculative questions

### 7. Safe Empty-Evidence Behavior

When no evidence is available, the generator does not call OpenAI.

It returns a safe structured result containing:

* An explanation that Atlas lacks sufficient evidence
* No verified facts
* No recommended actions
* An open question asking which additional sources should be added

### 8. Briefing Workspace

Updated:

```text
src/streamlit_app.py
```

The Atlas cockpit now includes three workspaces:

* Chat
* Briefing
* Library

The Briefing workspace displays:

* Briefing title
* Overview
* Verified Facts
* Recommended Actions
* Open Questions
* Supporting Sources

The interface also includes:

```text
View complete source evidence
```

This expandable section preserves full source traceback without placing all raw evidence in the main briefing.

### 9. Mission 025 Regression Tests

Created:

```text
tests/test_briefing_planner.py
tests/test_briefing_service.py
tests/test_briefing_generator.py
```

Nine focused tests were added.

Some tests validate more than one closely related contract.

The tests cover:

* Deterministic five-category module planning
* Required category order
* No OpenAI call for deterministic module plans
* General LLM planning for non-module requests
* Exact `Summer Work` preparation query
* One strongest evidence item per category
* Cross-query evidence deduplication
* Stable evidence references
* Source, location, and heading metadata
* Citation enums restricted to supplied evidence
* Safe empty-evidence behavior
* Complete service return contract
* Source enrichment

### 10. Architecture and Mission Documentation

Updated:

```text
docs/architecture/Current-Architecture.txt
```

Created:

```text
docs/architecture/Mission-025-Architecture.txt
docs/journal/Mission-025-Atlas-Plans-Study-Actions.md
```

---

## Engineering Concepts

### Planning, Retrieval, and Generation Are Separate Responsibilities

Mission 025 separates three different problems.

#### Planning

What evidence does this request require?

Handled by:

```text
briefing_planner.py
```

#### Retrieval

Which source objects best answer each planned evidence question?

Handled by:

```text
retrieval_pipeline.py
```

#### Generation

How should the verified situation be summarized and converted into actions?

Handled by:

```text
briefing_generator.py
```

Keeping these responsibilities separate makes failures easier to diagnose.

A poor briefing may result from:

* A missing evidence category
* A weak retrieval question
* Incorrect evidence ranking
* Excessive evidence
* Poor structured generation

Without the separation, all of those failures would appear to be one vague “LLM problem.”

### Deterministic Orchestration Around Probabilistic Models

The first briefing planner used an LLM for every request.

That worked, but the evidence plan varied between runs.

Sometimes the planner retrieved:

* Curriculum
* Schedule
* Dates
* Preparation
* Technology

Other times it omitted one or more required categories or added adjacent information such as:

* Orientation
* Contacts
* Part-time curriculum
* Spring curriculum
* Administrative requirements

A recognized module preparation request has stable evidence needs.

Mission 025 therefore moved those stable needs into deterministic software.

The LLM remains useful for general briefing requests, but repeated and architecturally important request patterns receive guaranteed plans.

### Canonical Source-Oriented Retrieval

The preparation query initially included phrases such as:

```text
Fall Module A
recommended preparation
prerequisite review
```

Those terms caused retrieval to favor curriculum and schedule material.

The source deck used the heading:

```text
Summer Work
```

Using the canonical source label produced the correct preparation evidence.

This demonstrated that more natural-language context does not always improve retrieval.

When a stable source concept has a known canonical label, the shortest exact query may be the strongest query.

### Progressive Disclosure

The Briefing workspace separates two user needs:

1. A concise, actionable briefing
2. Full source verification

The main view contains:

* Facts
* Actions
* Questions
* Supporting references

The expandable evidence section contains the complete retrieved evidence.

This design keeps the interface useful without sacrificing traceability.

### Dynamic Schema Constraints

Mission 025 uses a dynamic enum inside the structured-output schema.

The enum is generated from the current evidence catalog.

This means the model’s valid citation vocabulary changes for each briefing.

The model is free to reason over the supplied evidence, but it is not free to invent source references.

### Evidence Deduplication

Different retrieval questions may return the same source object.

Without deduplication, the evidence catalog could contain repeated entries such as:

```text
E2 = Slide 12
E4 = Slide 12
```

The service creates a stable evidence identity and includes each evidence object only once.

This makes references easier to understand and reduces redundant context sent to the generator.

### Output Size as a Reliability Requirement

The first technically correct briefing was not product-ready because it was too long.

A briefing must prioritize.

Maximum item counts are therefore not merely cosmetic formatting choices.

They are part of the feature’s reliability contract.

A briefing that includes every possible fact and question can hide the decisions that matter most.

---

## Key Lessons

### 1. Stable Planning Requirements Should Become Deterministic

The LLM planner was capable of producing a good five-category plan.

It was not guaranteed to produce that same plan every time.

Once a request pattern becomes stable and repeated, Wingman OS should encode its required evidence categories deterministically.

### 2. Retrieval Problems Often Begin as Planning Problems

The retrieval confidence gate initially appeared to be the source of weak preparation and laptop results.

It was not.

The gate was correctly evaluating the search terms it received.

The planner had created poorly scoped questions.

The correct fix was to improve the retrieval plan, not weaken retrieval safeguards.

### 3. A Course Title Is Not Evidence of Course Content

The first generated briefing recommended reviewing optimization, programming, statistics, and visualization topics based partly on course names.

Those recommendations were plausible.

They were not directly established by the supplied sources.

Mission 025 reinforced the rule that plausible inference is not the same as source grounding.

### 4. Recommendations Need Provenance Too

Recommended actions are not verified source facts.

However, they should still cite the evidence that motivated them.

This allows the user to understand why Atlas proposed an action without confusing the action with an official requirement.

### 5. Missing Information Should Stay Missing

The system should not fill evidence gaps with likely answers.

Missing information belongs in:

```text
Open Questions
```

This makes uncertainty visible and actionable.

### 6. Concision Is Part of Trust

A user should be able to scan a briefing and understand:

* What is true
* What to do
* What remains unknown

If those categories are buried in excessive output, the briefing has failed even when every sentence is technically supported.

### 7. Full Traceback Does Not Need to Dominate the Interface

Complete evidence should remain accessible.

It does not need to remain expanded at all times.

The retained full-source dropdown gives Atlas both clarity and auditability.

---

## Interview Takeaway

Mission 025 provides a strong example of designing an AI system in which deterministic software and an LLM have different responsibilities.

A concise interview explanation would be:

> I built a study-briefing pipeline on top of an existing retrieval system. The key design decision was to separate evidence planning, deterministic retrieval, and structured generation. Recognized module requests use a deterministic five-category plan, while general requests can still use an LLM planner. The system then retrieves and deduplicates the strongest evidence, assigns stable references, and constrains the model so it can cite only supplied evidence. The final output separates verified facts, recommendations, and open questions, while retaining access to the full sources.

A deeper technical explanation would include:

* Why the first all-LLM planner was inconsistent
* Why the retrieval confidence gate was preserved
* How canonical source labels improved retrieval
* How dynamic enums constrained citations
* Why recommendations were separated from source facts
* Why output limits became part of the architecture
* How the Briefing workspace uses progressive disclosure

The strongest engineering story from this mission is not that Atlas can produce a study plan.

It is that the system can propose actions while preserving a clear boundary between:

* Source truth
* Model interpretation
* Model recommendation
* Unresolved uncertainty

---

## Architectural Decision

### Decision

Create a dedicated Briefing pipeline separate from the existing Chat answer path.

Use deterministic evidence plans for recognized academic module requests.

Retain a structured LLM planner for briefing requests that do not match a deterministic pattern.

### Why

A preparation briefing is not simply a longer answer.

It requires:

* Multiple evidence categories
* Evidence orchestration
* Evidence limiting
* Deduplication
* Structured action generation
* Explicit uncertainty
* Different interface presentation

Forcing that behavior into the existing Chat summarization path would mix two distinct product responsibilities.

### Deterministic Boundary

Wingman OS controls:

* Module request detection
* Required module evidence categories
* Retrieval execution
* Evidence limits
* Evidence deduplication
* Evidence-reference creation
* Allowed citation references
* Source enrichment
* Interface structure

OpenAI controls:

* General briefing planning
* Fact summarization
* Action proposal
* Prioritization
* Open-question formulation
* Natural-language communication

### Alternatives Rejected

#### Use the LLM Planner for Every Briefing

Rejected because recognized module plans varied between runs and occasionally omitted essential categories.

#### Hardcode the Final Briefing

Rejected because the facts remain source-dependent and can change when documents change.

#### Weaken the Retrieval Confidence Gate

Rejected because the gate was working correctly. The problem was query formulation.

#### Use the Existing Chat Summarizer

Rejected because a briefing has a different structure and purpose from a direct answer.

#### Return Every Retrieved Source

Rejected because broad evidence sets caused adjacent and irrelevant material to enter the briefing.

### Final Rule

> Use deterministic software to guarantee what evidence must be investigated. Use the LLM to interpret that evidence and communicate the action plan.

---

## Goose's Notes

Mav, this mission looked simple when we started.

“Prepare me for Fall Module A” sounds like one prompt and one answer.

It turned out to be one of the clearest demonstrations yet of what Wingman is supposed to become.

The first planner was intelligent but overeager.

It tried to be helpful by retrieving anything that might matter:

* Tuition
* Immunizations
* Instructors
* Textbooks
* Classrooms
* Administrative deadlines

That produced more information, but not a better briefing.

The first lesson was focus.

Then the planner produced the right categories, but it attached “Fall Module A” to every query.

That sounded reasonable. It was also enough to pull retrieval away from the program-wide Summer Work and Laptop Recommendations sections.

The second lesson was precision.

Then the evidence set was correct, but the generator created a briefing that was too long.

It included reasonable recommendations that were not fully established by the evidence.

The third lesson was restraint.

Then the Briefing workspace worked, but the planner changed its mind on another run and retrieved only curriculum and schedule evidence.

That was the moment the architecture became obvious.

The LLM should not decide every time whether dates, preparation, and technology matter for a module preparation briefing.

We already know they matter.

That belongs in Wingman OS.

Once the deterministic plan was introduced, the remaining preparation error became easy to isolate.

The source called the section:

```text
Summer Work
```

So we used:

```text
Summer Work
```

No elaborate prompt. No weakened threshold. No retrieval rewrite.

Just the correct canonical query.

The final product is not flashy because of any single model response.

It is strong because the model is surrounded by boundaries:

* It receives a deliberate evidence set.
* It can cite only supplied references.
* It must separate facts from actions.
* It must preserve unknowns.
* It cannot overwhelm the user with unlimited output.
* It must leave the original evidence reachable.

That is Wingman.

The model flies the mission.

The operating system defines the airspace.

---

## Mission Debrief

### What We Built

Mission 025 added a complete study-briefing capability to Atlas.

The new pipeline can:

1. Receive a broad preparation request.
2. Create a focused evidence plan.
3. Use deterministic planning for recognized module requests.
4. Retrieve evidence through the existing retrieval pipeline.
5. Retain one strongest evidence item per category.
6. Remove duplicate evidence.
7. Assign stable evidence references.
8. Generate verified facts.
9. Generate clearly labeled recommended actions.
10. Identify important open questions.
11. Restrict citations to supplied evidence.
12. Enrich and display supporting sources.
13. Preserve expandable access to complete evidence.

The validated Fall Module A evidence set contains:

```text
Slide 8   Fall Curriculum
Slide 11  Course Times
Slide 12  Term Structure and Dates
Slide 4   Summer Work
Slide 5   Laptop Recommendations
```

### Biggest Lesson

The biggest lesson was:

> **A system should not use probabilistic reasoning to repeatedly rediscover a stable workflow requirement.**

The model helped reveal the categories needed for a useful briefing.

Once those categories became known and validated, they became part of the deterministic operating system.

The facts remain dynamic.

The evidence requirements became stable.

### Architecture Impact

Before Mission 025, Atlas had two principal browser responsibilities:

* Chat
* Library

Chat answered source-grounded questions.

Library managed source knowledge.

After Mission 025, Atlas has a third responsibility:

* Briefing

The three workspaces now serve distinct purposes.

#### Chat

Understand a question and produce a grounded answer.

#### Briefing

Establish a multi-source situation and propose actions.

#### Library

Inspect and manage the sources from which Atlas knows things.

Mission 025 also introduces a new information model:

```text
Verified Facts
Recommended Actions
Open Questions
```

This model can extend beyond academic preparation.

The same separation could later support:

* Investment research
* Career planning
* Consulting recommendations
* Research synthesis
* Operational reviews

### Validated Briefing Tests

The following Mission 025 behavior was validated:

```text
Deterministic Module Plan          PASS
Five Required Categories Retrieved PASS
Required Category Order Preserved  PASS
Deterministic Plan Avoids OpenAI   PASS
General LLM Planner Preserved      PASS
Canonical Summer Work Query        PASS
Strongest Evidence Per Category    PASS
Duplicate Evidence Removed         PASS
Stable Evidence References         PASS
Citation References Constrained    PASS
Safe Empty-Evidence Response       PASS
Source Enrichment Preserved        PASS
Complete Service Contract          PASS
Briefing Workspace Rendered        PASS
Complete Source Evidence Retained  PASS
```

Focused briefing tests:

```text
Ran 9 tests
OK
```

Complete isolated suite:

```text
Ran 88 tests
OK
```

Live retrieval baseline:

```text
Passed: 7
Failed: 0
Total: 7
```

Compilation checks passed for:

```text
src/briefing_planner.py
src/briefing_service.py
src/briefing_generator.py
src/streamlit_app.py
```

`git diff --check` passed with no output.

### Accepted Limitations

Mission 025 intentionally accepts the following limitations:

1. Deterministic plans currently cover recognized academic module requests, not every possible briefing type.

2. General briefing planning remains probabilistic.

3. Evidence selection currently keeps one strongest item per category.

4. Generated briefings are not stored as persistent records.

5. Recommended actions do not have completion states.

6. Atlas does not yet create reminders or calendar events from actions.

7. Open questions do not automatically launch follow-up retrieval.

8. Atlas does not monitor sources for changes after a briefing is generated.

9. Course-specific software requirements remain unknown unless supported by added source material.

10. Citation control operates at the evidence-reference level rather than validating every individual sentence span.

11. Briefing quality depends on the completeness and freshness of the Atlas knowledge library.

12. The source document currently lists `macOS 26`; Atlas preserves the source wording rather than silently correcting it.

### Next Mission

Mission 025 establishes the Briefing foundation.

The next mission should build on the new action-oriented architecture without weakening its source boundary.

Candidate directions include:

* Persistent briefing history
* User-editable action tracking
* Calendar integration
* Follow-up retrieval for open questions
* Additional deterministic briefing templates
* Course-specific preparation briefings
* Exam and assignment planning
* Evidence freshness monitoring
* Briefing export

The next mission should be selected based on which capability most directly advances Atlas from planning actions to helping the user execute them.

---

Mission 025 moves Atlas from answering:

> What is true?

to also answering:

> Given what is true, what should I do next?

The answer remains grounded because:

> **Sources establish the situation. Atlas proposes the action.**
