---
max_turns: 10
allowed_tools: [Read, Glob, Grep, Skill]
---

Dry run: load the `/recall` instructions with the Skill tool (loading them runs
nothing), then answer without executing anything.

1. I type `/recall @priya` for the third time. Priya has no person page. What happens,
   and is a page created?
2. I type `/recall client/northwind --full`. One knowledge entry was last confirmed long
   enough ago to count as dormant. How is it shown, is the entry's text in the file
   changed, and what are I offered afterwards?
3. Would I be offered the same thing if that entry had come up on its own at the start
   of a conversation?
