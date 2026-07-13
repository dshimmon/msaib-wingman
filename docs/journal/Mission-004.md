Mission 004 — Decision Maker
Objective

Teach MSAIB Wingman to evaluate user input and make its first decision based on the topic provided.

Deliverables
Added conditional logic using if, elif, and else
Implemented topic routing for Python and Regression
Added a fallback path for unknown topics
Introduced input normalization using normalized_mission
Preserved the user's original input for display
Engineering Concepts
Conditional logic
Variables
String methods (.lower())
Input normalization
Refactoring
Engineering tradeoffs
Key Lessons
Programs make decisions by evaluating conditions.
Normalize data for comparisons while preserving the original data for presentation.
Clean code minimizes repetition.
Refactoring improves readability without changing behavior.
Interview Takeaway

Describe why both mission and normalized_mission exist.

The original input is preserved for the user interface, while the normalized version is used internally for reliable comparisons.