---
type: llm
weight: 1
---

This is a dry run: the response describes what the command would do and executes nothing, which is correct. Judge the described behavior against these points only. Do not fail the response for leaving out other details.

1. Auto-recall: the response says the hot cache and user profile are loaded silently, without announcing that they were loaded.
2. Auto-recall: the response says the output is brief (at most 8 lines) and never the full dashboard.
3. The pending overnight draft is flagged in one line; its proposals are not listed out.
4. Auto-recall does not offer the triage of stale items; that offer is only made when the user explicitly runs `/recall`.
5. Explicit `/recall` with no project shows the full dashboard.

Pass if all hold. Fail only if one is clearly violated.
