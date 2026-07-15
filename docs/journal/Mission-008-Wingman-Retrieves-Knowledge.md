# Mission 008 — Knowledge Retrieval

**Mission Call Sign:** Knowledge Retrieval

**Status:** ✅ Complete

---

## Objective

Teach MSAIB Wingman to retrieve relevant information from an external knowledge source rather than simply recognizing topics.

---

## Deliverables

- Created the `data/notes` directory.
- Added the first searchable knowledge file (`programming.txt`).
- Implemented `search_notes()` in `knowledge.py`.
- Introduced `pathlib` to automatically discover every notes file.
- Refactored the search function to search all `.txt` files inside `data/notes`.
- Enhanced search results to display both the matching note and its source file.

---

## Engineering Concepts

- File I/O
- `pathlib`
- Iteration
- Search algorithms
- Data retrieval
- Tuples
- Unpacking
- Separation of knowledge and presentation

---

## Key Lessons

- Applications should retrieve knowledge rather than hardcode information.
- Designing software for future growth often requires changing the architecture before adding new features.
- A search function should scale automatically as new knowledge sources are added.
- Good software explains not only **what** it found, but also **where** it found it.

---

## Interview Takeaway

Explain why the application searches every file inside the `data/notes` directory instead of searching individual files one by one.

Searching an entire directory makes the application scalable. New knowledge files can be added without modifying the application's logic, making the software significantly easier to maintain and extend.

---

## Goose's Notes

Mission 008 represents the first implementation of knowledge retrieval within the Wingman architecture.

Although the knowledge currently resides in simple text files, the retrieval pipeline mirrors the same architectural pattern that future Retrieval-Augmented Generation (RAG) systems will follow:

1. Receive a topic.
2. Search available knowledge.
3. Retrieve relevant information.
4. Present the results to the user.

Today's implementation replaces hardcoded knowledge retrieval with a reusable search architecture that can later evolve to support lecture notes, PDFs, and vector databases.

---

## Mission Debrief

### What We Built

Wingman can now:

- Search every knowledge file stored in `data/notes`.
- Retrieve relevant information for a requested topic.
- Display both the matching content and its source.
- Scale automatically as additional knowledge files are added.

### Biggest Lesson

Separating **knowledge**, **retrieval**, and **presentation** creates software that is significantly easier to scale than embedding knowledge directly inside application logic.

### Next Mission

**Mission 009 — 🛫 Ready for Takeoff**

**Call Sign:** Intelligent Responses

Wingman will move beyond retrieving information and begin generating intelligent responses based on the knowledge it finds, laying the groundwork for future LLM integration.