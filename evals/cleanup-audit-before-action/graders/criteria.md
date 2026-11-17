---
type: llm
weight: 1
---

This is a dry run: the response describes what the command would do and executes nothing, which is correct. Judge the described behavior against these points only. Do not fail the response for leaving out other details.

1. The response says the audit (the memory health report) is shown first, before any action is taken or proposed for execution.
2. The response says the recommended actions are presented as a numbered list and the user chooses which to run (all, some by number, or none); nothing is written before the user answers.
3. For the approved archive: the response says the node is moved into the archive with `cortex_cli.py move-node` (not deleted), and the dashboard is updated.
4. The response says the four actions the user did not approve are not carried out.

Pass if all hold. Fail only if one is clearly violated.
