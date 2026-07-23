# Mission 006 — External Knowledge

**Mission Call Sign:** External Knowledge

**Status:** ✅ Complete

---

## Objective

Move Wingman's knowledge out of the application logic and into an external data source, allowing the application to learn new topics without modifying the Python code.

---

## Deliverables

- Created the `data` directory.
- Created `topics.json`.
- Moved topic knowledge out of `main.py`.
- Loaded knowledge using Python's `json` module.
- Successfully verified that Wingman could retrieve knowledge from an external source.

---

## Engineering Concepts

- JSON
- External data
- Separation of knowledge and logic
- Reading files
- Data-driven applications

---

## Key Lessons

- Good software separates application logic from application knowledge.
- Data can evolve independently from code.
- External knowledge sources are easier to maintain and expand.
- Small architectural improvements create significant long-term scalability.

---

## Interview Takeaway

Explain why storing knowledge in an external JSON file is preferable to hardcoding values directly into the application.

Separating knowledge from logic allows the software to grow without continually modifying the underlying code. This makes the application easier to maintain, easier to test, and significantly more scalable.

---

## Goose's Notes

Mission 006 represents one of the most important architectural shifts in MSAIB Wingman.

For the first time, Wingman learned information from a source outside the application itself.

Although the current knowledge base is small, the architecture now mirrors the pattern that future versions will use for lecture notes, PDFs, and Retrieval-Augmented Generation (RAG).

This mission was not about JSON—it was about changing where knowledge lives.

---

## Mission Debrief

### What We Built

Wingman can now:

- Load knowledge from an external file.
- Expand its knowledge without modifying Python code.
- Continue separating knowledge from application logic.

### Biggest Lesson

Software becomes significantly easier to maintain when knowledge is treated as data instead of being embedded directly into application logic.

### Next Mission

**Mission 007 — 🛫 Ready for Takeoff**

**Call Sign:** Modular Wingman