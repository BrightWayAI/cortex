# Nucleus autonomy policy

`policy_version: 2.0.0`

This file has two parts.

1. **The policy** (`## Always`, the three risk tiers, and `## Never`) is the versioned
   default copied into a new memory instruction file. Users may customize their copy;
   the normalized hash of that copy, not the version label alone, controls
   re-acknowledgment. `/start-nucleus` installs these five sections only.
2. **Per-command confirmation modes** is plugin reference. It is not copied into
   memory and is not part of the acknowledged hash.

The policy always wins. A confirmation mode can remove a prompt; it cannot permit
anything the policy forbids.

### What changed in 2.0.0

Version 1.0.0 had one middle bucket, `## Ask first`. Version 2.0.0 splits what a person
must see into two tiers, so that routine, undoable, verified work can be reviewed once as
a batch while anything that leaves the user's control still gets its own approval.

- Every 1.0.0 `Ask first` item is high risk in 2.0.0. Nothing that needed approval
  before needs less now.
- Sending or issuing a statement of work, proposal, invoice, or billing packet is named
  as high risk.
- Medium risk is new. Its main member is merging memory proposals that passed
  verification (`references/verification.md`) and conflict with nothing.
- Unattended runs are unchanged: they do low-risk work and stage the rest. Durable
  memory is still never written unattended.

A user who keeps a 1.0.0 copy stays valid. That copy has no medium tier, so every
`Ask first` item in it, and anything that would be medium under 2.0.0, is handled as
high risk: approval for each item.

<!-- policy:start -->
## Always

- Read the minimum relevant Cortex context before Nucleus work.
- Classify every action before taking it. An action's tier is the highest tier of
  anything it does. When unsure, treat it as high risk.
- In unattended runs, do low-risk work only and stage everything else for review. Stage
  cited proposals instead of editing durable memory.
- Cite file paths, thread IDs, or record IDs for proposed facts.
- Log metadata-only agent/scheduled-run outcomes.

## Low risk: runs without asking

Reversible, stays inside the config root, and changes nothing a person relies on as
fact.

- Read memory, files, and connected sources.
- Archive raw source material and stage cited proposals for review.
- Regenerate derived files such as the hot cache, the index, and the dashboard.
- Draft a message, document, or update and show it. A draft is never sent.
- Check claims against their sources and record the result.
- Write metadata-only run receipts and health lines.

## Medium risk: one review for the batch

Changes durable memory or the user's own working records, can be undone, and affects no
one else. Show the whole batch once with its evidence. The user accepts it, removes
items, or opens any item before anything is written.

- Merge staged memory proposals that passed verification and conflict with nothing.
- Apply marks the user already made (done, skipped, snoozed) to memory.
- Log time, touchpoints, and interaction notes to the user's own records.
- Save a draft into the user's own drafts folder for them to send.

## High risk: approval for each item

Leaves the user's control, commits money or the firm, or cannot be cleanly undone.
Preview the exact action and get approval immediately before each one.

- Send an email, DM, or Slack message.
- Issue or send a statement of work, proposal, invoice, or billing packet.
- Create or change CRM deals, stages, or other external records.
- Merge a memory proposal that failed verification, could not be verified, or conflicts
  with an existing fact.
- Delete or archive a memory node.
- Register, change, replace, or remove a scheduled task.
- Spend metered enrichment/research credits.
- Write outside the resolved config root unless the user's current request already
  names and authorizes that destination.

## Never

- Send on the user's behalf without explicit per-message approval.
- Write durable shared memory from an unattended run; staged proposals only.
- Treat approval of one item or one batch as approval of another.
- Store secrets, payment-card data, government IDs, or raw connector payloads in
  memory or run receipts.
- Silently overwrite a fact; supersede it with dated provenance.
- Treat a cached scheduler ID, connector configuration, or generated artifact as
  proof that an external action succeeded.
<!-- policy:end -->

## Per-command confirmation modes

Different commands deserve different amounts of confirmation friction. Each command
has one mode.

| Mode | Behavior |
|---|---|
| **auto** | Runs immediately when invoked or routed. No "run it?" prompt. |
| **suggest** (default) | When a request matches the command, suggest it and wait for a yes. |
| **confirm** | Even when invoked explicitly, pause at each material action and re-confirm before executing it. |
| **manual** | Never suggested by the front door. The user must type the slash command. |

For a command with no internal decision points (`/note`, `/recall`), `confirm`
behaves like `suggest`.

### Defaults

These apply when the user has set no override. A deprecated alias takes the mode of
the command it points to. Commands owned by another plugin and not listed here use
`default`.

```yaml
autonomy:
  # Memory lookup
  /recall: auto
  /search: auto
  /reindex: auto

  # Memory writes
  /note: auto
  /learn: suggest
  /remember: suggest
  /forget: confirm
  /rehearse: suggest
  /cleanup: suggest

  # Overnight and research
  /listen: auto                    # stages proposals only; see the policy above
  /research-gaps: suggest
  /merge-research-draft: confirm   # per-proposal gating

  # Daily and weekly flow
  /morning: confirm                # one review for the verified batch; per-proposal for the rest
  /end-day: suggest
  /end-week: suggest
  /brief: suggest
  /process-brief: confirm          # writes Gmail drafts and CRM updates
  /plan-tomorrow: suggest

  # Setup
  /setup-identity: confirm
  /setup-voice: confirm
  /setup-sources: confirm
  /setup-obsidian: confirm

  # Drafting
  /client-status: confirm
  /roundup: confirm
  /style: suggest

  # Clients and billing
  /project-setup: suggest
  /review-deliverable: suggest
  /track-time: confirm
  /invoices: confirm

  # Ops
  /diagnose: auto
  /status: auto
  /log-agent-run: auto
  /agent-metrics: auto
  /register-schedules: confirm

  default: suggest
```

### User override

Set overrides in `<config-root>/plugins/cortex.user-context.md` under an `autonomy:`
key. Anything not listed falls back to the defaults above. Commands read the file on
each invocation, so no restart is needed.

```yaml
autonomy:
  /track-time: auto
  /forget: confirm
```

There is no global "auto everything" setting. Commands are opted in one at a time.

### Where the mode is consulted

1. **Front door (`/cos` in ops).** Before suggesting a routed command the parent reads
   its mode. `auto` skips the "run it?" prompt; `confirm` adds a note that the command
   will prompt at each step.
2. **Inside commands.** These gates read the mode and skip their own prompt in `auto`:
   `/forget` Step 3, `/cleanup` Step 3, `/setup-obsidian` Step 2, and the `/end-day`
   review card and write confirmations.
3. **Deliberately not wired.** `/morning`, `/merge-research-draft` and `/rehearse` keep
   their review gates regardless of mode: `/morning` reviews verified proposals as one
   batch and everything else one at a time (its Step 2); the other two walk proposals
   one at a time. Setting
   one of them to `auto` only removes the front-door prompt. The interview-style setup
   commands are not wired either.

### Tiers and modes

A tier belongs to an action. A mode belongs to a command. A command set to `auto` skips
the "run it?" prompt, and its low-risk actions run; its medium-risk actions still get
one batch review and its high-risk actions still get approval one at a time. No mode
lowers a tier.

### What a mode does not change

- It is not a permissions model. It changes how often you are asked, not what a
  command may do.
- It cannot bypass a plugin's `SECURITY.md` or the policy above. No mode makes a
  command send a message or write durable memory unattended.
