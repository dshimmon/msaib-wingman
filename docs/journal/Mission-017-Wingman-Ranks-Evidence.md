```markdown
# Mission 017 — Wingman Ranks Evidence

**Mission Call Sign:** Priority

**Status:** ✅ Complete

---

## Objective

Teach Wingman OS to score and order retrieved evidence so the strongest supporting information reaches the language model first.

Atlas served as the first product used to validate this reusable ranking capability.

---

## Deliverables

- Created the `evidence_ranker.py` module.
- Added evidence ranking to the runtime pipeline.
- Kept ranking separate from:
  - Retrieval
  - Context assembly
  - LLM communication
- Created a deterministic relevance-scoring system.
- Added ranking signals for:
  - Exact heading matches
  - Partial heading matches
  - Section matches
  - Text matches
- Added a relevance score to each retrieved evidence object.
- Sorted evidence from highest to lowest relevance score.
- Preserved the original order when multiple evidence items received the same score.
- Temporarily displayed relevance scores for testing.
- Confirmed that Slide 7 ranked above Slide 23 for the topic `Orientation`.
- Confirmed that Slide 8 ranked first for the broader topic `Fall`.
- Removed the temporary relevance-score display after validation.
- Verified that ranking did not interfere with:
  - Structured course-schedule retrieval
  - Persistent concept-memory retrieval
- Updated `Current-Architecture.txt`.
- Created `Mission-017-Architecture.txt`.

---

## Engineering Concepts

- Evidence ranking
- Relevance scoring
- Deterministic algorithms
- Weighted scoring
- Stable sorting
- Retrieval precision
- Retrieval recall
- Separation of responsibilities
- Regression testing
- Explainable ranking
- Reusable platform capabilities

---

## Key Lessons

- Retrieval and ranking are different responsibilities.
- Retrieval determines which evidence may be relevant.
- Ranking determines which retrieved evidence should appear first.
- Matches inside headings are usually stronger than matches inside body text.
- Match location can be more useful than repeated word counts.
- A simple and explainable scoring model is a better starting point than a complicated algorithm.
- Ranking should not interfere with exact structured-record filters.
- Ranking should not disturb persistent concept-memory retrieval when no ranking terms are provided.
- Evidence with equal scores can preserve its existing order until a real need for tie-breaking appears.
- A ranking test requires multiple competing evidence items.
- One retrieved source cannot prove that ranking works.
- Platform-level capabilities should be built in Wingman OS and validated through a specific Wingman product.

---

## Interview Takeaway

Explain how Wingman decides which retrieved evidence reaches the language model first.

Wingman separates retrieval from ranking.

The retrieval system first finds all evidence that may match the structured retrieval plan. The evidence ranker then assigns an explainable score based on where the search term appears.

For example, an exact heading match receives more weight than a body-text match. Evidence is then sorted by score before it is passed to the context builder and language model.

This creates a deterministic and inspectable relevance baseline before introducing embeddings or machine-learning ranking methods.

---

## Architectural Decision

**Decision:** Introduce a dedicated deterministic evidence-ranking module between retrieval and context assembly.

**Why we made it:**

As Wingman’s knowledge base grows, a search may retrieve many possible evidence items.

Passing every matching item to the language model without prioritization would introduce unnecessary context, increase cost, and make answers more vulnerable to irrelevant information.

Ranking allows Wingman to place the strongest evidence first while keeping the ranking logic independent from retrieval and LLM reasoning.

**Alternatives considered:**

- Allow retrieval order to determine evidence priority.
- Ask OpenAI to rank all retrieved evidence.
- Count every occurrence of a search term.
- Introduce embeddings immediately.
- Build a complex ranking formula before collecting more documents.

**Tradeoffs:**

The initial scoring model is intentionally simple.

It cannot yet understand semantic similarity, and evidence with equal scores remains tied.

However, the scoring system is deterministic, explainable, easy to test, and provides a baseline that future semantic ranking can be compared against.

---

## Goose's Notes

Mission 017 introduced the first prioritization capability in Wingman OS.

Before this mission, Wingman retrieved evidence and passed it forward in the order it was found.

After this mission, Wingman can distinguish between stronger and weaker matches.

For the topic:

`Orientation`

Atlas ranked the primary orientation slide above a later slide that only mentioned orientation in its body text.

The scoring model used observable evidence:

Exact heading match

↓

Section match

↓

Text match

This mission also clarified the distinction between Wingman OS and Atlas.

Evidence ranking is not specifically an academic feature.

The same ranking system can later support:

- Academic documents in Atlas
- Investment research in Radar
- Career documents in Vector
- Research sources in Recon
- Consulting materials in Forge

Atlas is the first product validating the reusable Wingman OS capability.

---

## Mission Debrief

### What We Built

Wingman OS can now:

- Assign relevance scores to retrieved text evidence.
- Reward exact heading matches.
- Reward partial heading matches.
- Reward section matches.
- Reward body-text matches.
- Sort evidence by relevance.
- Preserve stable ordering for tied evidence.
- Pass ranked evidence into the context builder.
- Display supporting sources in ranked order.
- Leave structured-record and concept-memory retrieval unchanged.

### Biggest Lesson

Finding relevant evidence is not enough.

As the knowledge base grows, Wingman must also determine which evidence deserves priority.

A simple deterministic ranking system gives Wingman an explainable baseline before more advanced semantic methods are introduced.

### Architecture Impact

Mission 017 added a ranking stage between retrieval and context assembly.

The runtime pipeline is now:

User Question

↓

Query Interpretation

↓

Structured Retrieval Plan

↓

Deterministic Retrieval

↓

Unified Evidence

↓

Evidence Ranking

↓

Ranked Evidence

↓

Context Assembly

↓

LLM Reasoning

↓

Answer and Supporting Sources

The new runtime component is:

- `evidence_ranker.py` — Deterministic evidence scoring and ordering

### Validated Ranking Tests

**Orientation**

- Slide 7 received the strongest score because the term appeared in its heading, section, and text.
- Slide 23 received a lower score because the term appeared only in its body text.

**Fall**

- Slide 8 ranked first because `Fall` appeared in its heading.
- Other slides mentioning `Fall` only in their body text ranked below it.

**Structured Schedule Retrieval**

The Fall Module A course schedule continued to retrieve only the matching structured records.

**Concept-Memory Retrieval**

The MSAIB Curriculum occurrence question continued to retrieve Slides 8, 9, and 10 from persistent memory.

### Next Mission

**Mission 018 — 🛫 Ready for Takeoff**

**Wingman Understands Meaning**

Wingman OS will introduce embeddings and semantic retrieval so evidence can be found by meaning even when the user’s wording does not exactly match the source text.

The deterministic ranking system from Mission 017 will remain as an explainable baseline and may later be combined with semantic similarity scores.
```
