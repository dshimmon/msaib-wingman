# Mission 015 — Wingman Enriches Knowledge

**Mission Call Sign:** Knowledge Memory

**Status:** ✅ Complete

---

## Objective

Teach MSAIB Wingman to enrich knowledge objects with structured concepts, records, and persistent memory while maintaining a deterministic architecture.

---

## Deliverables

- Created `concept_enrichment.py` as the orchestration layer for knowledge enrichment.
- Created `concept_extractor.py`.
- Introduced structured concept objects containing:
  - ID
  - Name
  - Canonical name
- Created `canonicalizer.py`.
- Implemented deterministic concept canonicalization.
- Created `record_extractor.py`.
- Added structured records to knowledge objects.
- Converted PowerPoint tables into structured schedule records.
- Added `concept_id` references inside structured records.
- Created `concept_registry.py`.
- Introduced persistent concept identities.
- Created `concept_registry_storage.py`.
- Added persistent storage using `concept-registry.json`.
- Implemented occurrence tracking for every concept.
- Added automatic schema migration for older registry entries using `setdefault()`.
- Preserved compatibility with the existing retrieval pipeline.
- Successfully validated end-to-end enrichment without affecting Wingman's responses.

---

## Engineering Concepts

- Knowledge enrichment
- Canonicalization
- Structured records
- Persistent memory
- Identity
- Registries
- Data migration
- Orchestration
- Separation of responsibilities
- Deterministic architecture
- Long-term knowledge storage

---

## Key Lessons

- Concepts represent ideas.
- Records represent structured facts.
- Canonicalization should connect concepts without removing specificity.
- Concepts should possess stable identities.
- Different kinds of knowledge deserve different representations.
- Different questions require different representations of knowledge.
- Knowledge should outlive the process that created it.
- Memory is deterministic; reasoning is intelligent.
- A registry should remember knowledge rather than interpret it.
- Deterministic software organizes knowledge.
- Large language models interpret organized knowledge.

---

## Interview Takeaway

Explain why Wingman separates concepts, records, and persistent memory.

Concepts, records, and memory solve different engineering problems.

Concepts allow semantic retrieval across documents.

Records preserve structured factual information that can answer precise questions without requiring an LLM to reconstruct tables or schedules.

The concept registry provides persistent identity and occurrence tracking, allowing the application to remember concepts across multiple ingestion sessions.

Separating these responsibilities creates a scalable architecture where deterministic software manages knowledge while the language model focuses on reasoning.

---

## Architectural Decision

**Decision:** Introduce a deterministic knowledge enrichment pipeline and persistent concept registry.

**Why we made it:**

Knowledge becomes significantly more valuable after it has been enriched.

Rather than asking the language model to rediscover concepts every time a question is asked, Wingman enriches knowledge during ingestion and stores the results permanently.

This reduces repeated work, improves explainability, and creates reusable knowledge for future reasoning.

**Alternatives considered:**

- Extract concepts during every user query.
- Store concepts as simple strings.
- Store records without concept references.
- Use the language model as the registry.

**Tradeoffs:**

The enrichment pipeline introduces additional processing during ingestion.

However, enrichment only occurs once while retrieval occurs many times.

Moving deterministic work upstream creates a simpler, faster, and more maintainable reasoning pipeline.

---

## Goose's Notes

Mission 015 fundamentally changed Wingman's role.

Before this mission, Wingman stored information.

After this mission, Wingman remembers information.

The project gained its first persistent knowledge memory through the concept registry.

Concepts now possess stable identities that survive across documents and ingestion sessions.

Structured records preserve factual information while concept identities connect related knowledge throughout the system.

Most importantly, this mission established the architectural boundary between Wingman and the language model.

Wingman is responsible for organizing knowledge.

The language model is responsible for interpreting knowledge.

This distinction will guide every future architectural decision.

---

## Mission Debrief

### What We Built

Wingman can now:

- Extract concepts from knowledge objects.
- Canonicalize concepts.
- Assign stable concept identities.
- Persist concepts across ingestion sessions.
- Remember where every concept has appeared.
- Extract structured schedule records from PowerPoint tables.
- Connect records to semantic concepts.
- Maintain deterministic long-term knowledge memory.

### Biggest Lesson

Knowledge organization and knowledge interpretation are separate engineering responsibilities.

Wingman should build, organize, connect, and remember knowledge.

The language model should reason over that knowledge.

This separation creates a clean architecture that leverages the strengths of both deterministic software and modern LLMs.

### Architecture Impact

Mission 015 introduced Wingman's knowledge enrichment pipeline.

The architecture now consists of:

- `interface.py` — User interaction
- `knowledge.py` — Unified evidence retrieval
- `reasoning.py` — Response generation
- `llm.py` — AI reasoning
- `document_ingestion.py` — Knowledge object creation
- `section_resolver.py` — Section assignment
- `concept_enrichment.py` — Knowledge enrichment orchestration
- `concept_extractor.py` — Concept extraction
- `canonicalizer.py` — Concept normalization
- `record_extractor.py` — Structured record extraction
- `concept_registry.py` — Concept identity management
- `concept_registry_storage.py` — Persistent registry storage

The knowledge pipeline is now:

Raw Document

↓

Knowledge Object

↓

Section Resolution

↓

Concept Extraction

↓

Canonicalization

↓

Concept Registration

↓

Record Extraction

↓

Persistent Knowledge

↓

Evidence Retrieval

↓

LLM Reasoning

↓

Answer

### Next Mission

**Mission 016 — 🛫 Ready for Takeoff**

**Wingman Builds Relationships**

Wingman will begin connecting concepts across documents, creating deterministic relationships that allow the knowledge engine to understand how ideas relate before the language model reasons about them.