---
description: Capture user identity (stable actor ID, name, company, role, time zone, and primary tools) once in `<config-root>/memory/me/identity.md`. Uses the vendor-neutral config-root resolver so every host and plugin reads the same file. Re-run anytime to update.
---

# /setup-identity

One-time identity bootstrap. Captures the basics that every plugin needs and writes them to a canonical shared file. Lives in whatever folder you've designated as your plugin config root (or `~/Documents/Claude/` by default for backward compatibility).

After this runs, every plugin's `/setup-*` command reads identity from this file instead of re-asking. You only ever update identity in one place.

---

## Step 0 — Resolve plugin config root

Resolve `<config-root>` through the canonical chain in
`references/core-contract.md`: explicit override, `CORTEX_CONFIG_ROOT`,
`~/.cortex/config-root`, legacy pointer, then default. A malformed higher-priority
pointer is an error, not permission to fall through. Request filesystem access only
for the resolved directory.

If an intentional root already resolves, continue to Step 1. Otherwise continue to
first-time bootstrap.

### First-time bootstrap

The pointer doesn't exist, so this is the user's first plugin setup of any kind. Prompt:

> "First-time Nucleus setup. Where should the shared config root live? Recommended: `~/cortex-root` (press enter to accept). Avoid `~/Documents`, `~/Desktop`, `~/Downloads` and iCloud folders: macOS prompts for access and cloud sync can lock files, so scheduled jobs and sandboxed hosts lose access. It will contain private identity/voice files under `memory/me/`, shared memory nodes, and a `plugins/` settings directory."

Once the user provides the path:

1. Ensure access to `<path>`. If running in Cowork and the folder isn't already mounted in this session, call `request_cowork_directory(<path>)`. If running in Claude Code or another environment with direct filesystem access, no mount call is needed — proceed to read or write the file.
2. Invoke the bundled deterministic configurator:
   `python3 scripts/configure_cortex.py --config-root <path>` (omit `--config-root` to use `~/cortex-root`). It creates the
   vendor-neutral pointer (`~/.cortex/config-root`, primary) atomically, mirrors it
   to the legacy pointer (`~/Documents/.claude-plugin-config-root`, fallback for
   hosts/plugins that haven't migrated), creates `memory/me/` and `plugins/` if
   missing, and seeds only missing foundation files.
3. If the configurator refuses because the pointer resolves elsewhere, show both
   resolved paths and request a second explicit confirmation. Only after that
   confirmation may it be rerun with `--force-pointer`.
4. Confirm: "Saved. All Nucleus hosts and plugins will resolve `<path>` from the vendor-neutral Cortex pointer."

For the rest of this document, **`<identity-path>`** refers to `<config-root>/memory/me/identity.md`.

---

## Step 1 — Check for existing identity

Read `<identity-path>` if it exists.

- **Populated** → ask: "Identity already captured. Update specific sections, or start over?"
  - "Update [section]" → jump there.
  - "Start over" → continue full interview.
- **Missing** → start fresh. Create the parent directory if needed.

---

## Step 2 — The interview

One section at a time. Confirm before moving on.

### Section 1 — Person

- Full name
- Stable actor ID (default: slugified full name, e.g. `zach-wagner`; confirm it
  because collaborative provenance uses it and it should not change casually)
- Title / role (founder, principal, VP marketing, etc.)
- Email address (primary work)
- Time zone (IANA format, e.g., `America/New_York`)
- Pronouns (optional)

### Section 2 — Company

- Company name
- One-sentence description of what your company does
- Industry (e.g., AI consulting, climate tech, SaaS, healthcare)
- Stage / type (founder, agency, in-house team, freelancer, nonprofit, etc.)
- Website URL
- Headcount range (1, 2–10, 11–50, 51–200, 200+)

### Section 3 — Primary tools

These help plugins know what's available without re-asking.

- Primary CRM (HubSpot / Salesforce / Pipedrive / Attio / Affinity / none)
- Primary calendar (Google Calendar / Outlook / Apple / other)
- Primary email (Gmail / Outlook / other)
- Communication tools you use daily (Slack, Teams, Discord — pick what applies)
- Storage / drive (Google Drive / Dropbox / OneDrive / Notion / other)

### Section 4 — Communication defaults

- Default response time you commit to (e.g., "within 1 business day")
- Default working hours (start, end)
- Out-of-office cadence (e.g., "rarely; back same day," "Fridays off," "vacation pre-announced")

---

## Step 3 — Write the identity file

Populate `<identity-path>` with the answers, using this exact structure (other plugins parse it):

```markdown
# User Identity

_Last updated: [today]_
_Created by /setup-identity (cortex plugin)_

## Person
- **Actor ID:** ...
- **Name:** ...
- **Title / role:** ...
- **Email:** ...
- **Time zone:** ...
- **Pronouns:** ... (optional)

## Company
- **Name:** ...
- **What we do:** ... (one sentence)
- **Industry:** ...
- **Stage:** ...
- **Website:** ...
- **Headcount:** ...

## Primary tools
- **CRM:** ...
- **Calendar:** ...
- **Email:** ...
- **Communication tools:** ...
- **Storage / drive:** ...

## Communication defaults
- **Response time:** ...
- **Working hours:** ...
- **Out-of-office:** ...
```

Create the parent directory if it doesn't exist.

---

## Step 3.5 — Write privacy defaults (.gitignore) (v4.7.2+)

After the identity file is written, ensure `<config-root>/.gitignore` exists with the privacy-sensitive paths excluded. Defensive — protects future `/listen` runs from accidentally committing raw email / Slack / transcript content to a git repo.

Logic:
1. If `<config-root>/.gitignore` exists, leave it alone (idempotent — `/listen` Step 0.5 will append missing patterns later if needed).
2. If it doesn't exist, write the full template from `references/gitignore-template.md`. Log one line to the user: "Wrote `.gitignore` with privacy defaults — protects raw archive content from accidental git commits. See `references/gitignore-template.md` for what's covered."
3. If `<config-root>/` lives inside a common cloud-sync path (iCloud, Dropbox, OneDrive, Google Drive), also surface a one-line note: "`.gitignore` doesn't prevent cloud sync. If you sync this folder via <provider>, see `references/gitignore-template.md` for the local-only archive pattern."

No user gate. Best-effort — if the write fails, log internally and continue.

---

## Step 3.6 — Initialize memory-as-git (v4.12.0+)

After the identity file + parent .gitignore are written, offer to initialize `<config-root>/memory/` as a git repository. Versioned memory becomes the substrate for daily diff review (`/morning` Step 0.5) and rollback safety (`git revert HEAD` undoes a day).

Logic:
1. Check whether `<config-root>/memory/` exists. If not, skip (cortex memory hasn't been bootstrapped yet — first `/end-day` will create it; init can happen then).
2. **Symlink check (v4.12.2+):** if `memory/` is a symlink (`test -L <config-root>/memory`), surface a warning before proceeding:
   > "⚠ `<config-root>/memory/` is a symlink pointing to `<resolved-path>`. memory-as-git's `.git/` directory will live at the symlink target. If that target lives in iCloud / Dropbox / OneDrive / Google Drive, the cloud-sync provider will sync `.git/` itself, which can corrupt across machines. Proceed only if you understand the implications. (y to continue / n to skip init)"
   Default no in `confirm` mode; ask in `suggest` mode; proceed in `auto` mode with a logged note.
3. Check whether `<config-root>/memory/.git/` exists. If yes → "Memory-as-git already initialized; skipping init." Then jump to Step 4a to validate the .gitignore even though we're not re-init'ing.
4. If memory exists but no git → prompt:
   > "Initialize memory-as-git? This makes `<config-root>/memory/` a local git repo so:
   >   - Each `/end-day` commits the day's memory changes as one reviewable unit
   >   - `/morning` surfaces what changed overnight as a git diff
   >   - You can `git revert HEAD` to roll back a day if something landed wrong
   >   - Optional: push to a private GitHub or self-hosted git for off-machine backup
   >
   > Default: yes, local-only (your memory stays on this machine). Recommended unless you have a reason to skip. (y / n / skip-for-now)"

5. On `y` or default-yes (autonomy: auto):
   ```
   cd <config-root>/memory

   # If .git/ already exists, skip git init but still validate .gitignore (Step 4a below).

   git init -b main
   git config user.name "<identity.name from identity.md>"
   git config user.email "nucleus-memory@localhost"
   ```

   **Email-default rationale (v4.12.2):** `nucleus-memory@localhost` is the default git-commit-author email. It carries no PII, no tenancy info, no domain leakage. It IS valid (`localhost` is a reserved TLD-equivalent for local use per RFC 6761).

   The user's real email from `identity.md` is NOT used by default — every git commit author header would otherwise leak that email into any pushed remote. If the user explicitly wants their real email on commits (e.g., for off-machine collaboration with attribution), they can override via:
   ```
   memory_as_git:
     commit_author_email: alice@example.com   # opt-in only; in cortex.user-context.md
   ```
   `/end-day` Step 5.8 reads this; falls back to the localhost default if unset.

   Then proceed to Step 4a.

Step 4a. **Write or validate `memory/.gitignore` (v4.12.2 fingerprint-precise logic):**

   The v4.12.0 template emitted inline comments which `.gitignore` parses as literal filenames. v4.12.1 introduced a regex-based detector that was too broad — it false-positived on legitimate user-added inline comments. v4.12.2 uses a fingerprint-precise match.

   ```
   target_path = <config-root>/memory/.gitignore
   ref_local_only = local-only variant from `references/memory-gitignore-template.md`
   ref_remote_safe = remote-safe variant from same
   user_context_path = <config-root>/plugins/cortex.user-context.md

   # Decide which variant to write
   remote_set = user_context_path contains a `memory_as_git.remote:` line with non-empty value
   chosen_variant = ref_remote_safe if remote_set else ref_local_only

   If target_path does NOT exist:
     Write chosen_variant to target_path. (Fresh install — no bug to fix.)

   If target_path exists:
     Read its content.

     Detect v4.12.0 fingerprint (precise, not heuristic):
       The v4.12.0 bug emitted exactly these 3 inline-comment lines:
         - line containing "log.md" AND "operations chronicle"
         - line containing "hot.md" AND "7-day rolling cache"
         - line containing "index.md" AND "auto-maintained catalog"
       Only treat as buggy if ALL THREE are present on a single non-comment line each.

     If v4.12.0 fingerprint matches:
       Rewrite target_path from chosen_variant.
       Run: git rm --cached hot.md index.md log.md .state.json .person-mention-counts.json .person-recall-counter.json 2>/dev/null
       (silently ignore errors for files not currently tracked)
       In autonomy mode `suggest` or `confirm`, surface a confirmation BEFORE the rm:
         "Detected v4.12.0 .gitignore bug. About to un-track: hot.md, index.md, log.md, .state.json, .person-mention-counts.json, .person-recall-counter.json. These files won't be deleted — just removed from git's index. Proceed? (y/n)"
       In `auto`, log and proceed without prompt.
     Elif chosen_variant differs from current content (e.g., promoting local→remote):
       Surface: "Promoting to remote-safe gitignore (you configured `memory_as_git.remote`). Will exclude PII-dense files: triage-log.md, dismissed-proposals.log. Proceed? (y/n)"
       On y: Rewrite target_path from ref_remote_safe; run git rm --cached on the newly-excluded files.
     Else:
       Leave target_path alone (idempotent — user may have customized; we don't touch).
   ```

Step 4b. **Remote-already-pushed remediation check (v4.12.2+)**

   If `git config remote.origin.url` returns a value AND `git log --oneline origin/main 2>/dev/null` returns lines AND the local repo has shown the v4.12.0 fingerprint at any point (presence of `<config-root>/memory/staged/skip-logs/remote-remediation-acknowledged` would indicate already-handled — skip if so):

   Surface (one-time):
   > "Pre-v4.12.2 commits with high-churn cache files and possibly PII-dense files exist on your remote at `<remote-url>`. Local repair has un-tracked them going forward, but already-pushed history retains them. To purge remote history:
   >
   >   `git filter-repo --invert-paths --path hot.md --path index.md --path log.md --path .state.json --path triage-log.md --path dismissed-proposals.log`
   >   `git push origin main --force`
   >
   > This rewrites history. Only do it if you're the sole user of the remote. See https://github.com/newren/git-filter-repo for installation. After remediation, mark acknowledged."

   On user choosing `acknowledge` or `skip`, create the marker `<config-root>/memory/staged/skip-logs/remote-remediation-acknowledged`. Subsequent runs skip this step.

Step 5. **Initial commit (only if `.git/` was freshly created in Step 5):**
   ```
   git add .
   git commit -m "Initial memory snapshot (cortex v4.12.2 /setup-identity init)"
   ```
   Surface: "Memory-as-git initialized. Local repo at `<config-root>/memory/.git/`. Daily commits via `/end-day` Step 5.8; diff review via `/morning` Step 0.5."

Step 5a. On `n` or `skip-for-now`:
   Surface: "Skipped. Re-run `/setup-identity` later, or set `memory_as_git.enabled: true` in `<config-root>/plugins/cortex.user-context.md` and run `/end-day` to init."

Step 6. **Optional remote configuration** (only if user said `y` AND autonomy is not `auto`):
   > "Configure a remote for off-machine backup? (private GitHub recommended for moderate privacy; self-hosted gitea/forgejo/gitlab for higher control; press Enter to skip and stay local-only)"

   If user provides a URL:
   - Write `memory_as_git.remote: <url>` to `<config-root>/plugins/cortex.user-context.md`
   - Write `memory_as_git.push_on_close: true` to same
   - **Re-run Step 4a** (so the gitignore promotes to remote-safe variant before any push).
   - Surface: "Remote configured. `/end-day` Step 5.8 will push after each commit. Gitignore promoted to remote-safe variant — triage-log.md, dismissed-proposals.log, and similar PII-dense files are now excluded from commits."
   - DO NOT run an initial push here — let the user manually `git remote add origin <url> && git push -u origin main` after verifying the remote URL.

**Idempotent:** safe to re-run. Existing `.git/` is preserved.

---

## Step 3.7 — Wire identity into user.md graph (v4.12.0+)

After identity.md is written, ensure `<config-root>/memory/me/user.md` has a wikilink to `[[identity]]` in its Canonical Files section. Without this link, identity.md is an orphan in the Obsidian graph view.

Logic:
1. Check whether `<config-root>/memory/me/user.md` exists. If not, skip — cortex's first `/remember` will create it with proper canonical-file references.
2. Read `<config-root>/memory/me/user.md`.
3. Check whether `[[identity]]` is already present anywhere in the file. If yes, skip (idempotent).
4. Look for a `## Canonical Files` section header in user.md.
   - **If found**: append `- [[identity]] — user profile (name, company, tools, working hours)` as a bullet under it.
   - **If not found**: insert a new section right before the first existing `##` heading:
     ```
     ## Canonical Files
     - [[identity]] — user profile (name, company, tools, working hours)
     ```
5. Write user.md back.

Symmetric note: Comms Desk's `/setup-voice` Step 3.5 does the same for `[[voice]]`. Both are idempotent. The end state: `user.md` Canonical Files section links to the canonical private profile files so Obsidian's graph view shows the connections.

**Why this matters:** `voice.md` and `identity.md` live under the private
`memory/me/` scope, which the shared-memory index and relinker intentionally
exclude. The setup commands are therefore responsible for wiring their links.

No user gate. Best-effort — if user.md doesn't exist or the write fails, log and continue.

---

## Step 4 — Confirm and offer next step

Summarize what was captured (one short paragraph). Then offer:

> "Identity saved to `<identity-path>`. Other plugins (Growth, Clients, Today's Brief, etc.) will read this automatically — you won't be asked these questions again. To configure a specific plugin's domain settings (CRM properties, ICP, voice, offerings catalog, etc.), run that plugin's setup command — those interviews skip identity questions and only ask plugin-specific things."

---

## Behavior rules

- One section at a time. Don't bombard.
- Skip what doesn't apply. "I don't have a CRM yet" is valid.
- Idempotent. Re-running updates existing sections.
- Never silently overwrite. If a value would change, confirm with the user.
- The file lives at `<identity-path>` — wherever the plugin config root points (or the legacy default). Stable across sessions. Plugins read it but don't own it.

## What this is NOT for

- Plugin-specific configuration (CRM custom properties, ICP, voice rules, offerings catalog) — those go in each plugin's per-plugin config at `<config-root>/plugins/<plugin>.user-context.md` via that plugin's setup.
- Capturing observations / preferences — that's what Cortex's passive observation
  does in shared memory nodes under `<config-root>/memory/`; private profile facts
  belong under `<config-root>/memory/me/`.
