---
max_turns: 10
allowed_tools: [Read, Glob, Grep, Skill]
---

Dry run: load the `/listen` instructions with the Skill tool (loading them runs
nothing), then walk Step 4.5 against this exact scenario without executing any step.
Tell me what it runs, what it passes to whom, and what ends up in the draft.

Last night's commit draft has four proposals. Proposal 1 is an explicit "done" mark I
clicked in yesterday's brief (tagged `from: listen-step-1.5`). Proposals 2, 3 and 4 were
mined by note-taker from a transcript. `check-citations` reports proposal 2 as
`pass-verbatim`, proposal 3 as `needs-verifier`, and proposal 4 as `fail`
(`source-file-missing`). The verifier agent then returns `pass` with `low` confidence
for proposal 2 and `fail` for proposal 3 because the source says Friday and the proposal
says Wednesday.

Also tell me what would happen instead if the verifier agent had crashed.
