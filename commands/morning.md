---
description: Interactive morning routine. Reads the most-recent `<config-root>/memory/staged/commit-drafts/` file (produced overnight by `/listen`), walks the user through the proposals (verified ones together, the rest one at a time), applies accepted proposals to active memory nodes, shows anything that went quiet, refreshes hot.md and the memory index, captures a short reflection and seeds today's brief priorities/outreach, and optionally chains into `/brief`.
---

# /morning

Walk the draft `/listen` staged overnight with the user, then hand off to the brief. Every accepted proposal is confirmed by the user; nothing merges silently.

## Step G — Config-root guard (run first)

Run `python3 scripts/cortex_cli.py root-status`. If it exits non-zero, **stop** and show its sentence verbatim; write nothing anywhere else and do not ask for folder access more than once per session. Exception: in a remote session with the sync repos attached, run the documented `bootstrap` (`references/core-contract.md` §11B) once and re-check before stopping.

## Step 0 — Find the draft

The helper scripts named below (`memory-diff`, `triage-draft`, `open-nudges`) only read. On a host where they cannot be run, do the same reading by hand, say so once, and continue; only Step G stops the run.

On a host with no resolved root (a cloud chat), run `python3 scripts/cortex_cli.py bootstrap --print-env` first. If the root is a synced checkout, run `cortex_cli.py sync` before reading and after the final write; always report a failed sync.

Find the most recent draft in `<config-root>/memory/staged/commit-drafts/*.md` by the date in the filename, not mtime.

- `--date YYYY-MM-DD` → use that draft instead.
- `--discard` → move the latest draft to `staged/commit-drafts/archive/<date>-discarded.md` and exit.

Check for open nudges: `python3 scripts/cortex_cli.py open-nudges --config-root <config-root>` (read-only).

- **No draft, no open nudges** → "No `/listen` draft to merge. Did `/listen` run last night?" List any `archive/<date>/_index.md` from the last 3 days, offer to run `/listen` for yesterday, otherwise exit.
- **No draft, open nudges** → say "No overnight draft to review," skip Steps 0.5 through 3, and go to Step 2.95.

## Step 0.5 — Memory diff review

Shows what already landed in memory since the previous commit. Skip if `cortex.user-context.md` has `memory_as_git.morning_diff: false`.

Run `python3 scripts/cortex_cli.py memory-diff --config-root <config-root>` (read-only) and act on `status`:

| `status` | Do |
|---|---|
| `not-git`, `no-changes` | Skip silently. |
| `fresh` | Say there is no prior commit to diff against. Continue. |
| `no-overnight-commit` | Say there has been no memory commit since today's last close. Continue. |
| `listen-running` | "Overnight /listen is still running (started <N> min ago). Wait 2 min and re-run /morning, or skip the diff review now?" Wait → exit. Skip → continue and note it. |
| `dirty` | "⚠ Uncommitted memory changes from yesterday — the last close may have failed." Show `dirty_files`. Offer **(c)ommit-now** (`git add . && git commit -m "Recovery commit (committed by /morning Step 0.5)"` in the memory folder), **(i)nspect** (`git status` and `git diff`, then ask again), or **(s)kip**. |
| `changed` | Show the previous commit date, nodes changed per directory, insertions, deletions, and files. Then: "⚠ The diff contains raw memory text. If you are screen-sharing, it will show. Open the diff? (y / skim / skip)". `y` → `git diff HEAD~1..HEAD`, 50 lines at a time. `skim` → the first 5 lines of each file's diff. |

If `stale_listen_marker` is true, delete `<config-root>/memory/staged/queues/listen-in-progress`. If the diff looks wrong, tell the user `git revert HEAD` rolls back the last commit; do not run it unasked.

## Step 1 — Show the overnight summary

Show the **Overnight summary** block from `references/morning-formats.md`: what was ingested, proposals by kind, the `Checked overnight` counts, sources status, the `To review` counts, the `Needs a nudge` line, and "Ready to go through them? (y/n/skim)".

- `Checked overnight` comes from the draft's `## Verification` section; with none, print `Checked overnight: not run`.
- `To review` comes from `python3 scripts/cortex_cli.py triage-draft --config-root <config-root> --draft <date>` (read-only). Step 2 uses the same grouping.
- Omit the `Needs a nudge` line when `open-nudges` returned none.
- `y` (default) → Step 2. `n` → exit, leaving the draft. `skim` → one line per proposal with no per-proposal gates; the user picks numbers to open. In skim mode `accept-all` and `accept-all-high` apply only to the `batch` group and must be typed by the user; `review` proposals are still decided one at a time.

## Step 2 — Review the proposals

Sorted by risk, per the autonomy policy's tiers (`references/autonomy-policy.md`): the `brief` group first (2a), then `review` one at a time (2b), then `batch` once as a list (2c).

Use the grouping from `triage-draft`; do not re-sort it. A proposal is in `batch` only if the draft records `Verification: pass` and `Conflicts: none`. Everything else not from the brief is in `review`, including every proposal in an unchecked draft.

**If the user's autonomy policy has no medium-risk tier** (a 1.0.0-shape policy with `Ask first`, or `policy_version: "1.0.0-kept"`), there is no batch: walk the `batch` group one at a time after the `review` group, and say once that `/start-nucleus` can change that.

### 2a — From yesterday's brief

Proposals tagged `from: listen-step-1.5`, headed **"From yesterday's brief."**

- **Explicit marks** (done, delegate, skip, not_important, reprioritized, annotations) are already the user's decision. Show the list, one line each, and offer one bulk accept: "N items from yesterday's brief, as you marked them. Accept all? (y / walk individually)".
- **Inferred closures** ("likely done", no explicit mark) are a guess. Walk them one at a time with the 2b choices.

A mark applies to memory as one batch (medium risk). Any part of a brief proposal that changes something outside memory, such as completing a HubSpot task, is high risk: preview it and get approval for it on its own, immediately before doing it. Accepting the batch does not approve it.

### 2b — Needs your decision (one at a time)

Walk the `review` group. Order: verification `fail`, then `unverifiable`, then conflicts, then `not-run` or not checked; within each, by priority (Critical / High / Medium / Low).

Open with one line saying what is here and why: "4 need your decision: 2 the overnight check could not support, 1 conflicts with an existing entry, 1 was not checked."

Show each with the **Proposal** block from `references/morning-formats.md`: node and type, confidence, source, the `Check` line, conflicts, the current entry, the proposed content, and `(a)ccept / (r)eject / (e)dit / (d)efer / (s)kip-remaining`.

`Check` is the draft's `Verification` result (`references/verification.md`), shown as recorded; with none, show `Check: not run`. For a `fail` or `unverifiable` proposal, say why in one plain sentence before the choices ("The transcript says Friday, not Wednesday."). The check is evidence, not a decision: every proposal gets the same choices, and nothing is accepted or rejected for the user because of it. Do not show raw archive content unless the user asks for a proposal's source.

**accept** — apply the proposal by its `Type`, then append `[YYYY-MM-DD] /morning merge: <one-line summary> — proposed by <agent>` to the node's `## Changelog`. Do not copy the five verification fields into the node.

- **Knowledge entry** → append to the matching `## Knowledge` subsection (Insights / Models / Gotchas / Lessons / Recipes / Corrections) with `[confirmed:today] [recalled:today] [by:<actor-id>]`, actor ID from the active identity.
- **Person-update** → append to `## Recent interactions` or `## Notes` on the person page; create the page if needed.
- **Commitment** → append to `## Open threads` (the user owes it) or `## Waiting on` (someone owes the user).
- **Thread-update** → change the named open thread (status, note, or close).
- **Decision** → write a decision record with `python3 scripts/cortex_cli.py record-decision ... --recorded-by /morning` (`references/decision-schema.md`): the proposal's content for what and why, its cited source as an input, the user's Actor ID as `--decided-by`. Append the returned `pointer_line` to the affected node's `## Knowledge` section. First show what will be recorded and confirm it is what was decided. Never batch a decision.

Check every knowledge-entry accept for a conflict with an existing entry. If there is one: "This contradicts the existing entry '<...>'. Supersede the old / Keep both / Skip the new?" Default: keep both. Never supersede silently.

**reject** — append `<today> proposal:<type>@<node> "<signal>" — rejected from /listen draft <date>` to `<config-root>/memory/staged/skip-logs/research.md`.

**edit** — show the proposed content as editable text; apply the edited version on confirmation.

**defer** — leave the proposal in the draft.

**skip-remaining** — stop; the remaining proposals stay in the draft for the next session.

### 2c — Verified overnight (one review for the batch)

Show the `batch` group once, as a numbered list:

Use the **Verified batch** block from `references/morning-formats.md`: one line per proposal (node, type, one-line summary) with its evidence line beneath (source, locator, quote), then "Accept all <B>? (y / drop <numbers> / open <number> / one-by-one / later)".

- `y` → apply every listed proposal exactly as `accept` does, then report how many were written and to which nodes.
- `drop 2 5` → remove those and ask what to do with each (reject or defer); apply the rest.
- `open 3` → show proposal 3 in full with the 2b choices, then return to the list.
- `one-by-one` → walk the whole group individually. `later` → leave the group in the draft.

Rules for the batch:

- Always show the list first. A previous morning's "y" never covers today's.
- Every item shows its evidence line. An item with no recorded evidence moves to 2b.
- If the write-time conflict check finds a conflict the draft did not list, take that item out of the batch and handle it one at a time. Continue with the rest.
- A proposal that would touch anything outside memory is not medium risk: move it to 2b.

## Step 2.9 — Record how the overnight check did

Append one line of counts (no proposal text, no names) so the verifier's accuracy can be judged over time:

```
python3 scripts/cortex_cli.py append-line --memory-root <config-root>/memory staged/verifier-outcomes.md "<today> by=<actor-id> draft=<date> pass:accepted=<n> pass:edited=<n> pass:rejected=<n> fail:rejected=<n> fail:accepted=<n> unverifiable:accepted=<n> unverifiable:rejected=<n> notrun=<n> deferred=<n>"
```

Count each proposal once, by its recorded verification and what the user did. Skip if nothing was reviewed. Report a failed write in Step 5; it does not undo the merges.

## Step 2.95 — Needs a nudge

Items growth's daily `/nudges` check staged: a quiet deal, an email with no reply, a follow-up the user owes. Skip silently if `open-nudges` returned nothing.

Use the list from `open-nudges`; do not decide yourself which items are open. Read each item's block, including its draft, from the day file it names under `<config-root>/memory/staged/nudges/`. Show them one at a time, longest quiet first within each trigger, at most 10; say how many remain for tomorrow. Use the **Nudge** block from `references/morning-formats.md`, with the choices `(u)se it / (e)dit / s(n)ooze / (d)ismiss / (l)ater`.

- **use** → show the draft ready to copy and send. This command does not send. If the user asks you to send it, that is high risk: show the exact message and recipient and get approval for that one message immediately before sending. Record `acted`.
- **edit** → apply the user's changes, show the result, then treat it as `use`.
- **snooze** → ask until when; default is the trigger's threshold from today (15 days for a quiet deal). Record `snoozed` with `until`.
- **dismiss** → say "I won't flag this one again," then record `dismissed`.
- **later** → record nothing; it returns tomorrow.

Record each decision as one ledger line, copying the item's `Key` exactly:

```
python3 scripts/cortex_cli.py append-line --memory-root <config-root>/memory staged/nudges/ledger.jsonl '{"ts": "<ISO-8601 now>", "key": "<Key>", "event": "acted | snoozed | dismissed", "until": "<YYYY-MM-DD, snooze only>", "by": "<actor-id>"}'
```

**Never change a deal.** Do not propose closing a deal or changing its stage because it is quiet. If the user says the deal is dead, `dismiss` the nudge; any CRM change they then ask for is a separate high-risk action. A nudge is not a memory proposal: nothing here is merged into a node.

Afterwards run `open-nudges` again and move each `archivable` file with `cortex_cli.py move-node --memory-root <config-root>/memory staged/nudges/<date>.md staged/nudges/archive/<date>.md`.

## Step 3 — Finalize the draft

- All proposals accepted, rejected, or archived → move the draft to `staged/commit-drafts/archive/<date>-merged.md`.
- Any deferred → leave the draft in place with the handled proposals struck out (`~~...~~`), so the next `/morning` picks up where this one stopped.

## Step 4 — Refresh, log, reflect, commit

1. **Refresh**, always: `python3 scripts/cortex_cli.py reindex --memory-root <config-root>/memory`, then `python3 scripts/cortex_cli.py refresh-hot --memory-root <config-root>/memory --trigger morning`.
2. **Log**: invoke the `log-writer` skill with `op_name: morning` and `summary: merged <a> / <total> proposals from <draft-date> draft. <r> rejected, <d> deferred. hot.md + memory/index.md refreshed.`
3. **Reflect and seed today's brief** (skip if `briefing` is not installed):
   - If `<config-root>/briefs/<yesterday_local>.md` has a `## Reflection` section that `/listen` wrote from the brief, show it and ask "edit it, or keep it as-is?" Keep → go to priorities. Edit → ask the three questions pre-filled.
   - Otherwise ask, one at a time, pre-filled from the merged draft where it helps: **"Biggest thing that got done yesterday?"**, **"What blocked you, if anything?"** (optional), **"What's the one thing today has to move?"** Accept "nothing major".
   - Write the answers to `<config-root>/briefs/<today_local>.md` as a `## Reflection` section (the **Reflection** block in `references/morning-formats.md`), replacing one already there for today.
   - Propose **today's priority tasks and outreach**, each `(k)eep / (e)dit / (d)rop`, with one batch shortcut when items plainly carry over. Candidates: the "one thing" answer, surviving P0/P1 next actions, and growth's tier for today plus deferred contacts. Never propose an item suppressed in `surfacing-prefs.md`. Write the accepted set to `<config-root>/briefs/<today_local>.seed.json` as `{priorities:[...], outreach:[...]}`.
   - Ask once: **"Anything else for today?"** Append any answer to the seed file.
4. **Friday rehearsal**: on a Friday, if `<config-root>/memory/staged/queues/rehearse.md` has candidates, run `/rehearse --batch 5` and report `Rehearsal: <N> entries reviewed`.
5. **Commit memory**: skip if `<config-root>/memory/.git/` does not exist. Otherwise acquire the write lock (`scripts/cortex_cli.py lock-acquire`), `git add . && git commit` any dirty state, release the lock. Push only if `cortex.user-context.md` has `memory_as_git.remote` set and `memory_as_git.push_on_close: true`: `git push <memory_as_git.remote_name, default "origin"> main`. On failure, log it and continue. Report `Memory: committed · pushed to <remote_name>` or `Memory: committed (local-only)`.

## Step 5 — Report and offer the brief

Show the **Closing report** block from `references/morning-formats.md` (counts, refreshes, reflection, plus the rehearsal and memory lines when they apply), ending "Run /brief to start the day with today's working surface? (y/N)".

`y` → invoke `/brief` for today. `n` → exit.

## What this command does not do

- Invoke `/listen` or `/nudges`; the draft and the nudges must already exist.
- Accept the verified batch without showing it and getting a yes, or batch a proposal that failed, could not be verified, was not checked, or conflicts with an existing fact.
- Send a nudge's draft without approval for that message, or change a deal.
- Modify `archive/`, call WebSearch or WebFetch, or run `/brief` without the user's yes.
