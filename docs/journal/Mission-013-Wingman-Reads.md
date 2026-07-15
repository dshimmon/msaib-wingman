# Mission 012 — Wingman Reads Its First Document

**Mission Call Sign:** First Document

**Status:** ✅ Complete

---

## Objective

Teach MSAIB Wingman to ingest its first real course document and convert it into structured, searchable knowledge.

---

## Deliverables

- Created the `document_ingestion.py` module.
- Installed the `python-pptx` package.
- Introduced the document ingestion pipeline.
- Successfully extracted text from a real MSAIB onboarding PowerPoint.
- Preserved document metadata, including:
  - Document name
  - Knowledge domain
  - Slide number
- Converted the PowerPoint into a structured JSON knowledge file.
- Produced Wingman's first machine-readable document representation.

---

## Engineering Concepts

- Document ingestion
- PowerPoint parsing
- Structured data
- JSON serialization
- Metadata
- Knowledge transformation
- Separation of ingestion and retrieval

---

## Key Lessons

- Documents should be ingested only once.
- Raw documents are designed for humans; structured knowledge is designed for software.
- Metadata is just as important as the extracted text.
- A document ingestion pipeline should be independent of knowledge retrieval.
- Good AI systems transform documents into reusable knowledge before attempting retrieval.

---

## Interview Takeaway

Explain why the application converts PowerPoint files into JSON before searching them.

Converting documents into a structured representation creates a reusable intermediate format. This allows retrieval, embeddings, vector search, and future AI features to operate on a consistent knowledge representation rather than repeatedly parsing the original document.

---

## Architectural Decision

**Decision:** Introduce a dedicated `document_ingestion.py` module.

**Why we made it:**

Document ingestion is fundamentally different from document retrieval.

Separating these responsibilities allows Wingman to support additional document types without changing the retrieval architecture.

**Alternatives considered:**

- Parse PowerPoint files directly inside `knowledge.py`.
- Read PowerPoint files every time a search is performed.

**Tradeoffs:**

Introducing a dedicated ingestion step adds an additional processing stage.

However, documents only need to be processed once, dramatically improving future retrieval performance and creating a consistent knowledge representation.

---

## Goose's Notes

Mission 012 represents Wingman's transition from handcrafted knowledge to real-world knowledge.

For the first time, the application successfully processed an authentic document from the MSAIB program instead of relying on manually created notes.

Although Wingman cannot yet retrieve information from the generated JSON knowledge, the ingestion pipeline has been established.

This mirrors the first stage of modern Retrieval-Augmented Generation (RAG) systems:

Document

↓

Ingestion

↓

Structured Knowledge

↓

(Retrieval comes next)

---

## Mission Debrief

### What We Built

Wingman can now:

- Read PowerPoint documents.
- Extract slide-level knowledge.
- Preserve source metadata.
- Convert documents into structured JSON.
- Create reusable knowledge files ready for future retrieval.

### Biggest Lesson

Documents are temporary.

Knowledge is permanent.

Wingman should transform documents into structured knowledge that can be searched, retrieved, and reasoned about long after the original document has been processed.

### Architecture Impact

Mission 012 introduced a dedicated document ingestion pipeline.

The Wingman architecture now consists of:

- `interface.py` — User interaction
- `knowledge.py` — Knowledge retrieval
- `reasoning.py` — Response generation
- `llm.py` — AI communication
- `document_ingestion.py` — Knowledge creation

This establishes a complete document-processing pipeline and prepares the project for unified knowledge retrieval.

### Next Mission

**Mission 013 — 🛫 Ready for Takeoff**

**Wingman Unifies Knowledge**

Wingman will combine handwritten notes and ingested documents into a single searchable knowledge system, creating one source of truth for all future retrieval.