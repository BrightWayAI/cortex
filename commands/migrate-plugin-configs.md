---
description: One-time migration. Archives legacy files in `<config-root>/plugins/` (retired config files whose replacement exists, backup copies, the old-location `ops.schedules.md`) and creates `plugins/ops/schedules.md`. Dry-run first; nothing is deleted or overwritten. Gated by the `memory/.migration-plugin-configs-done` marker.
---

# /migrate-plugin-configs

Moves leftover files in `<config-root>/plugins/` into `plugins/archive/` and makes sure
the schedule definitions file exists where ops reads it. All file operations run in
`scripts/cortex_cli.py migrate-plugin-configs`; do not move files by hand.

## Step 0 — Resolve config root

Resolve `<config-root>` with the shared precedence chain. If `<config-root>/plugins/`
does not exist, say so and stop.

## Step 1 — Find the schedule starter (optional)

If the ops plugin is installed, locate its `references/schedules.template.md` and pass
it as `--schedules-template`. If ops is not installed, omit the flag; the migration then
only creates `plugins/ops/schedules.md` when an old `ops.schedules.md` can be carried
over.

## Step 2 — Dry run

```bash
python3 scripts/cortex_cli.py migrate-plugin-configs \
  --config-root "<config-root>" \
  --schedules-template "<ops-plugin-root>/references/schedules.template.md"
```

The output is a JSON plan listing file names only. Show it to the user as a table:
action, from, to, reason. If the status is `already-done`, report that and stop.

What the plan can contain:

| Action | When |
|---|---|
| `create ops/schedules.md` from `ops.schedules.md` | the old file holds a schedule table and no definitions file exists |
| `create ops/schedules.md` from the starter | no usable old file, and a template was supplied |
| `move … → archive/` | `ops.schedules.md` after it is carried or superseded; a retired config file whose replacement exists (`client-status.user-context.md` once `clients-status.user-context.md` exists); any `*.bak-<date>` backup |
| `skip` | a retired file is still the only copy, or no template was supplied |

Files that current commands still read are never touched, including
`plan-tomorrow.user-context.md`.

## Step 3 — Confirm and apply

Ask once: "Apply these moves?" On yes, rerun the same command with `--apply`. On
success it writes the marker. On any error it stops, writes no marker, and is safe to
run again.

## Step 4 — Report

List what moved and what was created. If `ops/schedules.md` was created, tell the user
to review it and run `/register-schedules` when ready. This command never registers,
changes or removes a scheduled task.

## Rerun

`--rerun` ignores the marker. Archive targets that already exist are never overwritten;
a numeric suffix is added instead.
