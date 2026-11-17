---
max_turns: 10
allowed_tools: [Read, Glob, Grep, Skill]
---

Dry run: load the `/remember` instructions with the Skill tool (loading them runs nothing), then answer without executing anything.

Two cases. (1) I type plain `/remember` at the end of a conversation that was only small talk, and the triage step returns `commit: false`. What is written and what do you say to me? (2) The same thing happens, but `/remember` ran on its own at the end of the conversation. What do I see? Also: during a write the memory lock is held by another command and stays held after a retry. What do you do?
