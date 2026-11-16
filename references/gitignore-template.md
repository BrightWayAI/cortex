# `.gitignore` template + cloud-sync notes for `<config-root>/`

The user's `<config-root>/` (typically `~/Documents/Claude/`) contains progressively more sensitive content as Nucleus runs:

| Path | Sensitivity | When written |
|---|---|---|
| `identity.md`, `voice.md` | Personal but synthesized | `/setup-identity`, Comms's `/setup-voice` |
| `memory/*.md` | Personal context, written by you + Claude | `/remember`, `/end-day`, mining |
| `briefs/YYYY-MM-DD.md` | Calendar / inbox / CRM metadata, your annotations | `/brief`, `/end-day` reflection |
| `plugins/*.md` | Configuration + dismissal logs | various setup commands |
| `archive/YYYY-MM-DD/` | **Raw email bodies, Slack messages, full meeting transcripts** | `/listen` (v4.7+) |
| `memory/staged/commit-drafts/` | **Proposals quoting raw archive content** | `/listen` (v4.7+) |
| `memory/staged/research-drafts/` | Web research output + source URLs | `/research-gaps` (v4.5+) |
| `memory/staged/heartbeat-drafts/` | (Proposed v4.9+) Proposals from `/sweep` heartbeat — quotes today's in-flight conversations and surfaces | `/sweep` (future) |

The `archive/` directory and `staged/commit-drafts/` are the most privacy-sensitive — they contain verbatim text from external systems that previously lived only on those systems' servers.

## Default `.gitignore` (written automatically by `/setup-identity` and `/listen`)

```gitignore
# Nucleus privacy defaults — added by cortex /setup-identity or /listen first-run.
# Do not remove unless you fully understand the privacy implications.

# Raw substrate pulled by /listen — emails, Slack, transcripts, calendar
archive/

# All in-flight memory state (v4.8.1+: unified under memory/staged/)
memory/staged/

# Legacy dotfile paths (pre-v4.8.1 — kept for transitional safety; can remove after migration)
memory/.commit-drafts/
memory/.research-drafts/
memory/.heartbeat-drafts/
memory/.reindex-queue
memory/.rehearse-queue.md
memory/.rehearse-skip-log.md
memory/.research-skip-log.md
memory/.morning-reject-log.md

# Triage log — meta-only commit decisions, but contains node names
memory/triage-log.md

# Plugin runtime state and dismissal logs
plugins/*.dismissed-log.md
plugins/*.user-context.md.bak

# Growth (relationships) plugin runtime state (v0.2.1+) — contains person names + free-form summaries
growth/events.jsonl
growth/snoozes.json
growth/inbox/
growth/today.json
growth/<YYYY-MM-DD>.json

# Local-only Obsidian state
.obsidian/workspace.json
.obsidian/workspace-mobile.json
.obsidian/graph.json
.obsidian/core-plugins-migration.json
.obsidian/cache/
```

### What this gitignore allows

- `memory/*.md` (active node files) — versioned. Lets you track how your knowledge evolves and roll back if Claude does something wrong.
- `memory/index.md`, `memory/hot.md` — auto-generated, versioned. Cheap re-derivation but useful in a diff.
- `memory/log.md` — operation history. Useful in version control.
- `briefs/YYYY-MM-DD.md` — daily working snapshots. Optional to track but lower-risk than archive/.
- `VAULT.md`, `identity.md`, `voice.md` — versioned. These are the "stable" config.

### What's blocked

- Anything raw / pulled from external systems
- Anything draft-state that hasn't been user-reviewed
- Anything internal-marker / queue-state

## Cloud-sync caveat (iCloud, Dropbox, OneDrive, Google Drive)

`.gitignore` doesn't apply to cloud-sync providers. If you sync `<config-root>/` to:

- **iCloud Drive** — no selective per-folder exclusion. Everything in the synced directory uploads to Apple's servers. Apple promises end-to-end encryption only if Advanced Data Protection is enabled on your Apple ID.
- **Dropbox** — has "Selective Sync" (Settings → Sync → Choose folders). You can exclude `archive/` and `memory/staged/` per machine.
- **OneDrive** — has "Always keep on this device" but the per-folder cloud-exclude UX varies by version.
- **Google Drive** — similar story; selective sync is per-machine, not server-side.

### Recommended pattern for cloud-sync users

Option A — keep archive local-only:

```bash
# Move archive outside the synced directory:
mkdir -p ~/.cache/nucleus/archive
ln -s ~/.cache/nucleus/archive ~/Documents/Claude/archive

# /listen writes through the symlink; the underlying data stays local.
```

Set this up *before* the first `/listen` run. cortex respects symlinks; mining agents read through them transparently.

Option B — accept the cloud copy. If your cloud provider has strong encryption and you trust them (e.g., iCloud with ADP enabled, Dropbox Business with E2E), it may be acceptable to sync `archive/`. Document this decision in your `<config-root>/PRIVACY-NOTES.md` for future you.

Option C — disable `/listen` entirely and rely on `/end-day` for capture. The interactive chain mines but doesn't archive raw substrate — lower privacy surface, less compounding.

## Future work (not blocking)

A more thorough fix would relocate `archive/` outside `<config-root>/` by default — e.g., `~/Library/Caches/nucleus/archive/` on macOS, `~/.cache/nucleus/archive/` on Linux. Configurable via `cortex.user-context.md`:

```yaml
archive:
  location: ~/.cache/nucleus/archive    # default-relocate (proposed)
```

For now, the default is `<config-root>/archive/` with this gitignore as the defensive layer.
