---
type: llm
weight: 1
---

This is a dry run: the response describes what the command would do and executes nothing, which is correct. Judge the described behavior against these points only. Do not fail the response for leaving out other details.

1. The response says the skip is logged with one of a fixed set of reason codes (such as not-stale, intentional-archive, pending-review, unclear), not with the user's free-form text.
2. The response says the free-text reason ("medical leave") is NOT written into the skip log.
3. The response does not record the medical detail anywhere on its own; at most it suggests the user put any nuance they want kept in the line itself or the node's notes.

Pass if all hold. Fail only if one is clearly violated.
