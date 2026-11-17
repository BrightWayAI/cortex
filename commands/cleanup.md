---
description: Run maintenance on working memory. Consolidates old log entries, detects stale threads, identifies orphaned nodes, and reports on memory health. Run periodically to keep memory sharp and within limits.
---

# /cleanup

Maintenance on working memory: audit it, show what you found, and change only what the user approves. Layouts and prompts for every finding are in `references/cleanup-formats.md`.

Three rules hold throughout:

- **Audit first.** Always show the audit report before taking any action.
- **Approval.** Nothing that removes, merges, or archives content happens without the user approving that action.
- **Archive over delete.** Default to archive over delete for any content removal.

## Step 1 — Audit current memory

Resolve `<config-root>` per `references/core-contract.md` §1. If `<config-root>/memory/` cannot be reached (request folder access for the resolved root where the host needs it), explain that memory cannot be audited without this folder and stop.

1. Read `<config-root>/memory/DASHBOARD.md`.
2. List every `.md` file under `memory/` except DASHBOARD.md and `archive/`. For each: last modified date, number of LOG entries, staleness of open threads.
3. Compare the dashboard against the files: entries with no file, files missing from the dashboard.
4. Check `memory/archive/` for archived nodes.

Compile the **Memory Health Report**: entry counts by type with a usage assessment (light, moderate, heavy, near limit), and node counts by age (Active within 7 days, Warm 8–14, Cooling 15–30, Dormant 30+, Archived).

## Step 2 — Identify maintenance opportunities

Run every check, in this order.

**A. Log consolidation.** Nodes with 10+ LOG entries; the oldest can be consolidated.

**B. Stale threads.** Open for 3+ sessions, or 14+ days without mention.

**C. Dormant nodes.** No activity in 30+ days.

**D. Orphaned people.** People entries that reference a node that is archived or missing.

**E. Expired signals.** SIGNAL entries older than 30 days that were never acted on.

**F. Duplicates.** A node with more than one SUMMARY entry; a person listed more than once.

**G. Isolated notes.** A node is isolated when no other node mentions its ID, it references no other node ID, and it was last updated more than 30 days ago (the `> Last updated:` line, else mtime). Suggest one of: **archive** (fewer than 5 entries and no open threads), **merge into `<candidate>`** (a sibling covers the same topic; pick the candidate with one low-cost classifier call against active node summaries), or **keep as standalone** (a genuine one-off). List them under `## Isolated Notes` in DASHBOARD.md too.

**H. Person pages.** For each file in `memory/person/`, using `person_threshold_cooling` (default 90), `person_threshold_dormant` (180), and `person_threshold_archive` (365) from `<config-root>/memory/.decay-config.md`:

- **Cooling** — last contact between cooling and dormant, and fewer than 2 recalls in 90 days → add a `[cooling]` badge in the dashboard's Active People table. No action proposed.
- **Dormant** — last contact between dormant and archive, and no recalls in 180+ days → propose `archive`.
- **Cold** — last contact beyond the archive threshold, and no recalls in 180+ days → propose `archive`, flagged more strongly.
- **Stale Recent interactions** — entries older than 90 days not yet in the page's `## Archive (>90 days)` section → propose `trim` (move them there).
- **Likely premature** — no Linked entities and fewer than 2 Recent interactions → offer `keep with note` or `archive`.

On `archive`: move the page to `memory/person/archive/<slug>.md` and remove its row from Active People. The recall counter entry for the slug is preserved.

**I. Dormant and cold knowledge.** For each knowledge entry in active nodes (skip `## Demoted knowledge`), compute its age from `[confirmed:...]` (the original commit date if untagged) against the effective threshold for its type and the node's `decay_profile` (`references/decay-model.md`). CORRECTIONs are excluded from this audit (immune to decay).

- **Dormant** (`threshold_dormant ≤ age < threshold_cold`): grouped by node, oldest first, at most 15 per run. Suggest `rehearse | demote | archive`.
- **Cold** (`age ≥ threshold_cold`): listed separately. Suggest `demote | archive`.

`rehearse` queues the entry in `<config-root>/memory/staged/queues/rehearse.md` for the next `/rehearse`. `demote` moves it to the node's `## Demoted knowledge` section with its tags and a demotion note. `archive` is `demote` plus a note that the user chose archive; there is no entry-level archive.

**J. Decisions due a revisit.** For each active decision with a `Revisit when` trigger (skip "n/a" or empty), ask the low-cost classifier whether the trigger appears to have fired, given the trigger text, the node's last 30 days of activity, and recent `log.md` entries; it returns `{triggered, reason}`. At most 10 per run, strongest and most recent first. For each that fired, show the decision, what triggered it, and the original reasoning, and offer:

- **(a)ccept** — flag it for revisit. For a decision record (`memory/decision/…`), do not edit the record: add `Revisit flagged <date>: <reason>` beside its pointer line on the affected node. For an older inline `DECISION` entry, set its `Status:` to `revisit-now` and add the same note.
- **(n)o-change** — log the false positive to `<config-root>/memory/staged/skip-logs/decision-revisit.md` and suppress this pair for 90 days.
- **(u)pdate-now** — chain into `/remember` with the decision pre-loaded; the user re-confirms it or supersedes it with a new decision.
- **(s)kip** — re-check next run.

**K. Structurally isolated nodes.** A node with zero outbound `[[wikilinks]]` and zero inbound ones (count `[[<slug>]]` and `[[<type>/<slug>]]` across all other nodes). Exclude `archive/`, `staged/`, and the system files (DASHBOARD.md, CLAUDE.md, index.md, hot.md, log.md, user.md). G looks for links by node ID plus age; K looks only at wikilinks. At most 10 per run. For each, offer:

- **(r)elink** — run `/relink-memory --scope <node-path>`. If it is still isolated afterwards, offer archive or keep.
- **(a)rchive** — move it to `memory/archive/<original-path>` and update the dashboard if it referenced the node.
- **(m)erge** — ask for the target, move the content into the target's matching sections, then archive the original. Do not delete it.
- **(k)eep** — record it in `<config-root>/memory/staged/skip-logs/cleanup-isolated.md` and suppress for 90 days.
- **(s)kip** — defer.

**L. Stale dashboard lines.** Each DASHBOARD.md line should carry `<!-- by:<command> @ <YYYY-MM-DD> -->`. Flag:

1. **Not refreshed by its owning command**: 7 days for `/listen`, `/morning`, `/end-day`; 30 days for `/remember`, `/note`, `/learn`; 60 days for `manual`. A line may override with `· stale-after:<days>` inside its comment.
2. **Missing provenance.**
3. **Orphaned references**: the line names a node that no longer exists (check against `memory/index.md`).

At most 15 per run, oldest first, with P0 and WAITING lines ahead of informational ones. For each:

- **(k)eep** — rewrite its provenance to `<!-- by:manual @ <today> -->`, which re-confirms it for 60 days.
- **(u)pdate-now** — if the owner is `/listen`, `/morning`, or `/end-day`, say it refreshes on the next scheduled run and ask whether to keep waiting; if it is `/remember` or `/note`, offer to run it now.
- **(d)elete** — remove the line, and log the removed text and date to `<config-root>/memory/staged/skip-logs/dashboard-prune.md` so it can be restored.
- **(s)kip** — log `(line, date, reason-code)` to the same file. `reason-code` is one of `not-stale`, `intentional-archive`, `pending-review`, `unclear`. **Free-form text is NOT accepted in this log**: a typed reason can carry personal details into a log that gets screenshotted. If the user gives a reason in words, pick the closest code, do not record their words, and say that any nuance they want kept belongs in the line itself or the node's Notes. The same four codes apply to `staged/skip-logs/sync-linked.md`.

**First run on older memory (before L and before K).** If `<config-root>/memory/staged/skip-logs/dashboard-baseline-acknowledged` does not exist, show the **L.0 baseline prompt**: `(b)aseline-stamp` appends `<!-- by:manual @ <today> -->` to every dashboard line lacking provenance and writes the marker; `(w)alk` proceeds line by line; `(s)kip` skips L this run and asks again next time. K has the same choice with marker `section-k-baseline-acknowledged`: `(b)aseline-defer` writes each isolated slug to `staged/skip-logs/sectionK-defer.md` with `resurface-after: <today + 90d>`.

**M. Cap violations.** Run `python3 scripts/cortex_cli.py check-caps --memory-root <config-root>/memory` (read-only). Put its output in the report under "Cap violations" verbatim, or "Cap violations: none" when clean. This section reports and offers no action: there is no safe automatic way to shorten a summary.

## Step 3 — Propose actions

If memory is already clean and healthy, say so and skip the action proposals.

Otherwise read the command's confirmation mode (`references/autonomy-policy.md`; default `suggest`):

- **`suggest`** — show the numbered **Recommended Actions** for findings A–F and ask "Execute all? Or select specific actions? (all / 1,3,5 / none)". Write nothing before the answer, and carry out only what was chosen.
- **`confirm`** — walk the same actions one at a time with yes / no / skip.
- **`auto`** — run without the gate only the actions that can be undone and stay inside memory: consolidate, escalate, archive, demote, re-stamp. Print each as it happens. Any action that removes content (expire, deduplicate, delete a line, merge) still asks first.

Findings G–L are then walked in order, each with the choices listed for it above. Their per-item prompts apply in every mode.

## Step 4 — Execute approved actions

Every write goes through `scripts/cortex_cli.py` (`references/core-contract.md` §11), which takes the lock and writes atomically; do not hand-edit files for these actions.

- **Consolidate** — write the archive entry with `append-section` or `replace-section`, then remove the consolidated lines with `replace-section` on `## Changelog`.
- **Escalate** — move the thread into `## Summary` as a blocker with a `[STALE]` tag (`replace-section` or `append-section`).
- **Archive** — `move-node` into `archive/`, then update DASHBOARD.md. Nothing is deleted.
- **Clean** — `replace-section` to remove or correct the orphaned entry.
- **Expire** — `replace-section` to remove the old signal entries.
- **Deduplicate** — `replace-section` to merge duplicates, keeping the most recent.

Report what was done after each action. Do nothing the user did not approve.

## Step 5 — Refresh, log, summarize

1. If Step 4 changed memory, run `python3 scripts/cortex_cli.py reindex --memory-root <config-root>/memory`. If no actions touched memory in Step 4, skip this step.
2. Invoke the `log-writer` skill with `op_name: cleanup` and `summary: <A> actions taken. Section H: <person-pages-archived>. Section I: <dormant-entries-deferred> deferred, <demoted> demoted.`
3. Show the **Cleanup Complete** summary: entries before and after, actions taken, memory health, and a suggested date for the next run (monthly for moderate use, weekly for heavy use).
