```markdown
# Mission 014 — Wingman Chunks Knowledge

**Mission Call Sign:** Knowledge Representation

**Status:** ✅ Complete

---

## Objective

Teach MSAIB Wingman to transform document content into structured knowledge objects that preserve identity, location, hierarchy, and source context.

---

## Deliverables

- Established a canonical evidence schema shared by all knowledge sources.
- Added a unique identifier to every ingested document chunk.
- Replaced PowerPoint-specific slide metadata with a generic `location` field.
- Added structural metadata, including:
  - Heading
  - Section
  - Concepts
- Distinguished between:
  - A heading that labels an individual chunk
  - A section that groups related chunks
  - Concepts that describe what the knowledge is about
- Created deterministic PowerPoint heading detection using:
  - Font size
  - Text length
  - Vertical position
- Created the `section_resolver.py` module.
- Separated section-assignment policy from document ingestion.
- Added persistent section state through `current_section`.
- Updated `knowledge.py` so notes and documents produce the same evidence schema.
- Preserved new metadata throughout the retrieval pipeline.
- Added PowerPoint table extraction.
- Successfully converted a course schedule table into readable structured text.
- Regenerated the onboarding knowledge file using the expanded schema.
- Verified that Wingman continued to retrieve evidence and generate accurate answers.

---

## Engineering Concepts

- Knowledge representation
- Canonical data models
- Data contracts
- Schema migration
- State
- Scope
- Deterministic heuristics
- Heading detection
- Section resolution
- Table extraction
- Metadata preservation
- Separation of policy and process
- Lossless data pipelines
- Defensive system design

---

## Key Lessons

- A chunk should be a self-contained unit of knowledge rather than an arbitrary portion of a file.
- Documents are containers; chunks are knowledge.
- A heading labels an individual knowledge object.
- A section groups related knowledge objects.
- Concepts describe what the knowledge is about and may appear across multiple documents.
- Every knowledge source should produce the same evidence schema.
- A schema change is incomplete until every downstream consumer understands it.
- Metadata should not be discarded after ingestion.
- Deterministic methods should be attempted before introducing AI.
- Existing libraries should be inspected before custom logic is invented.
- PowerPoint information may exist inside text boxes, tables, charts, notes, and other shapes.
- Knowledge should become richer as it moves through the system.

---

## Interview Takeaway

Explain how Wingman represents knowledge after ingesting a document.

Wingman converts source documents into structured knowledge objects rather than passing raw files directly to the language model.

Each object contains a unique identity, source, domain, heading, section, concepts, location, and extracted text. This common representation allows retrieval and reasoning components to operate independently of the original file type.

The ingestion pipeline also uses deterministic rules to detect headings and document structure before relying on AI-based enrichment. This makes the system more explainable, testable, and maintainable.

---

## Architectural Decision

**Decision:** Introduce a canonical knowledge object and separate section resolution into its own module.

**Why we made it:**

Wingman originally treated each PowerPoint slide as an isolated block of text.

That structure preserved the content but did not describe how the knowledge was organized or how related pieces belonged together.

A canonical knowledge object gives every piece of evidence the same structure regardless of whether it originated from a text note, PowerPoint, PDF, or future source.

The `section_resolver.py` module separates the policy for assigning sections from the process of extracting document content.

**Alternatives considered:**

- Continue treating each slide as an independent chunk.
- Use the slide heading directly as the section without a dedicated resolver.
- Use an LLM to identify headings and sections during every ingestion.
- Store different evidence structures for each document type.
- Ignore tables and retrieve only ordinary text boxes.

**Tradeoffs:**

The richer schema introduces additional fields and requires ingestion and retrieval components to remain synchronized.

Deterministic heading detection is not guaranteed to work perfectly across every presentation design.

However, this approach creates an explainable baseline that can later be enhanced with better heuristics or AI without redesigning the rest of the system.

---

## Goose's Notes

Mission 014 began as an effort to improve document chunking.

It became a mission about knowledge representation.

Wingman no longer treats a chunk as merely a piece of extracted text.

Each chunk is now a knowledge object with:

- Identity
- Domain
- Source
- Heading
- Section
- Concepts
- Location
- Content

The knowledge hierarchy is becoming:

Course

↓

Document

↓

Section

↓

Knowledge Object

↓

Heading and Concepts

This mission also established an important design philosophy:

Deterministic first.

Intelligent second.

Wingman should begin with reliable, explainable, and testable behavior. AI should enhance the system rather than being required for the system to function.

The addition of PowerPoint table extraction demonstrated why document ingestion must account for structure beyond ordinary text boxes.

A slide may contain valuable knowledge in tables, charts, images, speaker notes, or other document elements.

---

## Mission Debrief

### What We Built

Wingman can now:

- Give every document chunk a unique identifier.
- Preserve generic source locations.
- Detect visible PowerPoint headings using deterministic rules.
- Distinguish headings, sections, and concepts.
- Maintain the current section while processing a document.
- Delegate section assignment to a dedicated resolver.
- Extract readable text from PowerPoint tables.
- Represent notes and documents using one consistent evidence schema.
- Preserve structural metadata through retrieval.
- Produce knowledge objects understandable without reopening the original document.

### Biggest Lesson

A document is not knowledge.

A document is a container that holds knowledge.

Wingman should extract that knowledge, preserve its source, enrich its structure, and represent it consistently enough that another engineer or AI system can understand it without needing the original file.

### Architecture Impact

Mission 014 expanded Wingman’s architecture with a dedicated section-resolution component.

The Wingman architecture now consists of:

- `interface.py` — User interaction
- `knowledge.py` — Unified evidence retrieval
- `reasoning.py` — Response generation
- `llm.py` — AI communication and evidence summarization
- `document_ingestion.py` — Document parsing and knowledge-object creation
- `section_resolver.py` — Section-assignment policy

The knowledge pipeline is now:

Raw Document

↓

Text and Table Extraction

↓

Heading Detection

↓

Section Resolution

↓

Structured Knowledge Object

↓

Evidence Retrieval

↓

Reasoning

↓

Summary and Supporting Sources

### Next Mission

**Mission 015 — 🛫 Ready for Takeoff**

**Wingman Enriches Knowledge**

Wingman will begin enriching knowledge objects with concepts and relationships, allowing related ideas to be identified across chunks, sections, documents, and courses.
```
