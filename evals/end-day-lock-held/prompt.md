---
max_turns: 10
allowed_tools: [Read, Glob, Grep, Skill]
---

/cortex:end-day This is a dry run. Do not execute any step, read or write nothing, and call no tools. Using only these instructions, answer the following.

Near the end of `/end-day`, at the memory commit step, `cortex_cli.py lock-acquire` exits 1 because another command holds the write lock. What do you do about the commit, about the lock file, and about the rest of the run? Separately: if a transcript contained "I'll send Dana the scope summary by Friday", does that become a CRM task?
