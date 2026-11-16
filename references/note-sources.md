# Note sources — config and how to add a provider (v4.3+)

How cortex's mining layer (`note-taker`, mode: transcript) knows where to look for meeting notes.

## Config file

`<config-root>/plugins/cortex.note-sources.md`

Markdown wrapper with a fenced YAML block holding the source list. Hand-editable; `/setup-sources` walks an interview to populate or update it.

Example:

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
    folder_id: "<gdrive folder>"
    filename_pattern: "Notes by Gemini"

- id: gemini-meet-email
  provider: gemini
  label: "Gemini meeting summaries (Gmail)"
  enabled: true
  scope: global
  config:
    method: gmail-search
    query: "from:meet-noreply@google.com OR subject:'Notes by Gemini'"

- id: riptoes-fireflies
  provider: fireflies
  label: "Fireflies for Riptoes calls only"
  enabled: true
  scope: project:riptoes
  config: {}
```

## Per-entry fields

| Field | Required | Description |
|---|---|---|
| `id` | yes | Unique within the file. Lowercase, hyphenated. |
| `provider` | yes | One of: `granola`, `gemini`, `fireflies`, `otter`, `notion`, `drive-folder`, `gmail-label`, `custom`. Maps to an adapter section in `references/note-source-adapters.md`. |
| `label` | yes | Human-readable. Shown in `/end-day` status output. |
| `enabled` | yes | `true` to use; `false` to opt out without deleting. |
| `scope` | yes | `global` (every run) or `project:<node-id>` (only when the run involves that project node). |
| `config` | yes | Provider-specific dict. Each adapter section documents what its `config` expects. Can be `{}` if the adapter needs no config. |

## Per-project source scope

`scope: project:<node-id>` lets a source apply only to runs involving a specific project node. A run is "for a project" if the time window contains at least one event (meeting, sent email, calendar event) whose attendees or title match that project node.

Multiple project-scoped sources can fire in the same run if multiple projects had activity. Global sources always fire.

## How `note-taker` (mode: transcript) uses the file

At the top of every run:

1. Read `<config-root>/plugins/cortex.note-sources.md`
2. Filter to `enabled: true` sources
3. Filter to `scope: global` ∪ `scope: project:<node>` where `<node>` matches a project in the run's `node_inventory` with activity in the window
4. For each filtered source, load its adapter from `references/note-source-adapters.md`
5. Call the adapter's `fetch(time_window)` to get normalized notes
6. Dedupe across sources (same meeting captured by Granola AND Gemini → keep richest, link the other as `cross_source_ref`)
7. Proceed with commitments + learnings extraction

If a source's connector is missing or fails health-check during the run, log a one-line warning and continue with the remaining sources.

## Adding a new provider

Two cases:

### Case 1 — Provider has a first-party MCP

Add a new section to `references/note-source-adapters.md` following the existing pattern. Document:

- Config schema (what `config:` fields the adapter needs)
- Tools used (which MCP tool names)
- `fetch(time_window)` logic (how to query the MCP, filter to window, map response fields to the normalized note shape)
- `health_check()` logic (a small smoke test against the connector)

No agent code changes needed — `note-taker` reads the adapter file fresh on each run.

### Case 2 — Provider has no MCP but writes to Drive or Gmail

Don't add a new provider — reuse the generic `drive-folder` or `gmail-label` adapter with a configured filename pattern, folder ID, label, or query that filters to that provider's output.

## Health-check during setup

When `/setup-sources` adds or updates a source, it calls the adapter's `health_check()` immediately. Failures surface with the verbatim error and an option to fix, disable, or remove. This is the loud-failure-at-setup design choice — better than discovering at `/end-day` time that a folder ID is wrong.

## Privacy / opt-out

- `enabled: false` keeps the config but excludes the source from mining
- Threads / notes containing `[CONFIDENTIAL]`, `[PRIVATE]`, or user-configured exclusion patterns are skipped at extraction time, not at fetch time (so the source's overall health-check still works even if specific notes are excluded)
- The `custom` provider with a free-form description lets a user wire any source without exposing its config publicly — useful for sources with sensitive auth or local-only access

## When to re-run `/setup-sources`

- Adopting a new notetaker
- Disabling a noisy source temporarily (set `enabled: false` instead of deleting)
- Adding a per-project scope (e.g., switching to Fireflies for one client)
- After a connector reinstall — run `/setup-sources --health-check-only` to verify all existing sources still work
