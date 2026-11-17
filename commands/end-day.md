---
description: Optional end-of-day close. `/listen` and `/morning` already cover overnight mining and the next brief; run this for a deeper same-day pass. Mines today's brief and CRM activity, shows what it learned and what it would forget for your review before anything is saved, captures a reflection, proposes tomorrow's priorities, offers to log to HubSpot, and pre-stages tomorrow's brief. Quick by default; `--full` adds inbox, transcript and conversation mining.
disable-model-invocation: true
---

# /end-day

Optional. `/listen` (nightly) and `/morning` (the required daily touch) already mine the day and seed the next brief. Run `/end-day` for a same-day close: the brief and CRM activity mined now, a reflection in the longitudinal `reflections.md`, a HubSpot catch-all log, and with `--full` the day's inbox, transcripts and other sessions. It never starts from natural language; the user types `/end-day`.

Formats, tables and step-by-step procedures are in `references/end-day-formats.md`. Read it before Step 0.7. This file is the order of operations and the rules; where the two differ, this file wins.

## Rules that hold in every step

- **Nothing mined reaches memory unreviewed.** Every proposed memory write, from any source and in both modes, goes through the Step 2b review first.
- **CRM writes need approval for each item**, immediately before the write. Approving one item approves only that item. No mode setting removes this.
- `references/autonomy-policy.md` wins over this file. A command mode of `auto` removes the source card prompt only; it lowers no risk tier.
- A step whose plugin or connector is missing is skipped without comment. Never invent counts, brief actions or sources.
- If no one answers a gate, take the default in **Timeouts** and move on. The chain never blocks.

## Before the chain

1. **Config-root guard.** Run `python3 scripts/cortex_cli.py root-status`. If it exits non-zero, stop and show its sentence verbatim; write nothing and do not ask for folder access more than once per session. Exception: in a remote session with the sync repos attached, run `bootstrap` (`references/core-contract.md` §11B) once and re-check.
2. **Resolve.** If no config root resolves, run `python3 scripts/cortex_cli.py bootstrap --print-env` and use the printed root; on a synced checkout run `cortex_cli.py sync` once (pull) before reading. Resolve `<config-root>` per `references/core-contract.md` §1. Read `<config-root>/memory/me/identity.md` for the time zone. Set `today_local` and `tomorrow_local` (next business day: Friday, Saturday and Sunday → Monday).
3. **One-time migrations**, each skipped when its marker exists and neither able to block the close:
   - `<config-root>/memory/.scope-migration-done` missing → run **Scope migration** in the reference. `/end-day --rerun-scope-migration` deletes the marker and runs it again.
   - `<config-root>/memory/.migration-staged-reorg-done` missing → invoke `/migrate-staged-substrates`. On failure, log it and continue.

## Modes and run order

| Mode | Steps, in this order |
|---|---|
| **Quick** (default) | 0.7 → 2c → 2a (CRM activity only) → 2.9 → 2b → 3 → 4 → 4.5 to 4.7 → 5 → 5.5 to 5.8 → 6 |
| **Full** (`--full`) | 0.7 → 2c → 1 → 2 → 2a → 2.9 → 2b → 3 → 4 → 4.5 to 4.7 → 5 → 5.5 to 5.8 → 6 |

The brief (Step 2c) is always mined first. The review (Step 2b) comes after every miner has finished.

**Auto-offer.** In quick mode, count today's transcripts in the configured note sources and today's unread inbox threads addressed to the user. If transcripts ≥ 2 or threads ≥ 5, ask once: "Heads up: you have <N> transcripts and <M> inbox threads from today. Want the full close? (default: no)". Yes → restart in full mode. Below both thresholds, do not ask.

## Step 0.7 — Source card

Before reading any source, show **one card** listing every source to be reviewed, each with a checkbox and an approximate cost, and a running total (shape and cost model: **Source card** in the reference). Never gate sources one prompt at a time.

| Source | Mode | Notes |
|---|---|---|
| Today's Brief responses | both | Required and first. Never a checkbox. |
| CRM activity (HubSpot) | both | On by default. Keep it on unless the user unchecks it. |
| Transcripts | full | |
| Email | full | |
| Slack | full | Off by default. |

- Defaults come from `end_day.sources:` in `<config-root>/plugins/cortex.user-context.md` when set.
- Quick mode with no CRM connected leaves only the brief: skip the card and go to Step 2c.
- Command mode `auto`: skip the card and review the default-on set.
- Anything unchecked is skipped and named in the Step 6 summary ("Reviewed: brief, CRM. Skipped: email, Slack.").

## Step 2c — Mine the brief (always)

1. **Already processed?** If `<config-root>/briefs/<today_local>.state.processed` exists, skip items 3 to 5 with the note "already processed today" and go to item 6.
2. **Read the state** through the chain in **Reading the brief state**: the state-mirror file `briefs/<today_local>.state.json`, then widget context, then asking the user to paste the sync blob, then the one multi-select fallback question. Stop at the first that yields state. Do not skip silently; skip only when the state is unreadable and no task list exists on disk, and say so.
3. **Work out the write-backs** from the tables in **Brief write-backs**: task actions (done, delegate, skip, not important), reprioritizations, unhandled annotations, outreach actions, and suppression learning into `surfacing-prefs.md`. Skip anything `/process-brief` already acted on today.
4. **Show them once and ask.** These are marks the user already made, so one review covers the batch: list each mark and the memory write it causes, and ask "Apply these? (y / remove items / n)". Write only what is accepted. Suppressions and repeat-ignore proposals are not in this batch; they go to Forgettings in Step 2b.
5. **CRM effects are separate.** A mark that would change HubSpot (completing a linked task, creating a delegate task, a prep task for a booked call, a stage move) is previewed and approved one item at a time. Then write `briefs/<today_local>.state.processed` with the current ISO timestamp.
6. **Feed forward.** Done items → Step 4 "biggest thing done" candidates. Surviving unsuppressed P0/P1 tasks → Step 4.5. Learnings inferred from annotations → the proposal set for Step 2b. They are never committed directly.

## Step 1 — Inbox triage (full mode)

Find threads that will need a reply tomorrow. If a `/triage-inbox` command is available, invoke it; otherwise search Gmail for today's messages addressed to the user with no reply, capped at 7. Hold the result for Step 5. Then ask: "Tomorrow's inbox triage shows <N> threads. Review them now, or wait for the morning brief?" Default: wait.

## Step 2 — Transcripts (full mode)

Read `<config-root>/plugins/cortex.note-sources.md` and keep enabled sources whose scope is global or matches a project with meetings today. None configured → say "No note sources configured. Run `/setup-sources` to enable transcript mining." and continue.

Invoke `note-taker` with `mode: "transcript"` (inputs: **Miner inputs and merge**). It returns `commitments_delta` and `learnings_delta`.

- **Commitments**: for each one ask "Convert this to a CRM task / cortex P0 / both / skip?" A CRM task is created only on that item's explicit yes, due tomorrow unless the user gives a date. A cortex P0 goes on the project node's `## Next Actions`. An empty delta gets one confirming line.
- **Learnings**: hold them for Step 2b.

## Step 2a — Other sources

- **Quick mode**: if CRM is checked, invoke `note-taker` with `mode: "activity"`.
- **Full mode**: invoke `note-taker` twice in parallel in one message, `mode: "conversation"` (excluding the current session) and `mode: "activity"`, for whichever sources are checked.

Merge every `learnings_delta` and the brief learnings from Step 2c using the dedup and sort rules in the reference (transcript wins over the other modes; drop anything already in the node; group by target node).

## Step 2.9 — Say what today was about

Before any accept or reject decision, give two or three plain sentences on what today was about, drawn from the brief actions, whatever was mined, and the reflection candidates. Then lay out two columns:

- **Memories**: proposed adds and updates, each with type, confidence, target node and source citation.
- **Forgettings**: stale facts to demote or archive, items to suppress (not-important marks and repeat-ignore proposals from Step 2c), and superseded beliefs, each with the reason.

## Step 2b — Review (both modes)

Walk both columns with the gate in **Review gate**: accept all, select per node, edit each, high-confidence only, or skip all. Quick mode uses the same gate; with few items show them as one compact list. With nothing to review, say so in one line.

- A proposal that would create a new node gets its own confirmation first, with a Scope interview.
- High-confidence-only defers the rest; they may come back tomorrow.
- Skipped items go to `<config-root>/memory/dismissed-proposals.log` so they do not resurface for 7 days.
- Forgettings never delete: a fact is demoted to `## Demoted knowledge` or archived, with the date and reason.

Accepted items, with any edits, pass to Step 3.

## Step 3 — Commit

Run `/remember` in silent mode with two inputs: the current session, and the items accepted in Step 2b. Accepted items are already routed and skip `/remember`'s triage; the triage runs on the session content only and is mandatory there. User corrections always commit to the `user` node. New entries carry `[confirmed:<today>] [recalled:<today>]`; a re-affirmed entry gets a new `confirmed` date only.

Report one line: "Memory updated: <N> nodes touched, <M> knowledge entries, <K> person-page updates, <P> reviewed proposals applied." If triage said nothing was worth saving and nothing was accepted: "Quiet day. Nothing material to commit."

**Step 3.7, person pages.** If `<config-root>/memory/.person-mention-counts.json` has a name with 3 or more mentions across 2 or more nodes and no person page, offer to graduate it (y / not yet / never), at most 3 offers per run. Procedure: **Person-page graduation**.

## Step 4 — Reflection

Ask one at a time, pre-filled from the brief state as suggestions (rules: **Reflection**). If the brief artifact already holds a reflection, show it and confirm it instead.

1. "Biggest thing that got done today?"
2. "What blocked you, if anything?" (optional)
3. "What's the one thing tomorrow has to move?"

"Nothing major today" is a valid answer. Paraphrase sensitive client detail from annotations; never quote it.

Write the answers, or `—` placeholders when skipped, to:
- `<config-root>/briefs/<today_local>.md` under `## Reflection`, replacing a section already there for today (create the file with a minimal header if it is missing);
- the top of `<config-root>/memory/me/reflections.md` as one dated block, replacing today's block on a re-run and never rewriting earlier ones. Create it from `references/reflections-template.md` if missing.

The third answer also becomes a `[P0]` next action on the relevant project node, dated tomorrow.

## Steps 4.5 to 4.7 — Tomorrow and HubSpot

**4.5 Priorities and outreach.** Propose tomorrow's priority tasks and outreach one at a time, `(k)eep / (e)dit / (d)rop`, with one batch shortcut when items plainly carry over. Candidates: surviving P0/P1 tasks, the "one thing" answer, accepted P0s, snoozes ending tomorrow, and growth's tier for tomorrow plus deferred contacts. Never propose an item suppressed in `surfacing-prefs.md`. Write the kept set to `<config-root>/briefs/<tomorrow_local>.seed.json` as `{priorities:[...], outreach:[...]}`. Nothing to propose → say so.

**4.6 Anything else.** Ask once: "Any other priorities or outreach for tomorrow?" Append the answer to the seed file.

**4.7 HubSpot.** If HubSpot is not connected, skip this step without a prompt. Otherwise ask once: "Anything to log in HubSpot before we close?" On "no" or silence, write nothing. Otherwise turn each item into a concrete write (note, task, stage or property change, new record), show them in one table, and get approval for each row before writing it (**HubSpot logging**). For records that map to a cortex node, add a one-line interaction entry. Keep the counts for Step 6.

## Step 5 — Pre-stage tomorrow's brief

Skip this step if `briefing` is not installed; Steps 5.5 to 6 still run.

Invoke `/brief` with `target_date: tomorrow_local`. It reads the seed file from Step 4.5. In full mode pass the Step 1 inbox results. It must update the existing `todays-brief` artifact rather than create a new one, in the same format `/brief` produces; where artifact tools are unavailable it writes the markdown snapshot and says the surface is degraded (**Pre-staging tomorrow's brief**). Then ask: "Tomorrow's brief is staged. Review it now, or wait until morning?" Default: wait.

## Steps 5.5 to 5.8 — Close-out (always run)

Each of these runs whether or not `briefing` is installed. A failure is logged and the chain continues.

- **5.5 Index**: `python3 scripts/cortex_cli.py reindex --memory-root <config-root>/memory`
- **5.6 Hot cache**: `python3 scripts/cortex_cli.py refresh-hot --memory-root <config-root>/memory --trigger end-day` (skip if `hot_cache.enabled: false`).
- **5.7 Chronicle**: invoke the `log-writer` skill with `op_name: end-day` and a summary of the mode and the real counts for what ran.
- **5.8 Memory commit**: only if `<config-root>/memory/.git/` exists (the reference covers the one-time offer to initialize it). Run `python3 scripts/cortex_cli.py lock-acquire --memory-root <config-root>/memory --timeout 10 --stale-after 600`.
  - **Exit 1 (lock held by another command)**: say "Memory write-lock held by another process. Skipping the memory commit; it will be picked up by the next `/morning` or `/end-day`." Skip the commit and continue to Step 6. Never delete or override the lock file; a stale lock is reclaimed automatically. There is no override.
  - **Exit 0**: follow **Memory commit** in the reference (gitignore check, staged-changes check, commit, verify), then run `python3 scripts/cortex_cli.py lock-release --memory-root <config-root>/memory` on every exit path. Push only when `memory_as_git.remote` is set and `memory_as_git.push_on_close: true`.

## Step 6 — Close

On a synced checkout (`<config-root>/.private` exists) run `python3 scripts/cortex_cli.py sync --root <config-root>` as the last write and report its result, including any `conflict/<host>/<ts>` branch.

Then one short summary: commitments converted, memory entries, person pages touched, HubSpot writes if any, which sources were reviewed and which were skipped, and whether tomorrow's brief is staged. Report only what ran. If ops is installed, log one telemetry line (`skill: end-day, mode, steps_run, commits_count, runtime_ms`).

## Timeouts

When a gate gets no answer (scheduled run, or the user walked away):

| Gate | Default |
|---|---|
| Full-close offer | no, after about 5s |
| Step 0.7 source card | the default-on set |
| Step 2c brief write-backs | apply nothing; leave the brief for `/listen` to mine |
| Step 1 inbox review | wait |
| Step 2 commitments | skip each; never create a CRM task unconfirmed |
| Step 2b review | skip all, after about 30s; skipped items go to the dismissal log |
| Steps 3.7, 4, 4.5, 4.6 | skip |
| Step 4.7 HubSpot | no; never write to the CRM unconfirmed |
| Step 5 brief review | wait |

## What this command is not for

- Mid-day check-ins: use `/recall` or `/search`.
- Long retrospectives: use `/end-week` or briefing's `/review`, which also cover the day.
- Saving one conversation: that is `/remember`.
- Blocking tomorrow's calendar: that is `/plan-tomorrow`.
