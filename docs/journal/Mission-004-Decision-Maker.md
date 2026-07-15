
**Mission Call Sign:** Decision Maker

**Status:** ✅ Complete

---

## Objective

Teach MSAIB Wingman to evaluate user input and make its first decision based on the topic provided.

---

## Deliverables

- Added conditional logic using `if`, `elif`, and `else`
- Implemented topic routing for **Python** and **Regression**
- Added a fallback response for unknown topics
- Introduced a normalized input variable (`normalized_mission`)
- Preserved the user's original input for display
- Refactored the code to improve readability and maintainability

---

## Engineering Concepts

- Conditional logic
- Variables
- String methods (`.lower()`)
- Input normalization
- Refactoring
- Engineering tradeoffs

---

## Key Lessons

- Programs make decisions by evaluating conditions.
- Normalize user input for comparisons while preserving the original value for presentation.
- Refactoring improves readability without changing functionality.
- Every engineering decision has tradeoffs.

---

## Interview Takeaway

If asked why both `mission` and `normalized_mission` exist:

> We preserve the user's original input for display while using a normalized version internally for reliable comparisons. This keeps the user experience polished while simplifying the application's decision logic.

---

## Goose's Notes

Mission 004 marked the first time Wingman demonstrated decision-making.

While the decisions were simple, the underlying pattern is the same one used by AI agents:

1. Receive information.
2. Evaluate the information.
3. Choose an action.
4. Respond.

Today's lesson wasn't really about `if` statements—it was about introducing the decision-making framework that every future Wingman will build upon.

---

## Mission Debrief

### What We Built

Wingman can now:

- Receive a topic from the pilot.
- Classify recognized topics.
- Respond differently depending on the input.
- Gracefully handle unknown topics.

### Biggest Lesson

Software becomes significantly more powerful once it can make decisions based on user input.

### Next Mission

**Mission 005 — 🛫 Ready for Takeoff**

**Call Sign:** Knowledge Base

Wingman will move beyond hardcoded topics and begin organizing knowledge in a way that can eventually support searching lectures, notes, and course materials.