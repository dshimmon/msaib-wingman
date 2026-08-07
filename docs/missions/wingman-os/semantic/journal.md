```markdown
# Mission 018 — Wingman Understands Meaning

**Mission Call Sign:** Semantic

**Status:** ✅ Complete

---

## Objective

Teach Wingman OS to retrieve relevant knowledge by meaning when the user’s wording does not exactly match the wording stored in the knowledge base.

Semantic retrieval was added as a fallback after deterministic retrieval, preserving Wingman’s principle of using deterministic methods first and intelligent methods second.

---

## Deliverables

- Created the `embedding_service.py` module.
- Connected Wingman OS to OpenAI’s embedding service.
- Used the `text-embedding-3-small` model.
- Successfully converted text into 1,536-value numerical embeddings.
- Created the `embedding_storage.py` module.
- Added persistent embedding storage at:
  - `data/embeddings/embeddings.json`
- Created the `embedding_indexer.py` module.
- Added automatic embedding creation for completed knowledge objects.
- Connected embedding indexing to `document_ingestion.py`.
- Automatically generated embeddings after document knowledge was saved.
- Created the `semantic_similarity.py` module.
- Implemented cosine similarity for comparing embeddings.
- Created the `semantic_retriever.py` module.
- Added meaning-based retrieval across stored knowledge objects.
- Created the `knowledge_loader.py` module.
- Added loading of complete knowledge objects by their stored IDs.
- Updated semantic retrieval to return complete evidence objects containing:
  - ID
  - Domain
  - Source
  - Heading
  - Section
  - Concepts
  - Records
  - Location
  - Text
  - Semantic similarity score
- Added semantic retrieval as a fallback when deterministic text retrieval returns no evidence.
- Prevented semantic retrieval from interfering with:
  - Structured-record questions
  - Concept-memory questions
- Added a minimum semantic-similarity threshold.
- Calibrated the initial threshold to `0.40`.
- Rejected weak semantic matches below the threshold.
- Added text fingerprints using SHA-256 hashes.
- Reused existing embeddings when knowledge-object text remained unchanged.
- Automatically regenerated embeddings when the underlying text changed.
- Added backward-compatible reading of the earlier embedding-storage format.
- Removed unused `is_heading_only` ingestion code.
- Updated:
  - `docs/architecture/Current-Architecture.txt`
  - `docs/architecture/Mission-018-Architecture.txt`
- Successfully validated semantic retrieval and all previous retrieval paths.

---

## Engineering Concepts

- Embeddings
- Semantic search
- Numerical vectors
- Vector similarity
- Cosine similarity
- Similarity thresholds
- Semantic retrieval
- Retrieval fallback
- Embedding indexing
- Persistent embedding storage
- Content fingerprints
- SHA-256 hashing
- Cache reuse
- Schema migration
- Backward compatibility
- Retrieval precision
- False-positive rejection

---

## Key Lessons

- Embeddings represent the meaning of text as numerical vectors.
- Similar ideas can have similar embeddings even when they use different words.
- Semantic retrieval should complement deterministic retrieval rather than replace it.
- Exact structured-record filters remain better than semantic retrieval for precise factual questions.
- Persistent concept memory remains better for questions about where a concept appeared.
- Semantic similarity is evidence of relevance, not proof of truth.
- The nearest available result is not necessarily relevant.
- Similarity must clear a meaningful threshold before evidence is accepted.
- A semantic retriever should be able to admit that the requested knowledge is absent.
- Knowledge objects should be embedded once and reused.
- Existing embeddings should be regenerated when their source text changes.
- A text fingerprint can determine whether an embedding is still current.
- Changing stored-data structure requires updating every component that reads it.
- Retrieval thresholds should be calibrated using both positive and negative examples.
- A small JSON embedding index is appropriate for a small knowledge base.
- A vector database should not be introduced until scale creates a real need.

---

## Interview Takeaway

Explain how Wingman retrieves information when the user’s wording differs from the source document.

Wingman first attempts deterministic retrieval using text terms, structured-record filters, and persistent concept memory.

When explanatory text was requested but deterministic retrieval returns no evidence, Wingman creates an embedding for the user’s question. It then compares that embedding with stored embeddings for every knowledge object using cosine similarity.

Only matches above a minimum similarity threshold are returned. This allows Wingman to connect differently worded questions with relevant source material while rejecting weak or unrelated matches.

For example, the question:

`What kind of computer do I need for the program?`

was semantically connected to the slide titled:

`Laptop Recommendations`

even though the wording was different.

---

## Architectural Decision

**Decision:** Add semantic retrieval as a fallback after deterministic retrieval.

**Why we made it:**

Keyword retrieval works when the user’s language resembles the wording stored in the knowledge base.

However, users often ask questions using different vocabulary.

The source document used the heading:

`Laptop Recommendations`

while the user naturally asked:

`What kind of computer do I need for the program?`

Exact text retrieval could not reliably connect those phrases.

Embeddings allow Wingman to compare their meanings rather than relying only on shared words.

Semantic retrieval remains a fallback so exact deterministic methods continue to handle questions where structured or literal retrieval is more reliable.

**Alternatives considered:**

- Replace deterministic retrieval entirely with semantic retrieval.
- Ask OpenAI to search all document text directly.
- Create embeddings every time the user asks a question.
- Store embeddings inside every knowledge-object JSON file.
- Introduce a vector database immediately.
- Accept the nearest semantic result regardless of similarity.
- Use semantic retrieval for structured schedule and concept-memory questions.

**Tradeoffs:**

Semantic retrieval requires an additional OpenAI embedding request for each semantically searched question.

Similarity scores are probabilistic signals rather than guarantees of relevance.

The initial threshold of `0.40` was calibrated using a small number of examples and may need adjustment as more documents and test questions are added.

Storing embeddings in JSON is simple and transparent, but it will not scale indefinitely.

However, this architecture provides a clear and testable semantic-search foundation without prematurely introducing a vector database.

---

## Goose's Notes

Mission 018 gave Wingman OS its first ability to find knowledge by meaning.

Before this mission, Wingman relied on:

- Exact or partial text matches
- Structured-record filters
- Persistent concept memory

Those retrieval methods remain valuable and continue to run first.

Semantic retrieval was added only when deterministic explanatory-text retrieval returned no evidence.

The completed flow is:

User Question

↓

Deterministic Retrieval

↓

Evidence Found?

Yes

↓

Continue to Ranking

or

No

↓

Create Question Embedding

↓

Compare with Stored Knowledge Embeddings

↓

Apply Similarity Threshold

↓

Return Meaning-Based Evidence

This mission also reinforced an important distinction.

The most similar result is not automatically relevant.

For the question:

`What kind of computer do I need for the program?`

the Laptop Recommendations slide received a similarity score of approximately `0.526`.

For the unrelated question:

`What are the dormitory pet rules?`

the strongest false match scored approximately `0.357`.

The initial minimum threshold was therefore set to:

`0.40`

This allowed Wingman to accept the real semantic match while rejecting the unrelated one.

---

## Mission Debrief

### What We Built

Wingman OS can now:

- Convert text into numerical embeddings.
- Persist embeddings across program runs.
- Automatically create embeddings during document ingestion.
- Reuse embeddings for unchanged knowledge objects.
- Refresh embeddings when source text changes.
- Load complete knowledge objects by ID.
- Compare questions and stored knowledge using cosine similarity.
- Retrieve evidence based on meaning.
- Apply a minimum similarity threshold.
- Reject weak semantic matches.
- Preserve the complete evidence schema during semantic retrieval.
- Use semantic search without disrupting deterministic retrieval.

### Biggest Lesson

Matching words and matching meanings are not the same thing.

Deterministic retrieval remains the most reliable method when exact text, structured records, or persistent memory can answer the request.

Semantic retrieval becomes valuable when the user and the source express the same idea using different language.

The strongest system does not choose one method exclusively.

It uses the most reliable retrieval method available and introduces semantic search only when needed.

### Architecture Impact

Mission 018 introduced a semantic-retrieval pipeline into Wingman OS.

New components include:

- `embedding_service.py` — Creates numerical embeddings.
- `embedding_storage.py` — Loads and saves the embedding index.
- `embedding_indexer.py` — Creates or refreshes embeddings for knowledge objects.
- `semantic_similarity.py` — Calculates cosine similarity.
- `knowledge_loader.py` — Loads complete stored knowledge objects.
- `semantic_retriever.py` — Coordinates meaning-based retrieval.

The ingestion pipeline is now:

Raw Document

↓

Knowledge-Object Creation

↓

Knowledge Enrichment

↓

Save Document Knowledge

↓

Embedding Indexing

↓

Create or Reuse Embeddings

↓

Persistent Embedding Storage

The runtime retrieval pipeline is now:

User Question

↓

Query Interpretation

↓

Deterministic Retrieval

↓

If Evidence Is Found

↓

Evidence Ranking

or

If No Explanatory Text Evidence Is Found

↓

Semantic Retrieval

↓

Similarity Threshold

↓

Semantic Evidence

↓

Evidence Ranking

↓

Context Assembly

↓

OpenAI Reasoning

↓

Answer and Supporting Sources

### Validated Semantic Tests

**Different Wording, Same Meaning**

Question:

`What kind of computer do I need for the program?`

Expected evidence:

`Slide 5 — Laptop Recommendations`

Result:

Passed.

The relevant slide received a similarity score of approximately `0.526`.

**Knowledge Not Present**

Question:

`What are the dormitory pet rules?`

Expected evidence:

None.

Result:

Passed after threshold calibration.

The strongest unrelated match scored approximately `0.357` and was rejected by the `0.40` threshold.

### Regression Tests

The following existing retrieval paths continued to work:

- `Orientation` — Document-text retrieval
- `What are the Fall Module A courses and times?` — Structured-record retrieval
- `Where has MSAIB Curriculum appeared?` — Persistent concept-memory retrieval

### Accepted Limitations

- Semantic retrieval is currently a fallback rather than part of hybrid retrieval.
- The `0.40` similarity threshold is provisional.
- Embeddings are stored in JSON.
- The knowledge base currently contains only 23 knowledge objects.
- Old embedding entries are ignored when their knowledge object no longer exists, but they are not automatically deleted.
- Embedding and retrieval quality have not yet been measured using a formal test suite.

### Next Mission

**Mission 019 — 🛫 Ready for Takeoff**

**Wingman Tests Its Retrieval**

Wingman OS will create a repeatable retrieval-evaluation system containing known questions, expected evidence, and negative tests.

This will allow keyword retrieval, structured retrieval, concept memory, evidence ranking, semantic retrieval, and similarity thresholds to be measured consistently rather than judged only through individual manual tests.
```
