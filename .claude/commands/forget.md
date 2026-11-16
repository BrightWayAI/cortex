---
description: Archive or remove a project node from working memory. Use when a project is complete, abandoned, or no longer relevant. Supports full removal, archival (compress to a single summary), or merging two nodes together.
---

# /forget $ARGUMENTS

You are modifying the project memory graph. This is a destructive operation — confirm with the user before proceeding.

---

## Step 1 — Validate the node

Search Claude's memory for the specified node. If it doesn't exist, tell the user and list the nodes that do exist.

If it exists, show the user what will be affected:
```
## Forgetting: [node-id]

**Living Summary**: [the current summary]
**Changelog entries**: [count] entries spanning [earliest date] to [latest date]
**People entries**: [count] people indexed under this node
**Signals**: [count] cross-project signals involving this node
```

---

## Step 2 — Determine the operation

### Default: Archive (safe)
Compress all memory for this node into a single archival entry, then remove the individual entries:
```
[node-id] ARCHIVED (YYYY-MM-DD): [1-2 sentence summary of what this project was and how it concluded]. Key decisions: [top 3]. Key people: [names]. [count] sessions logged from [start] to [end].
```

This preserves searchability while freeing memory space.

### With `--merge [target]`: Merge into another node
Move all relevant context from the source node into the target node:
- Append a LOG entry to the target noting the merge
- Transfer any people entries
- Transfer any open threads or next actions
- Delete the source node's entries
- Update the target's living summary to reflect the merged context

### Full removal (only if user explicitly says "delete" or "remove completely")
Remove all memory entries for this node. This is irreversible.

---

## Step 3 — Confirm (autonomy-aware in v4.7.2+)

**Consult autonomy mode** per `references/autonomy-policy.md` (Per-command confirmation modes): read `<config-root>/plugins/cortex.user-context.md` `autonomy:` section; fall back to defaults (default for `/forget`: `confirm`).

- **Mode = `auto`**: skip the confirmation prompt entirely. Show what will happen as an inline statement ("Archiving [node-id]: removing [...] / writing [...]") and proceed to Step 4. The user opted into this; don't second-guess.
- **Mode = `suggest`**: standard confirmation prompt as below, single yes/no gate.
- **Mode = `confirm`** (default for `/forget`): stricter — show each material side effect as a separate yes/no gate. Defer to standard prompt if there's only one effect (e.g., a simple archive).

Default prompt (suggest / confirm modes):

```
I'll [archive/merge/delete] the [node-id] node. This will:
- [action 1]
- [action 2]
- [action 3]

Proceed? (yes/no)
```

Wait for confirmation before modifying memory (unless autonomy mode = `auto`).

---

## Step 4 — Execute and report

### File Operations

Memory is stored at `<config-root>/memory/` (resolve per `references/core-contract.md` §1).

**Before modifying**: Check if `<config-root>/memory/` is accessible.
- **Cowork**: Use `mcp__cowork__request_cowork_directory(path=<config-root>)` to request access. Wait for the user to approve.
- **Claude Code**: The directory is accessible directly via the filesystem.

If the directory cannot be accessed, explain that memory cannot be modified without this folder and stop.

All operations below go through `scripts/cortex_cli.py`, which acquires the shared lock, performs the change, and releases it in one call (see `references/core-contract.md` §11) — do not hand-edit or hand-delete node files for this step.

- **Archive** (default): move the node file into `memory/archive/`:
  ```
  python3 scripts/cortex_cli.py move-node --memory-root <config-root>/memory \
    "<node-relative-path>" "archive/<filename>"
  ```
  Then remove the node's entry from DASHBOARD.md Active Nodes and add a one-line entry to the Dormant or a new "Archived" section, using `replace-section`/`append-section` as in `/remember` Step 3.
- **Merge**: read both node files first (to build the merged content), then:
  ```
  python3 scripts/cortex_cli.py append-section --memory-root <config-root>/memory \
    "<target-relative-path>" "## Changelog" "<merge note + transferred entries>"

  python3 scripts/cortex_cli.py delete-node --memory-root <config-root>/memory \
    "<source-relative-path>"
  ```
  Update the target's living summary via `replace-section` and update DASHBOARD.md.
- **Delete**:
  ```
  python3 scripts/cortex_cli.py delete-node --memory-root <config-root>/memory \
    "<node-relative-path>"
  ```
  Remove the node's entry from DASHBOARD.md.

After execution, confirm what was done:
- For archive: "Archived [node-id]. It's searchable but won't appear in dashboards."
- For merge: "Merged [source] into [target]. Updated [target]'s summary."
- For delete: "Removed all [count] entries for [node-id]."

---

## Step 5 — Clean up cross-references

After archiving/deleting, scan for:
- SIGNAL entries in other nodes that reference this node — update them to note the node is archived/deleted
- PEOPLE entries in other nodes that mention this node — update the "Also in:" list
- Any WAITING actions in other nodes that depend on this node — flag them for the user

---

## Behavior notes

- Default to archive, not delete. Data loss should require extra intent.
- If the node has open P0 or P1 actions, warn the user before proceeding
- If the node has cross-project signals to active nodes, flag this
- Never archive/delete `personal` without strong explicit confirmation
