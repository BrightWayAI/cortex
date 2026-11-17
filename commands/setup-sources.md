---
description: Configure the list of note sources cortex's mining layer uses. Walks an interview covering which notetakers / providers the user uses (Granola, Gemini, Fireflies, Otter, Notion, generic Drive folders, generic Gmail labels, custom) and writes the configured list to `<config-root>/plugins/cortex.note-sources.md`. Run on first cortex setup or anytime you adopt a new notetaker. Each source's adapter runs a health-check during setup so misconfigurations fail loudly here, not silently at `/end-day` time.
---

# /setup-sources

Sets up the note-source list that powers the v4.3 mining layer. Without at least one source, `note-taker` (mode: transcript) has nothing to mine.

This is a standalone command. It does not replace any other setup. It can be re-run anytime to add a new source, disable a source, or change provider config.

---

## Step 0 — Resolve plugin config root

Resolve `<config-root>` through the canonical precedence chain in
`references/core-contract.md` §1. Request access only to the resolved root in
Cowork. If it is inaccessible, stop with: "No accessible Cortex config root.
Run `/setup-identity` first."

Sources config file lives at `<config-root>/plugins/cortex.note-sources.md`.

---

## Step 1 — Read existing config (if any)

If `<config-root>/plugins/cortex.note-sources.md` exists, parse the current source list. Surface it:

> "You have N sources currently configured: [list with id, provider, enabled status, scope]. Update specific entries, add new ones, or start over?"

- **Update specific** → ask which IDs; jump to per-source interview for each.
- **Add new** → continue to Step 2 with current list preserved.
- **Start over** → continue to Step 2 with empty starting list (the existing file is preserved as a backup at `cortex.note-sources.<today>.bak`).

If the file does not exist, continue to Step 2 with empty list.

---

## Step 2 — Provider menu

Show the supported provider list with one-line descriptions:

```
Which notetakers / sources do you use? Pick all that apply:

  [ ] granola         — Granola desktop app (native MCP)
  [ ] gemini          — Google Meet's Gemini notes (Drive doc or Gmail summary)
  [ ] fireflies       — Fireflies meeting recorder (if MCP connected)
  [ ] otter           — Otter.ai (native MCP or Drive folder sync)
  [ ] notion          — Notion meeting-notes database
  [ ] drive-folder    — Generic: any Drive folder where meeting notes land
  [ ] gmail-label     — Generic: any Gmail thread tagged with a label
  [ ] custom          — Anything else; free-form description
```

User picks one or more. For each picked, walk a per-provider interview (Step 3).

---

## Step 3 — Per-provider interview

For each provider the user picks, ask its config questions. Use the adapter reference at `references/note-source-adapters.md` to know what to ask. Summary:

### granola

- ID for this source entry (default: `granola`)
- Label (default: `"Granola (default notetaker)"`)
- Scope (default: `global` — or pick a specific project node if Granola is project-scoped)

No additional config needed.

### gemini

- ID for this source entry
- Label
- Scope
- Method: **drive-folder** (Gemini writes the notes doc into a Drive folder) OR **gmail-search** (Gemini emails a meeting summary) OR **both** (configure two separate sources, e.g., `gemini-meet-drive` and `gemini-meet-email` — cross-source dedup will merge the same meeting captured by both)
- If `drive-folder`:
  - `folder_id` (offer to call Drive MCP `search_files` to help pick if available)
  - `filename_pattern` (default: `"Notes by Gemini"`)
- If `gmail-search`:
  - `query` (default: `"from:meet-noreply@google.com OR subject:'Notes by Gemini'"`)

### fireflies

- ID, label, scope
- No additional config (assumes Fireflies MCP is connected and the default workspace is correct)

### otter

- ID, label, scope
- Method: **native MCP** (if Otter MCP exists) OR **drive-folder** (Otter syncs recordings to a Drive folder — fall back to the drive-folder adapter with an Otter-specific filename pattern)

### notion

- ID, label, scope
- `database_id` for the Notion DB holding meeting notes
- `title_property` (default: `"Meeting"`)
- `date_property` (default: `"Date"`)
- `attendees_property` (optional)

### drive-folder

- ID, label, scope
- `folder_id`
- `filename_pattern` (default: `"*"`)
- `title_extraction`: `filename` (default) | `doc-title` | `first-line`
- `datetime_extraction`: `file-created` | `file-modified` (default) | `parse-from-body`

### gmail-label

- ID, label, scope
- `label` (the Gmail label name)
- `sender_filter` (optional)

### custom

- ID, label, scope
- `description` (free-form prose: where the notes live, how to fetch, how to map fields)
- `tools` (list of MCP tool names the adapter should use)

---

## Step 4 — Health-check each source

For each newly configured source (and any updated existing source), call the adapter's `health_check()` from `references/note-source-adapters.md`.

For each result:

- **Pass** (≥ 1 historical match in last 14 or 90 days, depending on adapter) → mark `enabled: true`, surface "✓ <source-id> healthy"
- **Fail** (connector missing, folder invalid, query syntax error, etc.) → surface the error verbatim. Ask user:
  > "<source-id> health-check failed: <error>. Options: (f)ix config now, (d)isable for now and keep config, (r)emove this source"

Loud failure at setup is the point — better than silent failure at `/end-day` time.

---

## Step 5 — Confirm and write

Show the assembled source list:

```
Final note-sources configuration:

  granola              global       enabled   ✓ healthy
  gemini-meet-drive    global       enabled   ✓ healthy
  gemini-meet-email    global       enabled   ✓ healthy  (will dedupe vs gemini-meet-drive)
  acme-fireflies    project:acme  enabled   ✓ healthy

Save to <config-root>/plugins/cortex.note-sources.md? (y/n)
```

On `y`, write the file. Format (markdown with fenced YAML blocks for parseability — stays consistent with the marketplace user-context convention):

```markdown
# cortex note-sources

_Configured by /setup-sources. Edit by re-running the command or by editing
this file directly (then re-run `/setup-sources --health-check-only` to verify)._

_Last updated: 2026-05-12_

## Sources

```yaml
- id: granola
  provider: granola
  label: "Granola (default notetaker)"
  enabled: true
  scope: global
  config: {}

- id: gemini-meet-drive
  provider: gemini
  label: "Gemini meeting notes (Drive)"
  enabled: true
  scope: global
  config:
    method: drive-folder
    folder_id: "<id>"
    filename_pattern: "Notes by Gemini"

- id: gemini-meet-email
  provider: gemini
  label: "Gemini meeting summaries (Gmail)"
  enabled: true
  scope: global
  config:
    method: gmail-search
    query: "from:meet-noreply@google.com OR subject:'Notes by Gemini'"

- id: acme-fireflies
  provider: fireflies
  label: "Fireflies for Acme calls only"
  enabled: true
  scope: project:acme
  config: {}
```
```

(One fenced YAML block. The block is the canonical source list — easy to read, easy to edit by hand, and any markdown reader renders it nicely.)

---

## Step 6 — Offer next step

> "Source list saved. The mining layer will use these on the next `/end-day` run. To test now without waiting, run `note-taker` directly with `mode: \"transcript\"` and a 1-day window — it'll exercise each source's adapter and report what it found."

---

## Per-project source overrides

For now, project-scoped sources (e.g., `scope: project:acme`) are configured through this command. A future cortex version (or the `project-setup` plugin) may add an inline "Does this engagement use a different notetaker than your defaults?" question during `/project-setup` — that will write a `scope: project:<new-node-id>` entry to this same file. For v4.3, run `/setup-sources` directly to add per-project sources.

---

## Re-running

- `/setup-sources` — full interview, current config surfaced first
- `/setup-sources --health-check-only` — re-run health-checks on the existing config without changing anything; useful after a connector reinstall
- `/setup-sources --remove <source-id>` — remove a single source entry (with confirmation)

---

## Behavior rules

- Idempotent. Re-running with the same input produces the same config file.
- Never silently overwrite. If a source ID would collide with an existing one, prompt the user to rename or replace.
- Health-checks are mandatory on new + updated entries. Skipping them defeats the loud-failure design.
- Never write to the sources file if any newly-required source's health-check fails AND the user chose `(r)emove` for it — drop it from the final list rather than save in a broken state.
- The sources file lives in `<config-root>/plugins/` per the marketplace convention, not in the cortex plugin's source folder.
