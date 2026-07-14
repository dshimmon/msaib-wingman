# Knowledge Flow

## Purpose

Describe how knowledge moves through MSAIB Wingman.

---

## Current Flow

Pilot

↓

Interface

↓

Reasoning (currently in `main.py`)

↓

Knowledge (`knowledge.py`)

↓

Knowledge Files (`data/notes/*.txt`)

↓

Relevant Results

↓

Interface

↓

Pilot

---

## Design Principles

- Knowledge should be stored outside the application logic.
- Knowledge retrieval should be reusable.
- The application should know **where** information came from.
- Presentation should remain separate from retrieval.
- Future knowledge sources (PDFs, lecture slides, textbooks, RAG) should plug into this architecture without changing the application's overall flow.

---

## Future Evolution

Current

Topic → Text File

↓

Next

Topic → Multiple Course Files

↓

Later

Topic → PDFs

↓

Future

Topic → Vector Database (RAG)

↓

Long-Term

Topic → Multi-Agent Knowledge System