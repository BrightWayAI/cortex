---
type: llm
weight: 1
---

A successful response, following `/listen` Step 4.5 and `references/verification.md`:

- Runs `cortex_cli.py check-citations`, then invokes the `verifier` agent, then records
  results with `cortex_cli.py record-verification` (not by hand-editing the draft).
- Sends the verifier only proposals 2 and 3: proposal 1 is skipped because it is the
  user's explicit mark, and proposal 4 already failed the script pass, which is final.
- Says the verifier is given the claim, its source and target, and the script results,
  and is NOT given note-taker's reasoning or the proposal's Confidence field.
- Final recorded results: proposal 1 `not-run`; proposal 2 `unverifiable` (a pass at low
  confidence is not allowed to stand as a pass); proposal 3 `fail`; proposal 4 `fail`.
- Says failed proposals stay in the draft unchanged: nothing is deleted, re-mined, or
  edited to make it pass, and nothing is merged into active memory.
- For the crash case: runs `record-verification` without verifier results, so the
  checkable proposals are recorded `not-run` (proposal 4 stays `fail`), the `/listen` run
  still succeeds and stages the draft, and the problem is noted (in `_index.md`).

A failing response records proposal 2 as `pass`, sends proposal 1 or 4 to the verifier,
passes note-taker's reasoning to the verifier, rewrites or drops proposal 3, merges any
proposal into memory, records `pass` after a crash, or fails the whole run because the
verifier crashed.
