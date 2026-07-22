```markdown
# Mission 016 — Wingman Uses Structured Knowledge

**Mission Call Sign:** Structured Retrieval

**Status:** ✅ Complete

---

## Objective

Connect Wingman’s enriched knowledge representations to runtime retrieval so natural-language questions can use document evidence, structured records, or persistent concept memory.

OpenAI interprets the user’s request and produces structured retrieval instructions. Wingman then executes those instructions deterministically and prepares the resulting context for the language model.

---

## Deliverables

- Created `openai_client.py`.
- Centralized the OpenAI client so multiple modules can share one API connection.
- Created `context_builder.py`.
- Moved context assembly out of `llm.py`.
- Updated `llm.py` to focus on OpenAI communication and final response generation.
- Updated `knowledge.py` to preserve:
  - Headings
  - Sections
  - Concepts
  - Structured records
  - Source metadata
- Corrected dormant domain metadata errors in the retrieval pipeline.
- Added structured records to the context provided to OpenAI.
- Created `query_interpreter.py`.
- Used OpenAI structured output to convert natural-language questions into retrieval plans.
- Added support for retrieval-plan fields including:
  - Text search terms
  - Record types
  - Exact record filters
  - Concept-memory search terms
- Added a deterministic bare-topic guardrail.
- Updated `knowledge.py` to accept both:
  - Simple string searches
  - Structured retrieval plans
- Separated document-text search terms from structured-record search instructions.
- Added exact structured-record filtering.
- Prevented records from being searched when they were not requested.
- Created `concept_retrieval.py`.
- Connected the persistent concept registry to runtime retrieval.
- Updated `main.py` to orchestrate:
  - Query interpretation
  - Document retrieval
  - Structured-record retrieval
  - Concept-memory retrieval
  - Context assembly
  - LLM reasoning
- Created:
  - `docs/architecture/Current-Architecture.txt`
  - `docs/architecture/Mission-016-Architecture.txt`
- Successfully validated three distinct retrieval paths.

---

## Engineering Concepts

- Query interpretation
- Structured outputs
- Retrieval planning
- Context assembly
- Structured retrieval
- Exact field filtering
- Runtime memory retrieval
- Backward-compatible interfaces
- Deterministic guardrails
- Separation of interpretation and execution
- Retrieval precision
- Regression testing
- Architecture documentation

---

## Key Lessons

- Enriched knowledge has little value until runtime retrieval can use it.
- OpenAI should interpret natural-language requests.
- Wingman should execute retrieval instructions deterministically.
- Structured output guarantees the shape of a response, not the correctness of its interpretation.
- Deterministic guardrails are useful when the application has a clear interface convention.
- A bare topic and a natural-language question are different kinds of input.
- Document evidence, structured records, and concept memory require different retrieval strategies.
- Structured records should be filtered by fields rather than searched only as flattened text.
- Exact record filters provide better precision than generating many broad search phrases.
- Context assembly is a separate responsibility from retrieval and LLM communication.
- Regression tests should cover every supported retrieval path after an architectural change.
- Domain-specific schemas are appropriate when they describe capabilities the deterministic system actually supports.
- Reusable architecture does not require eliminating every domain-specific example.
- The interpreter should know the available schemas but should not invent unsupported record types or fields.

---

## Interview Takeaway

Explain how Wingman handles a natural-language question without attempting to replace the language model.

Wingman uses OpenAI to interpret the user’s request and return a structured retrieval plan. The plan identifies which deterministic knowledge representation should be searched, such as document text, structured records, or persistent concept memory.

Wingman then executes the plan using exact retrieval rules. For example, a request for Fall Module A courses is converted into a `course_schedule` request with the filter `module = Mod A`. Wingman applies that filter to stored records and passes the resulting facts to OpenAI for explanation.

This architecture uses each component for the work it performs best: the language model interprets language and reasons over context, while deterministic software retrieves and preserves factual knowledge.

---

## Architectural Decision

**Decision:** Introduce an OpenAI-assisted query interpreter that produces structured retrieval instructions executed deterministically by Wingman.

**Why we made it:**

Wingman’s original retrieval system searched for the user’s entire input as a literal substring.

This worked for short topics such as `Orientation`, but failed for natural questions such as:

`What are the Fall Module A courses and times?`

The necessary knowledge already existed in structured records, but Wingman could not translate the natural-language request into the correct retrieval operation.

OpenAI is well suited to interpreting the user’s meaning. Wingman is well suited to executing exact searches and filters over stored knowledge.

Separating those responsibilities preserves Wingman’s deterministic architecture without attempting to reproduce the language model’s natural-language abilities.

**Alternatives considered:**

- Continue searching the user’s complete question as one string.
- Build a deterministic keyword-based intent classifier.
- Send every knowledge object to OpenAI for every question.
- Search every representation for every question.
- Build a relationship graph before connecting existing structured knowledge to retrieval.
- Let OpenAI directly answer from its own knowledge without deterministic retrieval.

**Tradeoffs:**

The query interpreter introduces an additional OpenAI call before final answer generation.

The interpreter may occasionally choose the wrong retrieval path, even when its structured output follows the required schema.

To manage this, Wingman uses deterministic guardrails for clear interface conventions and exact validation when executing retrieval instructions.

The additional step improves retrieval precision and allows Wingman to use multiple knowledge representations without replacing the LLM’s interpretation capabilities.

---

## Goose's Notes

Mission 016 began with a proposal to build relationships between concepts.

That direction was challenged because relationships were not required for current product capabilities such as generating course quizzes or retrieving information by course and section.

The mission then considered a deterministic query planner. That idea was also challenged because understanding natural-language intent is one of the language model’s core strengths.

These architecture reviews produced a clearer boundary:

OpenAI interprets.

Wingman executes.

The final runtime flow is:

User Question

↓

Query Interpretation

↓

Structured Retrieval Plan

↓

Deterministic Retrieval

↓

Context Assembly

↓

LLM Reasoning

↓

Answer and Supporting Sources

Mission 016 also demonstrated why different knowledge representations should not share one blunt retrieval method.

Document text is searched using relevant phrases.

Structured records are searched using record types and exact field filters.

Concept memory is searched using canonical concept terms and persistent occurrence data.

The result is not a homemade AI or natural-language engine.

It is a deterministic knowledge system that gives the language model the appropriate context for each request.

---

## Mission Debrief

### What We Built

Wingman can now:

- Interpret natural-language retrieval needs using OpenAI.
- Return structured retrieval plans with a predictable schema.
- Recognize simple topic commands through a deterministic guardrail.
- Search ordinary document evidence.
- Search structured records using exact filters.
- Retrieve persistent concept occurrences.
- Combine different evidence representations into unified context.
- Send structured records to the language model.
- Preserve supporting sources across every retrieval path.
- Use one shared OpenAI client across interpretation and reasoning.
- Document its current architecture in version-controlled text files.

### Biggest Lesson

Interpretation and execution are different responsibilities.

OpenAI should determine what the user is asking for.

Wingman should determine which stored facts satisfy the resulting instructions.

The language model should not replace deterministic retrieval, and deterministic software should not attempt to replace the language model’s understanding of language.

### Architecture Impact

Mission 016 introduced query interpretation, context assembly, and runtime concept-memory retrieval.

The Wingman architecture now consists of:

- `interface.py` — User interaction
- `main.py` — Runtime orchestration
- `query_interpreter.py` — Natural-language interpretation and retrieval-plan creation
- `knowledge.py` — Deterministic text and structured-record retrieval
- `concept_retrieval.py` — Persistent concept-memory retrieval
- `context_builder.py` — Organized context assembly
- `reasoning.py` — Response-generation coordination
- `llm.py` — Final LLM communication
- `openai_client.py` — Shared OpenAI client
- `document_ingestion.py` — Knowledge-object creation
- `section_resolver.py` — Section assignment
- `concept_enrichment.py` — Knowledge-enrichment orchestration
- `concept_extractor.py` — Concept extraction
- `canonicalizer.py` — Concept normalization
- `record_extractor.py` — Structured-record extraction
- `concept_registry.py` — Concept identity and occurrence management
- `concept_registry_storage.py` — Persistent registry storage

The runtime pipeline is now:

User Question

↓

Bare-Topic Guardrail or OpenAI Interpretation

↓

Structured Retrieval Plan

↓

Document Evidence, Structured Records, or Concept Memory

↓

Unified Evidence

↓

Context Builder

↓

OpenAI Reasoning

↓

Answer and Supporting Sources

### Validated Retrieval Paths

**Document Evidence**

Input:

`Orientation`

Result:

Wingman retrieves relevant slide text and provides an explanatory summary.

**Structured Records**

Input:

`What are the Fall Module A courses and times?`

Result:

OpenAI requests `course_schedule` records with the exact filter `module = Mod A`. Wingman returns the matching course schedule and no unrelated slides.

**Persistent Concept Memory**

Input:

`Where has MSAIB Curriculum appeared?`

Result:

Wingman retrieves Slides 8, 9, and 10 from persistent concept-registry occurrences.

### Next Mission

**Mission 017 — 🛫 Ready for Takeoff**

**Wingman Ranks Evidence**

Wingman will begin scoring and ordering retrieved evidence so the most relevant context reaches the language model first, improving precision as the knowledge base expands.
```
