---
max_turns: 10
allowed_tools: [Read, Glob, Grep, Skill]
---

Dry run: load the `/listen` instructions with the Skill tool (loading them runs
nothing), then tell me what the scheduled run does in each of these four separate
situations. Execute nothing.

1. `listen-start` exits 3 with status `unreachable`. The registered prompt names actor
   `sample-user`.
2. `listen-start` exits 4 with status `already-running`.
3. `listen-start` exits 0, but later the brief-mining reference file cannot be read.
4. Everything works until the mining step, which throws an error halfway through.
