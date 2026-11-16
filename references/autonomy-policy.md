# Nucleus autonomy policy

`policy_version: 1.0.0`

This file has two parts.

1. **The policy** (`## Always`, `## Ask first`, `## Never`) is the versioned default
   copied into a new memory instruction file. Users may customize their copy; the
   normalized hash of that copy, not the version label alone, controls
   re-acknowledgment. `/start-nucleus` installs these three sections only.
2. **Per-command confirmation modes** is plugin reference. It is not copied into
   memory and is not part of the acknowledged hash.

The policy always wins. A confirmation mode can remove a prompt; it cannot permit
anything the policy forbids.

<!-- policy:start -->
## Always

- Read the minimum relevant Cortex context before Nucleus work.
- In unattended runs, stage cited proposals instead of editing durable memory.
- Cite file paths, thread IDs, or record IDs for proposed facts.
- Log metadata-only agent/scheduled-run outcomes.

## Ask first

- Send an email, DM, or Slack message.
- Create or change CRM deals, stages, or other external records.
- Delete or archive a memory node.
- Register, change, replace, or remove a scheduled task.
- Spend metered enrichment/research credits.
- Write outside the resolved config root unless the user's current request already
  names and authorizes that destination.

## Never

- Send on the user's behalf without explicit per-message approval.
- Write durable shared memory from an unattended run; staged proposals only.
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
  /morning: confirm                # per-proposal gating
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
3. **Deliberately not wired.** `/morning`, `/merge-research-draft` and `/rehearse` walk
   proposals one at a time and keep every per-item gate regardless of mode. Setting
   one of them to `auto` only removes the front-door prompt. The interview-style setup
   commands are not wired either.

### What a mode does not change

- It is not a permissions model. It changes how often you are asked, not what a
  command may do.
- It cannot bypass a plugin's `SECURITY.md` or the policy above. No mode makes a
  command send a message or write durable memory unattended.
