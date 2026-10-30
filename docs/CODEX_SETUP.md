# Codex adapter setup

Cortex uses the same Markdown memory root from Claude and Codex. There is no
Codex-specific database or pointer file.

## What is included

- `AGENTS.md` is the durable Codex entrypoint.
- `.agents/skills/` contains generated Codex-discovery copies of every
  canonical workflow. Invoke them as `$remember`, `$recall`, `$note`, and so
  on; natural-language activation also works.
- `plugin.json` is the portable Agent Plugins manifest. Its trusted
  `SessionStart` hook reads a bounded bundle from `memory/hot.md`,
  `memory/me/user.md`, and `memory/DASHBOARD.md`.
- `.codex/agents/` maps the portable read-oriented roles to Codex custom
  agents. `note-taker`'s `mode: conversation` is deliberately absent because
  Codex does not expose an equivalent cross-session transcript capability
  (`mode: transcript` / `mode: activity` are mapped).

The generated skill wrappers in `skills/` remain compatible with the Claude
plugin. `commands/*.md` continues to be the only workflow authority.

## Resolve and grant the shared memory root

The adapter calls `scripts/lib/config_root.py`; precedence remains:

1. an explicit workflow override, when one is supplied;
2. `CORTEX_CONFIG_ROOT`;
3. `~/.cortex/config-root`;
4. `~/Documents/.claude-plugin-config-root` (legacy);
5. `~/cortex-root`, only after `cortex_cli.py bootstrap` created it (cloud-first default);
6. `~/Documents/Claude` (backward-compatible default).

Existing Claude users should keep the resolved root and do not need a second
memory directory. New users can set the vendor-neutral pointer and initialize
only missing starter files with:

```bash
python3 scripts/configure_cortex.py \
  --config-root "$HOME/cortex-root"
```

This writes `~/.cortex/config-root`. It refuses unsafe paths and will not
replace a pointer that targets a different root unless `--force-pointer` is
supplied after the user has confirmed that switch. It never moves or deletes
the old root.

### Imported Claude global instructions

Codex can import a user's global Claude instructions. An importer may
mechanically change a reference from `memory/CLAUDE.md` to
`memory/AGENTS.md`, even though the former is a legacy, user-owned file inside
the shared config root rather than the plugin's repository entrypoint.

Re-running `configure_cortex.py` handles that case idempotently: when
`memory/CLAUDE.md` exists and `memory/AGENTS.md` does not, it creates a short
`memory/AGENTS.md` forwarding shim. It never copies, renames, edits, or
replaces the legacy instructions. New config roots without legacy
`memory/CLAUDE.md` receive neither file; the installed plugin's root
`AGENTS.md` remains the Codex instruction entrypoint.

Review imported global instructions and keep the vendor-neutral pointer
`~/.cortex/config-root`. A `.Codex-plugin-config-root` pointer is not part of
the Cortex resolution chain.

Inspect the result without reading memory content:

```bash
python3 hooks/session_start.py --print-root
```

Configure that absolute path as a Codex sandbox writable root. Read-only
workflows need read access; mutating workflows need write access. Sandbox
configuration is host/user state and is intentionally not committed with an
absolute machine-specific path. If Codex prompts for access, grant only the
resolved Cortex root—not a home directory or broad parent.

`adapters/codex/config.toml.example` contains the relevant Codex keys. Merge
them into the active config layer and replace its placeholder:

```toml
approval_policy = "on-request"
sandbox_mode = "workspace-write"

[sandbox_workspace_write]
writable_roots = ["/ABSOLUTE/PATH/TO/CORTEX-CONFIG-ROOT"]
network_access = false
```

The Codex sandbox file is permission configuration, not another Cortex
location pointer. The only persistent Cortex pointer needed is
`~/.cortex/config-root`; `.cortex.json` is an optional project behavior
override.

For fixture-only diagnostics, inject both paths explicitly:

```bash
CORTEX_CONFIG_ROOT=/tmp/cortex-fixture \
  python3 hooks/session_start.py --home /tmp/cortex-home --print-root
```

## Enable the session-start hook

Install or enable this repository as the `cortex` plugin, then review and
trust `hooks/hooks.json`. Codex does not execute plugin hooks until the user
trusts their current definition. The hook is read-only and output-bounded.

The repository intentionally has no `SessionEnd` auto-commit hook. A hook can
remind an agent, but it cannot guarantee that model-driven extraction or a
memory commit completed. Invoke `$remember` when the commit matters.

## Regenerate and validate adapters

```bash
python3 scripts/generate_codex_skills.py --write
python3 scripts/check_repo.py
```

All adapter tests inject temporary homes and config roots. Do not point test
commands at a real Cortex memory directory.

## Cloud-first sync (v4.29+)

The config root may be two git checkouts (`memory/` = shared org repo, `.private/` =
per-user private repo, joined by directory symlinks); see `references/core-contract.md`
§11B. What this means for Codex:

- Keep `writable_roots` pointed at the resolved root (for example `~/cortex-root`).
  The `memory/me`, `memory/staged`, `archive`, `briefs`, and `plugins` symlinks all
  resolve inside that root, so one writable root covers them.
- The default sandbox has `network_access = false`, so Codex cannot push. On a machine
  that runs the host sync job (`cortex_cli.py sync` under launchd), that is fine: Codex
  writes locally and the job pushes within minutes. Do not enable network access just to
  push; do not `git push` by hand.
- A Codex surface with no persistent local root (cloud) must run
  `python3 scripts/cortex_cli.py bootstrap --print-env` first and needs git credentials
  for both repos, and either both repos attached as checkouts (found by their
  `.cortex-role` marker) or `CORTEX_ORG_REPO` / `CORTEX_PRIVATE_REPO` (or `--org-repo` /
  `--private-repo`). That path is untested on Codex.
- Never edit shared nodes directly once more than one actor writes (§11A); write
  proposals, then run `cortex_cli.py sync`. A sync conflict is reported with a
  `conflict/<host>/<ts>` branch, never auto-resolved or force-pushed.
