# Decision records (v4.38+)

A decision gets its own file, so that six months later you can answer: what did we
decide, on what information, who decided, when, and has it been replaced?

One file per decision at `<config-root>/memory/decision/<YYYY-MM-DD>-<slug>.md`.

## What counts as a decision

A choice that commits you going forward and that someone might later ask "why did we do
it this way?" about: picking a vendor, setting a price, changing a process, declining a
kind of work, a staffing call. Cues: "we decided", "I'm going with", "settled on",
"going forward we'll", "the call is".

Not a decision record: a lesson learned (LESSON), a fact about how something works
(MODEL, INSIGHT), a to-do or commitment (open thread), or a preference about how you
like to work (user node).

## The record

```markdown
---
type: decision
decided: 2026-11-16
decided_by: sample-user
status: active
supersedes: decision/2026-05-15-crm-choice
affects: [client/acme, bizdev/atlas-ventures]
recorded_by: /remember
---

# Use Pipedrive as the CRM

## Decision
What was decided, stated so it stands on its own.

## Inputs
- The facts and sources the decision rested on, each with where it came from.

## Why
The reasoning at the time.

## Affects
- [[client/acme]]

## Revisit when
What would reopen this, or n/a.
```

| Field | Rule |
|---|---|
| `decided` | The date the decision was made, not the date it was recorded |
| `decided_by` | The Actor ID of the person who decided. Required. A record is never written with no decider or with `unresolved`. An agent never decides; it records. |
| `status` | `active`, or `superseded` once a later decision replaces it |
| `supersedes` | The earlier decision this replaces, if any |
| `superseded_by` | Added to the earlier record when it is replaced |
| `affects` | Node ids this decision bears on |
| `recorded_by` | The command that wrote the record |
| Inputs | What was known at the time, with sources. This is what lets a later reader judge the decision fairly. |

## Rules

1. **Write records only through the CLI:**
   `python3 scripts/cortex_cli.py record-decision --memory-root <config-root>/memory --title "<one line>" --what "<what>" --why "<why>" --decided-by <actor-id> --date <YYYY-MM-DD> [--input "<fact, source>"]... [--affects <node-id>]... [--supersedes decision/<id>] [--revisit-when "<trigger>"] [--recorded-by /morning]`
   It validates the fields, takes the memory lock, refuses to overwrite, and marks the
   superseded record in the same operation.
2. **A decision is never edited to say something different.** If the decision changes,
   record a new one with `--supersedes`. The old record stays, marked `superseded`, with
   its original text. Fixing a typo is fine; changing what was decided is not.
3. **A record is never deleted.**
4. **Only one decision supersedes another.** To replace a decision that has already been
   replaced, supersede the newest one in the chain.
5. **Each affected node gets a pointer, not a copy.** The CLI returns a `pointer_line`:
   `DECISION [confirmed:<date>] <title> → [[decision/<id>]] [by:<actor>]`. Append it to
   the `## Knowledge` section of each affected node. The reasoning lives in the record.
6. **Decisions mined overnight are proposals.** `/listen` may propose a decision it found
   in a transcript; the record is written only when the user accepts it in `/morning`,
   and `decided_by` is the user.

## Older inline decisions

Before 4.38 a decision was a multi-line `DECISION` entry inside a node. Those entries
remain valid and readable. They are not migrated automatically. New decisions use
records.
