---
description: Scaffold an Obsidian vault config over `<config-root>/` so the second brain becomes a graph-viewable, mobile-readable knowledge base. Writes `.obsidian/` workspace config, a `VAULT.md` home page, and configures daily-notes to use the `briefs/` folder. Idempotent and non-destructive — never clobbers existing `.obsidian/` content. Optional opt-in feature; users who don't want Obsidian don't need to run this.
---

# /setup-obsidian

You are configuring `<config-root>/` as an Obsidian vault. After this runs, the user can:

1. Open Obsidian → File → Open vault → select `<config-root>/`.
2. See the graph view of all cortex memory nodes (person, client, topic, domain — connected by `[[wikilinks]]`).
3. Open today's brief from briefing as today's Obsidian daily note.
4. Use `VAULT.md` as the home page with Dataview-powered active-entity tables.
5. Sync the same vault to a phone via iCloud / Obsidian Sync.

This command is **idempotent and non-destructive.** Existing `.obsidian/` files are not overwritten. Existing `VAULT.md` is not overwritten. Re-run safe.

---

## Step 0 — Resolve config root

Standard pattern:
- Resolve `<config-root>` through the canonical precedence chain in
  `references/core-contract.md` §1.
- Cowork: `mcp__cowork__request_cowork_directory(path=<config-root>)`. Claude Code: direct.

If `<config-root>` doesn't exist, say so and ask the user to run `/setup-identity` first. Stop.

---

## Step 1 — Read identity for personalization

Read `<config-root>/memory/me/identity.md` and extract:
- `name` (for the VAULT.md title and template substitution)
- `time_zone` (for resolving "today")

If `identity.md` doesn't exist, fall back to "Nucleus vault" as the title and the system's local date as today.

---

## Step 2 — Print the plan and confirm (autonomy-aware in v4.7.2+)

**Consult autonomy mode** per `references/autonomy-policy.md` (Per-command confirmation modes). Default for `/setup-obsidian`: `confirm`.

- **Mode = `auto`**: skip the confirmation prompt; proceed straight to Step 3 after a single-line "Scaffolding Obsidian vault at `<config-root>/` (preserving existing files)." Use when the user has already decided.
- **Mode = `suggest` / `confirm`** (default): use the standard plan-and-confirm prompt below.

Default prompt (suggest / confirm modes):

```
I'll scaffold an Obsidian vault config at <config-root>/:

  WRITE:
    .obsidian/app.json
    .obsidian/core-plugins.json
    .obsidian/daily-notes.json
    VAULT.md  (home page for the vault)

  PRESERVE:
    Any existing .obsidian/ files (community-plugins.json, workspace.json, plugins/).
    Any existing VAULT.md (no overwrite).

After this completes:
1. Install Obsidian (https://obsidian.md) if you haven't.
2. Open Obsidian → File → Open vault → select <config-root>/.
3. Install Dataview from Settings → Community plugins (so VAULT.md tables render).
4. Mobile: install Obsidian on phone, sync via iCloud or Obsidian Sync.

Proceed?
```

Wait for user confirmation (unless autonomy mode = `auto`). On no, abort.

---

## Step 3 — Write `.obsidian/` config

Create `<config-root>/.obsidian/` if it doesn't exist.

For each of `app.json`, `core-plugins.json`, `daily-notes.json`:
- If the file does NOT exist, copy the template from `references/obsidian-config-templates/<filename>` to `<config-root>/.obsidian/<filename>`.
- If the file EXISTS, leave it alone and report: "Preserved existing `.obsidian/<filename>`."

Do NOT touch `community-plugins.json`, `workspace.json`, or `plugins/` — those are Obsidian's per-vault user state and may contain the user's existing customizations.

---

## Step 4 — Write `VAULT.md`

If `<config-root>/VAULT.md` does NOT exist:
- Read `references/obsidian-config-templates/vault-template.md`.
- Substitute placeholders: `{{user_name}}` ← from identity (default "Your"), `{{today}}` ← today's date in YYYY-MM-DD per identity time zone.
- Write to `<config-root>/VAULT.md`.

If it exists, leave it alone and report: "Preserved existing VAULT.md."

---

## Step 5 — Verify briefing integration (informational only)

Check whether `<config-root>/briefs/` exists. If it does, confirm:
> "Daily-brief snapshots at `<config-root>/briefs/YYYY-MM-DD.md` will appear as Obsidian daily notes (the daily-notes plugin is configured to use this folder)."

If it doesn't exist (briefing not installed or not yet run), note:
> "Heads up: briefing is not yet generating `<config-root>/briefs/`. Once you install the `briefing` plugin and run `/brief`, today's brief will automatically become today's daily note in Obsidian. No additional config needed."

This step writes nothing — just informs the user.

---

## Step 6 — Verify memory index integration (informational only)

Check whether `<config-root>/memory/index.md` exists. If it does, confirm:
> "Memory index found. Open `<config-root>/memory/index.md` in Obsidian for a graph-friendly catalog of every memory node."

If not, note:
> "Memory index doesn't exist yet. Run `/reindex` to generate it, or wait for the next `/end-day` — it auto-regenerates as part of the closing chain."

---

## Step 7 — Report

```
Obsidian vault configured.

Files written: <list of files actually written>
Files preserved: <list of files left alone>

Next steps:
1. Open Obsidian → File → Open vault → select <config-root>/
2. (Optional) Install Dataview from Settings → Community plugins so VAULT.md tables render
3. (Optional) Install Calendar, Tasks, Periodic Notes for richer UX
4. (Optional) Mobile: install Obsidian on phone, set up iCloud or Obsidian Sync
```

---

## Idempotent re-runs

Running `/setup-obsidian` a second time after the user has used Obsidian and customized it:
- Preserves all existing `.obsidian/` files (user's window layout, installed community plugins, etc.).
- Preserves `VAULT.md` (the user may have customized it).
- Writes only files that don't yet exist (covers the case where the user deleted one by accident).
- Reports the diff between what was written and what was preserved.

If the user wants to FORCE-overwrite everything (e.g., reset to defaults), they pass `/setup-obsidian --reset`. The command then asks for explicit confirmation per file before overwriting.

---

## What this command does NOT do

- Does not install Obsidian itself. The user installs from obsidian.md.
- Does not install community plugins. Obsidian's plugin API doesn't permit external installs; the user clicks through Settings.
- Does not modify briefing, daily-notes, or any other plugin's output. Pure config-only scaffolding.
- Does not sync to mobile. The user chooses iCloud / Obsidian Sync / etc. on their own.
- Does not create memory/index.md (that's the indexer's job).
- Does not touch existing user content in `<config-root>/` outside of writing `.obsidian/` config files and a fresh VAULT.md.
