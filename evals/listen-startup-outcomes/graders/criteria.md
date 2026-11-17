---
type: llm
weight: 1
---

This is a dry run: the response describes what the scheduled run would do and executes
nothing, which is correct. Judge the described behavior against these points only. Do
not fail the response for leaving out other details.

1. Unreachable root: the response says the run writes or emits a failure receipt with
   the `config_root_unreachable` error and actor `sample-user` (from the registered
   prompt, not guessed), exits non-zero, does not report success, and does no other
   work.
2. Already running: the response says this run exits without doing the work and does
   not overwrite or force past the other run.
3. Unreadable brief-mining reference: the response says the run does not improvise that
   procedure; it records that brief mining was skipped, marks the run as partial, and
   continues with the rest.
4. Error during mining: the response says the shut-down step still runs: a failure line
   is recorded, the in-progress marker and lock are removed, and the failure is
   reported rather than hidden.
5. In none of the four cases does the response say the run asks the user a question or
   waits for input.

Pass if all five hold. Fail only if one is clearly violated.
