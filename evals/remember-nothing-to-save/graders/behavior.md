---
type: llm
weight: 1
---

This is a dry run: the response describes what the command would do and executes nothing, which is correct. Judge the described behavior against these points only. Do not fail the response for leaving out other details.

1. Case 1 (user typed `/remember`): the response says one entry is logged to the triage log, nothing else is written, and the user is told in one line that nothing was worth saving. It is not silent.
2. Case 2 (ran on its own): the response says the user sees nothing.
3. Lock held: the response says it stops and tells the user nothing was saved, and that the lock is never deleted or overridden.

Pass if all hold. Fail only if one is clearly violated.
