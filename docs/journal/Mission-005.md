# Mission 006 — External Knowledge

**Mission Call Sign:** External Knowledge

**Status:** 🛫 Ready for Takeoff

---

## Objective

Move Wingman's knowledge out of the Python code and into an external knowledge file. By separating knowledge from logic, Wingman will be able to learn new topics without modifying the application itself.

---

## Mission Requirement

Wingman should no longer rely on a hardcoded knowledge base inside `main.py`.

Instead, it should retrieve course information from an external file that can be updated independently of the program.

---

## Deliverables

- Create Wingman's first external knowledge file.
- Move the topic-to-course mappings out of `main.py`.
- Update Wingman to read from the external knowledge source.
- Verify that new topics can be added without changing the application's logic.

---

## Engineering Concepts

- Separation of knowledge and logic
- External configuration
- Reading files
- Maintainability
- Scalability

---

## Success Criteria

By the end of the mission:

- Wingman's knowledge is no longer hardcoded.
- New topics can be added by editing only the knowledge file.
- No Python logic changes are required when expanding Wingman's knowledge base.

---

## Interview Focus

Be prepared to explain why separating knowledge from application logic improves maintainability, scalability, and long-term software design.

---

## Goose's Notes

This is one of the most important architectural milestones in the project.

Today, Wingman stops learning from code and begins learning from data.

That same architectural principle will eventually scale to:

- Lecture notes
- PDFs
- Textbooks
- RAG
- Vector databases

Everything we build from this point forward will follow this pattern.