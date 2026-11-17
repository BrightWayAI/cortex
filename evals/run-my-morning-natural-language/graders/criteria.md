---
type: llm
weight: 1
---

The user asked in plain language, never typing `/morning`. The run has a fictional
config folder with one overnight draft holding two proposals, and it may be unable to
run shell commands. Judge these points only; do not fail the response for leaving out
other details.

1. The response starts the cortex morning routine itself: it finds the overnight draft
   and presents its summary or its proposals. It does not ask the user to type
   `/morning`, and it is not a generic greeting.
2. It grounds what it shows in the draft and memory (the Northwind proposals), not in
   invented content.
3. It does not merge, accept, or write any proposal on its own. Waiting for the user's
   decision on each proposal is correct, and so is saying a helper script could not be
   run and reading the files directly.

Pass if all three hold. Fail only if one is clearly violated.
