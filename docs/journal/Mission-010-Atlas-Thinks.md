# Mission 010 — First Flight

**Mission Call Sign:** First Flight

**Status:** ✅ Complete

---

## Objective

Integrate a real Large Language Model into MSAIB Wingman while preserving the modular architecture developed during the previous missions.

---

## Deliverables

- Created `llm.py`.
- Loaded the OpenAI API key securely from `.env`.
- Added `.env` to `.gitignore`.
- Installed the `openai` and `python-dotenv` packages.
- Connected Wingman to the OpenAI API.
- Replaced the handcrafted summary with an AI-generated summary.
- Preserved source attribution beneath the generated response.
- Completed Wingman’s first successful LLM-powered response.

---

## Engineering Concepts

- APIs
- API keys
- Environment variables
- Secure credential management
- External Python packages
- Request-and-response cycles
- LLM integration
- Dependency isolation
- Modular AI architecture

---

## Key Lessons

- An LLM should be treated as one service within a larger application, not as the entire application.
- Good architecture allows the implementation of one module to change without forcing changes throughout the system.
- API keys should never be stored directly in source code or committed to GitHub.
- Retrieval should happen before generation so the model receives grounded context.
- AI-generated summaries should remain connected to their original sources.

---

## Interview Takeaway

Explain why the LLM integration was isolated inside `llm.py`.

The rest of the application should not depend directly on a specific AI provider or model. Isolating the API integration makes it easier to change models, compare providers, add caching, or introduce local models without redesigning the entire application.

Also explain the current information flow:

1. The pilot enters a topic.
2. Wingman searches the local knowledge base.
3. Relevant notes are retrieved.
4. The notes are sent to the LLM as context.
5. The LLM generates a concise summary.
6. Wingman displays the summary and preserves the original sources.

---

## Architectural Decision

**Decision:** Place all OpenAI communication inside a dedicated `llm.py` module.

**Why we made it:**  
The application needed a clean boundary between Wingman’s internal logic and the external AI service.

**Alternatives considered:**  

- Place the API call directly inside `main.py`.
- Place the API call directly inside `reasoning.py`.
- Delay creating a separate module until the application grew larger.

**Tradeoffs:**  

- A separate module adds another file and import.
- In return, it significantly improves maintainability, security, flexibility, and provider independence.

---

## Goose's Notes

Mission 010 marked MSAIB Wingman’s first successful use of a real Large Language Model.

The most important achievement was not the API call itself. It was proving that the architecture could absorb a new intelligence layer without requiring major changes to `main.py`, `interface.py`, or `knowledge.py`.

Wingman successfully:

1. Received a user request.
2. Retrieved relevant knowledge.
3. Sent grounded context to an LLM.
4. Generated a concise response.
5. Preserved the path back to the original source.

This mission implemented one of the central principles of the Wingman Architecture Philosophy:

> **Wingman summarizes information, but always preserves a path back to the source.**

---

## Mission Debrief

### What We Built

Wingman can now:

- Communicate with a real LLM.
- Generate summaries from retrieved notes.
- Keep AI integration isolated from the rest of the application.
- Protect sensitive credentials using environment variables.
- Display source material beneath its AI-generated response.

### Biggest Lesson

AI is not the product.

AI is one component inside a thoughtfully engineered product.

### Architecture Impact

Mission 010 added the intelligence layer without disrupting the existing architecture.

The current structure is now:

- `main.py` — Application coordination
- `interface.py` — User interaction
- `knowledge.py` — Knowledge retrieval
- `reasoning.py` — Response orchestration
- `llm.py` — External model communication
- `data/` — External knowledge sources

This confirms that Wingman’s modular architecture can support new intelligence capabilities while remaining maintainable and extensible.

### Product Issue Discovered

Wingman currently uses two separate systems:

- `topics.json` for topic-to-course routing
- Notes files for knowledge retrieval

This creates a contradiction when a topic exists in the notes but not in `topics.json`. Wingman may say that the course is unknown while still producing a valid summary.

This issue becomes the focus of Mission 011.

### Next Mission

**Mission 011 — 🛫 Ready for Takeoff**

**Call Sign:** Unified Intelligence

Wingman will unify course routing and knowledge retrieval so it answers one consistent question:

> **Can Wingman answer this topic, and where did the answer come from?**