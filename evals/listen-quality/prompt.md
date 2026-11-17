---
max_turns: 12
allowed_tools: [Read, Glob, Grep, Skill]
---

Dry run, write nothing: load the `/listen` instructions with the Skill tool. Treat this as `/listen --remine` for yesterday: read yesterday's kickoff transcript under `archive/<yesterday>/transcripts/` in the config folder and tell me exactly which memory proposals Step 3 and Step 4 would stage from it, in the commit-draft format.
