---
max_turns: 10
allowed_tools: [Read, Glob, Grep, Skill]
---

Dry run: load the `/cleanup` instructions with the Skill tool (loading them runs
nothing), then answer without executing anything.

1. My settings put `/cleanup` in `auto` mode. The audit recommends archiving a dormant
   node and expiring three old signal entries. Which of those run without asking me?
2. A node has no wikilinks in or out, and I choose to merge it into another node. What
   happens to the original file?
3. A decision stored as a record under `memory/decision/` has a revisit trigger that
   looks like it fired, and I accept the suggestion to flag it. What is edited?
4. Memory turns out to be clean, with nothing to fix. What do you show me?
