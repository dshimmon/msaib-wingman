```markdown
# Mission 013 — Wingman Unifies Knowledge

**Mission Call Sign:** Unified Knowledge

**Status:** ✅ Complete

---

## Objective

Teach MSAIB Wingman to retrieve handwritten notes and ingested documents through one unified knowledge system.

---

## Deliverables

- Renamed `search_knowledge()` to `retrieve_evidence()`.
- Replaced the term `results` with `evidence` throughout the retrieval pipeline.
- Updated `knowledge.py` to search:
  - Handwritten text notes
  - Ingested document JSON files
- Standardized retrieved evidence to include:
  - Domain
  - Source
  - Location
  - Text
- Updated `reasoning.py` to work with evidence.
- Updated `llm.py` to organize evidence by domain.
- Updated `main.py` to use evidence-based terminology.
- Preserved supporting sources beneath Wingman’s generated summary.
- Successfully answered a question using evidence from the MSAIB onboarding presentation.

---

## Engineering Concepts

- Unified retrieval
- Evidence-based architecture
- Data normalization
- Metadata
- Retrieval-Augmented Generation
- Domain grouping
- Separation of retrieval and reasoning
- Architectural refactoring

---

## Key Lessons

- Knowledge can originate from different sources while sharing one internal representation.
- The reasoning system should not need to know whether evidence came from a note, slide, PDF, or another source.
- Retrieval finds evidence; reasoning interprets evidence.
- Consistent metadata makes future features easier to build.
- Clear terminology improves both code readability and architectural thinking.

---

## Interview Takeaway

Explain why the application uses a unified evidence model.

A unified evidence model allows Wingman to retrieve information from different knowledge sources while presenting each result in the same structure.

This means the reasoning and language model layers do not require separate logic for text notes, PowerPoint presentations, PDFs, or future knowledge sources.

The architecture can therefore expand without requiring the entire application to be rewritten.

---

## Architectural Decision

**Decision:** Represent all retrieved knowledge as evidence with a standardized structure.

**Why we made it:**

Notes and ingested documents originally used different formats.

Allowing those formats to move directly through the application would require the reasoning layer to understand every possible knowledge source.

Instead, `knowledge.py` transforms retrieved information into a shared evidence structure before passing it to the rest of the application.

**Alternatives considered:**

- Maintain separate retrieval pipelines for notes and documents.
- Allow the language model to interpret different source formats.
- Convert every knowledge source into the same file type before retrieval.

**Tradeoffs:**

Creating a unified evidence model required refactoring several modules and changing existing terminology.

However, the rest of the application can now operate independently of the original knowledge source.

This makes the architecture easier to maintain and prepares Wingman for additional document types and retrieval methods.

---

## Goose's Notes

Mission 013 represents Wingman’s transition from separate knowledge sources to one unified retrieval architecture.

Before this mission, handwritten notes and ingested documents existed as independent forms of knowledge.

Wingman can now retrieve both through the same pipeline.

Question

↓

Retrieve Evidence

↓

Organize Evidence by Domain

↓

Generate Summary

↓

Display Supporting Sources

Although the current retrieval method still relies on keyword matching, the architecture now reflects the central pattern used in Retrieval-Augmented Generation systems.

The retrieval technology can change later without requiring the reasoning architecture to be rebuilt.

---

## Mission Debrief

### What We Built

Wingman can now:

- Search handwritten notes.
- Search ingested document knowledge.
- Convert retrieved information into standardized evidence.
- Organize evidence by domain.
- Generate a concise AI summary.
- Display the supporting sources used to create the answer.

### Biggest Lesson

Knowledge sources may be different.

Evidence should be consistent.

By transforming every retrieved item into the same evidence structure, Wingman can reason across an expanding knowledge base without becoming dependent on individual file types.

### Architecture Impact

Mission 013 unified Wingman’s knowledge retrieval system.

The Wingman architecture now consists of:

- `interface.py` — User interaction
- `knowledge.py` — Unified evidence retrieval
- `reasoning.py` — Response generation
- `llm.py` — AI communication and evidence summarization
- `document_ingestion.py` — Knowledge creation

The complete knowledge pipeline is now:

Document

↓

Ingestion

↓

Structured Knowledge

↓

Evidence Retrieval

↓

Reasoning

↓

Summary and Supporting Sources

### Next Mission

**Mission 014 — 🛫 Ready for Takeoff**

**Wingman Chunks Knowledge**

Wingman will improve how documents are divided into searchable evidence, creating knowledge chunks designed for future embeddings, semantic search, and production-quality Retrieval-Augmented Generation.
```
