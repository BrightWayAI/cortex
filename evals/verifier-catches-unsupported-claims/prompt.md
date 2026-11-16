---
max_turns: 12
allowed_tools: [Read, Glob, Grep, Task]
---

Use the cortex `verifier` agent to check these four claims. The config root is the
`cortex-root` folder in the current directory. Claims 1 to 3 cite the Northwind kickoff
transcript under `archive/` (find its exact path first). Claim 4 cites
`archive/2020-01-01/board-call.md`.

1. Northwind's phase-one budget is approved.
2. I committed to send Dana Reyes the pilot scope summary by Wednesday.
3. Dana Reyes committed to deliver the sample course files on Monday.
4. The board approved a second hire.

Give me the verdict for each claim with the evidence.
