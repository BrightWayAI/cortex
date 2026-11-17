---
type: llm
weight: 1
---

This is a dry run: the response describes what the command would do and executes nothing, which is correct. Judge the described behavior against these points only. Do not fail the response for leaving out other details.

1. The response says quick mode skips the commit-worthiness triage and the full extraction; it does not analyze the whole conversation.
2. The response says one line is added to the Northwind node's `## Changelog` through `cortex_cli.py` (the `prepend-section` command), not by editing the file by hand.
3. The response says the reply to the user is a single confirmation line of the form "Noted in client/northwind: ...", with no analysis and no follow-up questions.

Pass if all hold. Fail only if one is clearly violated.
