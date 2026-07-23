# Mission 005 — Knowledge Base

**Mission Call Sign:** Knowledge Base

**Status:** ✅ Complete

---

## Objective

Separate Wingman's knowledge from its application logic by introducing a dedicated knowledge base.

---

## Deliverables

- Replaced hardcoded topic routing with an external knowledge structure.
- Introduced the first knowledge base (`topics.json`).
- Updated Wingman to retrieve course information from data rather than application logic.
- Added support for multiple topic aliases (e.g., `api`, `apis`, `learn apis`).

---

## Engineering Concepts

- Data-driven applications
- JSON
- Knowledge bases
- Separation of knowledge and logic
- Scalability
- Maintainability

---

## Key Lessons

- Knowledge should be stored as data rather than embedded directly into application logic.
- Well-designed software grows by expanding its knowledge, not by repeatedly modifying its code.
- One reusable retrieval mechanism is preferable to many specialized implementations.
- Architecture should anticipate growth without becoming unnecessarily complex.

---

## Interview Takeaway

Explain why storing application knowledge inside a JSON file is preferable to writing long chains of `if` / `elif` statements.

Separating knowledge from application logic makes software significantly easier to maintain, extend, and test as the knowledge base grows.

---

## Goose's Notes

Mission 005 marked the beginning of Wingman's transition from a hardcoded application into a configurable system.

Rather than teaching Wingman new topics by modifying Python code, new knowledge could now be added simply by updating the knowledge base.

This architectural decision established the pattern that future versions of Wingman will use for lecture notes, PDFs, textbooks, and eventually Retrieval-Augmented Generation (RAG).

---

## Mission Debrief

### What We Built

Wingman can now:

- Load topics from an external knowledge base.
- Expand its understanding without modifying Python code.
- Support multiple aliases for the same concept.

### Biggest Lesson

Good software separates **knowledge** from **logic**.

The application should focus on **how** to think, while its knowledge should remain independent and easily expandable.

### Architecture Impact

Mission 005 introduced the first external knowledge layer.

Instead of embedding knowledge inside application logic, Wingman now retrieves information from an independent data source.

This architectural pattern becomes the foundation for every future knowledge source added to the platform.

### Next Mission

**Mission 006 — 🛫 Ready for Takeoff**

**Call Sign:** External Knowledge

Wingman will move beyond structured topic mappings and begin retrieving information from external notes.