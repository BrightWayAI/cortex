---
description: Nightly autonomous ingest. Pulls yesterday's calendar / Gmail / Slack / transcripts / Drive activity into immutable `<config-root>/archive/YYYY-MM-DD/`, mines yesterday's Today's Brief state (explicit marks + an unmarked-item inference pass) into closures/snoozes/reflection, runs the note-taker mining agent (modes: transcript, conversation, activity) against the archive, and stages all proposed memory commits as a single draft at `<config-root>/memory/staged/commit-drafts/YYYY-MM-DD.md`. Refreshes `<config-root>/memory/hot.md`. Designed for unattended scheduled execution. Pair with `/morning` to review and merge the draft.
---

# /listen

The overnight ingest. **Unattended by design**: no user gates, no prompts. It runs to completion or fails loudly. Its output is one draft the user reviews in `/morning`. `/listen` never modifies active memory nodes.

## Step G — Config-root guard (run first)

Run `python3 scripts/cortex_cli.py root-status`. If it exits non-zero, **stop** and show its sentence verbatim; write nothing anywhere else and do not ask for folder access more than once per session. Exception: in a remote session with the sync repos attached, run the documented `bootstrap` (`references/core-contract.md` §11B) once and re-check before stopping.

## Step 0 — Root, start-up, target date

**Cloud-first.** If no config root resolves, or it is the cloud default, run `python3 scripts/cortex_cli.py bootstrap --print-env` (with `--adopt-org`/`--adopt-private` when the routine's repo checkouts are present) and use the printed root. No computer needs to be attached.

**Start-up.** Run `python3 scripts/cortex_cli.py listen-start --config-root <config-root>`. It probes that the root is readable and writable, ensures `<config-root>/.gitignore` protects `archive/` and `memory/staged/`, writes the in-progress marker `/morning` checks, and takes the memory write lock. Act on its exit code:

| Exit | `status` | Do |
|---|---|---|
| 0 | `ok` | Keep the `token` it returns; Step 8 needs it. Continue. If `cloud_sync` names a provider, log once: "`<config-root>` is inside <provider>. `.gitignore` does not prevent cloud sync; see `references/gitignore-template.md`." |
| 3 | `unreachable` | **Hard failure.** Write the failure receipt (below), send the failure notification, exit non-zero, do not report success. Nothing was started, so do not run Step 8. |
| 4 | `already-running` | Another `/listen` is running. Print a one-line `NOOP` summary and exit 0. Do not run Step 8: the marker and lock belong to the other run. Only a person, interactively, may re-run with `--force`. |
| 5 | `busy` | Another command held the memory lock through two retries. Log "Memory busy — try /listen again later" to `memory/log.md` and exit 0. Do not run Step 8. |

**Failure receipt for an unreachable root.** This is the case where a task fires somewhere that cannot reach the config root; a silent skip is the failure this gate exists to catch.

```
python3 scripts/cortex_cli.py write-receipt --config-root <config-root> --schedule nightly-listen --run-id <run_id> --started-at <iso> --ended-at <iso> --outcome failed --error-code config_root_unreachable --actor-id <the actor named in the registered prompt>
```

With the root unreachable the command prints the receipt to stdout and exits 2; that output is the receipt. The identity file cannot be read here, so the actor comes from the registered prompt; with none, the receipt says `actor_id: "unresolved"`. Never guess an actor.

This gate is only for the whole root. One connector failing is logged under `## Errors` in `_index.md` and the run continues.

**Target date.**

- No argument → yesterday in the identity time zone.
- `--date YYYY-MM-DD` → that date.
- `--backfill N` → once per day for the last N days with no archive; each day gets its own draft.
- `--remine YYYY-MM-DD` → skip Step 1; re-run mining against the existing archive into `staged/commit-drafts/<date>-remine-<seq>.md`, leaving the original.

If `<config-root>/archive/<target_date>/` already exists and the mode is not `--rewrite` or `--remine`, log "Archive for <date> already exists; skipping pull. Use --remine to re-run mining or --rewrite to force re-pull.", go to Step 8 with a `NOOP` health line, and exit 0. **Never silently overwrite an archive.**

## Step 1 — Pull yesterday's sources (skipped in `--remine`)

For each source enabled in `<config-root>/plugins/cortex.user-context.md` and `/setup-sources`, write to `<config-root>/archive/<target_date>/` in the formats in `references/archive-layout.md`:

- **Calendar** → `calendar.md`. Events starting on `target_date` in the user's time zone. Skip blocked time and personal events.
- **Gmail** → `inbox.md`. `after:<target_date> before:<target_date+1> (to:me OR cc:me)` where the user is not the latest sender. Cap 50 threads. Metadata plus a 200-character snippet; full body only if `listen.inbox.full_body: true`.
- **Slack** (optional) → `slack.md`, grouped by channel. Messages from `target_date` that mention the user or that the user wrote. Cap 100.
- **Drive** (optional) → `drive.md`. Files created or modified on `target_date` in watched folders. Metadata only.
- **Transcripts** → `transcripts/<meeting-id>-<slug>.md`, one per meeting, with front-matter (source adapter, original ID, title, participants, date) and the transcript. One query per configured adapter, per `references/note-source-adapters.md`.

Skip an adapter `/setup-sources` marked unhealthy and note it. Log each failed source under `## Errors` in `_index.md` and continue with what was pulled.

## Step 1.5 — Mine yesterday's brief

Runs in normal and `--remine` modes, and even when the brief state for `target_date` is missing (the inference pass still runs against the archive).

**Read `references/listen-brief-mining.md` and follow it in full.** It covers: reading and archiving the brief state (hosted artifact or local file), turning the user's explicit marks into proposals, inferring "likely done" items from the archive, writing `closures.json`, the reflection carry-forward, the snooze ledger and growth sync, and idempotency. The direct writes it lists are the only ones this command makes outside the archive and the draft. It never prompts.

If that file cannot be read, do not improvise the procedure: record `brief mining: skipped (reference unreadable)` under `## Errors` in `_index.md`, set the receipt's outcome to `partial` with error code `brief_mining_skipped`, and continue.

## Step 1.6 — Write the run receipt

Once Step 1.5 has written its closures, ledger, and reflection, write one metadata-only receipt (schema 1.1.0). Do not hand-write the JSON:

```
python3 scripts/cortex_cli.py write-receipt --config-root <config-root> \
  --schedule nightly-listen --run-id <host run id or UUID> \
  --started-at <ISO-8601> --ended-at <ISO-8601> --outcome succeeded \
  --actor-id <the actor named in the registered prompt, if any> \
  --extra '{"state_source": "state.json | artifact-db | none", "counts": {"closed": 0, "carried": 0, "snoozed": 0, "suppressed": 0, "reflection_written": false}}'
```

`counts` is what Step 1.5 actually produced. If the brief state was absent and the artifact preflight found nothing, set `state_source: "none"` and zero counts, so a run that had no brief to mine says so. `actor_id` is read from the identity file; `--actor-id` is used only if that file cannot be read, and with neither the receipt says `unresolved`.

## Step 2 — Write the archive index

Write `archive/<target_date>/_index.md`, the record of what this run did:

```markdown
# Archive index — <target_date>

Generated by /listen at <ISO timestamp>.

## Counts
- Calendar events: <N>
- Inbox threads: <N>
- Slack mentions: <N>
- Drive changes: <N>
- Transcripts: <N>
- Brief state: read | absent | processed-skip
- Brief proposals staged: <N> (<M> closures, <K> snoozed, <inference-count> inferred)

## Sources pulled
- <source or adapter>: ok (<N>) | skipped | error

## Errors
- (none) or list with retry hints
```

If the date had no source data at all, still write a minimal `_index.md` saying so, stage no draft, log "no activity to mine", and go to Step 5.

## Step 3 — Mine the archive

Invoke `note-taker` once per mode. Every mode is read-only against the archive and against active memory; they propose and never write nodes.

| `mode` | Scope | Cross-reference | Proposes |
|---|---|---|---|
| `transcript` | `archive/<target_date>/transcripts/` | active person pages; open threads on project and client nodes | knowledge entries, commitments to and from others, person-page updates |
| `conversation` | Cowork session metadata for `target_date` (session-info MCP, if available) | active project nodes | knowledge entries, user-observation updates |
| `activity` | `calendar.md`, `inbox.md`, `slack.md`, `drive.md` | active person, client, and topic nodes | person-page entries, open-thread updates, commitments |

Combine the three proposal lists.

## Step 4 — Stage the commit draft

Write every proposal to `<config-root>/memory/staged/commit-drafts/<target_date>.md`:

```markdown
# Commit draft — <target_date>

Generated by /listen at <ISO timestamp>.
Total proposals: <N> across <M> nodes.

## Summary
- <P> proposed knowledge entries
- <Q> proposed person-page updates
- <R> proposed commitments
- <S> proposed thread updates / closures

## Proposals

### Proposal 1 — <node>: <one-line summary>
- **Type:** INSIGHT | MODEL | GOTCHA | LESSON | RECIPE | CORRECTION | DECISION | person-update | thread-update | commitment
- **From:** note-taker (mode: transcript) | note-taker (mode: conversation) | note-taker (mode: activity)
- **Source:** archive/<target_date>/<file> (line <N> or section <X>)
- **Proposed content:**
  > <verbatim or near-verbatim text to add>
- **Target placement:** `<node-path>` · section `<section-name>`
- **Confidence:** high | medium | low
- **Conflicts:** <existing entries this might supersede or contradict; or "none">
```

Sort by priority (Critical / High / Medium / Low) within type, grouped by source agent. Step 4.5 adds five verification fields under each proposal and a `## Verification` section; do not write those here.

A `DECISION` proposal is something the source shows was decided. `/listen` never writes a decision record; `/morning` does, after the user confirms it (`references/decision-schema.md`). Put what was decided and the stated reason in Proposed content, and set `Conflicts: decision — review individually` so it is never batched.

The draft is not active memory.

## Step 4.5 — Verify the proposals

Every proposal is checked against the source it cites before the user sees it. The rules are in `references/verification.md`; this step applies them. It adds evidence to the draft. It does not remove, rewrite, reorder, or merge any proposal, and a `pass` writes nothing to active memory.

1. **Script pass.** Run:
   ```
   python3 scripts/cortex_cli.py check-citations --config-root <config-root> --draft <target_date>
   ```
   It reports `fail`, `pass-verbatim`, or `needs-verifier` per proposal. A `fail` here is final.

2. **Verifier pass.** Invoke the `verifier` agent once (in batches of 40 if there are more) with:
   - the config root;
   - one claim per proposal that did not `fail` in step 1: `id` = the proposal number, `claim` = its Proposed content, `sources` = its Source field, `target` = its Target placement;
   - the JSON from step 1.

   Pass nothing else. Do not include the note-taker's output, your own view of the proposal, or the Confidence field: the verifier must judge the claim and the source alone.

   **Skip** proposals tagged `from: listen-step-1.5` that are explicit marks (Step 1.5c). Those are the user's own clicks, not mined claims. They are recorded as `not-run`.

3. **Record.** Save the verifier's JSON to a temporary file outside `<config-root>` and run:
   ```
   python3 scripts/cortex_cli.py record-verification --config-root <config-root> --draft <target_date> --verifier-results <file>
   ```
   This writes five fields under each proposal (`Citation check`, `Verification`, `Verifier confidence`, `Evidence`, `Verification reasons`) and a `## Verification` count section above `## Proposals`. Do not write these fields by hand. The script applies the merge rules, so report its output, not the verifier's raw verdicts: a script `fail` stays `fail` whatever the verifier said; a proposal with no valid verifier result is `not-run`; and a `pass` at `low` confidence, or a `pass` with no evidence, is recorded as `unverifiable`.

4. **If the verifier cannot run or returns something unusable,** run `record-verification` without `--verifier-results`. Every checkable proposal is then recorded as `not-run`. Never record `pass` for a claim that was not checked, and never fail the `/listen` run because verification failed: the draft is still staged and the user reviews it as before. Note `verification: not-run (<reason>)` in `_index.md` under Errors.

5. **Do not repair.** If a proposal fails, leave it in the draft as failed. Do not ask note-taker to re-mine it, and do not edit its content so that it passes.

Carry the four counts (pass / fail / unverifiable / not-run) into the Step 8 health line and summary line.

## Step 5 — Refresh, log, retain

1. `python3 scripts/cortex_cli.py refresh-hot --memory-root <config-root>/memory --trigger listen`.
2. If `ops` is installed, log one line via `/log-agent-run`: `skill: listen, date: <target_date>, archive_size_bytes: <N>, proposals_count: <M>, runtime_ms: <T>`.
3. Invoke the `log-writer` skill with `op_name: listen` and `summary: archived <target_date> (<events> events, <inbox> inbox, <mentions> mentions, <transcripts> transcripts, <errors> errors). <P> proposals staged.` If the write fails, continue.
4. **Weekly, when `target_date` is a Sunday:** compress `archive/YYYY-MM-DD/` directories older than 30 days into `archive/YYYY-MM.tar.gz`. Never delete a tarball; retention beyond that needs the user.

## Step 8 — Publish, release, exit

Runs on every path out of this command **once `listen-start` returned `ok`**, whether the later steps succeeded or failed, like a `finally`. A run that never started (exit 3, 4, or 5 above) skips it:

1. Append one line to `<config-root>/memory/staged/listen-health.md`: `<iso8601> OK <date>: <N> proposals (...; verified <p> pass / <f> fail / <u> unverifiable / <n> not-run)`, or `<iso8601> FAILED <date>: <reason>`, or `<iso8601> NOOP: ...`.
2. `python3 scripts/cortex_cli.py listen-finish --config-root <config-root> --token <token from listen-start>` removes this run's in-progress marker and lock, and nothing that belongs to another run. It must run even if an earlier step failed, or the next `/listen` and `/morning` see a stale lock.
3. `python3 scripts/cortex_cli.py sync --root <config-root>`. A failed sync is a failed run: say so in the summary and exit non-zero.
4. If anything failed, send a Slack DM or push notification with the one-line reason, since a failed sync means the health line never reached GitHub.
5. Print one line: `/listen <target_date> complete: <N> proposals staged in staged/commit-drafts/<target_date>.md (verified: <p> pass, <f> fail, <u> unverifiable, <n> not run). Run /morning to review.`

Exit 0 on success; non-zero only for a hard failure (root unreachable, every source failed, sync failed).

## Behavior rules

- **No interactive prompts,** including for brief mining. Errors go to `_index.md`, the health line, and the receipt.
- **Idempotent on the archive.** Re-running a date without `--rewrite` is a no-op; `--remine` is always allowed against an existing archive.
- **Privacy-conservative.** Metadata only for inbox and Slack unless the user opted in to full bodies.
- **Never modify active memory.** Proposals stage to `staged/commit-drafts/`; the only direct writes are the record-keeping listed in `references/listen-brief-mining.md`.
- **Verification informs, it does not decide.** A `pass` merges nothing and a `fail` deletes nothing.
- It does not run web research (`/research-gaps`), render or call `/brief`, or chain into `/morning`.

## Scheduling

Register through ops `/register-schedules`; the starter library's `nightly-listen` row runs it as a cloud routine with no computer attached. The registered prompt bootstraps, walks any dates missing `archive/<date>/_index.md` (at most 3), runs `/listen` for each, and always ends with Step 8. Pair it with a local `cortex_cli.py sync` job so the copy on the computer follows.
