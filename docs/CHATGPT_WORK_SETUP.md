# ChatGPT Work setup

Cortex supports two materially different ChatGPT Work execution modes. Both
use the same `skills/` workflows and config-root precedence chain; they differ
only in how the host reaches the user-owned Markdown files.

## Support matrix

| Surface | Memory access | Cortex transport | Status |
|---|---|---|---|
| ChatGPT desktop, Local Work | Direct, permissioned local access | Bundled stdio MCP server in `mcp.json` | Supported |
| ChatGPT Work on the web/cloud | No direct Mac filesystem access | Secure MCP Tunnel to the local stdio server | Supported for private/developer use after one-time tunnel setup |
| Public plugin directory | Public HTTPS MCP endpoint | Streamable HTTP + OAuth 2.1 | Not deployed by this repository |

A GitHub marketplace distributes plugin instructions; it does not upload or
synchronize the Cortex memory folder. The MCP bridge always operates against
the config root resolved on the machine where the bridge process runs.

## What the bridge exposes

`adapters/chatgpt_work/server.py` supplies eight bounded tools:

- `cortex_status`, `cortex_recall`, and `cortex_search` are read-only.
- `cortex_configure` writes the vendor-neutral pointer and initializes only
  missing starter files. It requires `user_confirmed=true`; replacing a
  pointer that targets another root also requires `force_pointer=true` after
  the user has separately confirmed the switch.
- `cortex_add_note` and `cortex_update_section` require
  `user_confirmed=true`; the server refuses the call until the host has shown
  the exact proposed change and obtained confirmation.
- `cortex_reindex` and `cortex_refresh_hot` regenerate derived files.

Every mutation shells out to `scripts/cortex_cli.py`. The bridge does not
reimplement locking, atomic writes, path validation, index generation, or hot
cache generation. It deliberately does not expose whole-file overwrite,
move, or delete tools. `/forget`, migrations, and other destructive workflows
therefore remain local/manual until a stronger review transaction is added.

## Local Work (recommended first setup)

Prerequisites: ChatGPT desktop, `uv`, and a trusted local checkout of this
repository. The portable `mcp.json` launches the official MCP Python SDK with
`uv`; the server then resolves the Cortex root in this order:

1. `CORTEX_CONFIG_ROOT`
2. `~/.cortex/config-root`
3. `~/Documents/.claude-plugin-config-root` (legacy)
4. `~/cortex-root`, only after `cortex_cli.py bootstrap` created it (cloud-first default)
5. `~/Documents/Claude` (default)

Install Cortex from the repository marketplace in the ChatGPT desktop plugin
browser, review the read/write capability and hook, and start a new Local Work
chat. The checked-in marketplace is `.agents/plugins/marketplace.json`; its local
source points to this repository root, where the portable `plugin.json` lives.
If the desktop app does not discover the repository automatically, add the
repository root with `codex plugin marketplace add /absolute/path/to/claude-cortex`
and install with `codex plugin add cortex@cortex-local`, then restart ChatGPT
desktop.

### First-run memory location

Existing Claude users should keep the root Claude already uses. Inspect the
resolved path without reading memory content:

```bash
python3 hooks/session_start.py --print-root
```

New users should choose a private local directory. The recommended setup is:

```bash
python3 scripts/configure_cortex.py \
  --config-root "$HOME/Documents/Cortex"
```

The same operation is available inside a Local Work chat:

```text
@Cortex configure my memory at ~/Documents/Cortex. Show me the exact path and
ask for confirmation before creating anything.
```

The command writes `~/.cortex/config-root`, creates `<config-root>/memory/`,
and seeds only missing `DASHBOARD.md`, `user.md`, `log.md`, `index.md`, and
`hot.md` files. Existing files are never overwritten. A pointer that already
targets a different root is refused unless the user explicitly confirms the
switch. The old root is not moved or deleted.

No ChatGPT-specific config file is needed. `CORTEX_CONFIG_ROOT` remains useful
for temporary/sandboxed execution and takes precedence over the pointer. A
project `.cortex.json` is optional and applies only when a host explicitly
loads that project override.

In a new chat, describe the workflow naturally or type `@` and choose Cortex
or one of its skills. The equivalent explicit forms are:

| Claude | Codex | ChatGPT Work |
|---|---|---|
| `/recall client:acme` | `$recall client:acme` | `@Cortex recall client:acme` |
| `/search procurement` | `$search procurement` | `@Cortex search procurement` |
| `/note strategy ...` | `$note strategy ...` | `@Cortex note strategy ...` |
| `/remember` | `$remember` | `@Cortex remember this conversation` |

Then test with:

```text
Use Cortex to report its status, then recall my dashboard.
```

For writes, Work should preview the exact mutation and ask first:

```text
Use Cortex to add this note to strategy: "Fixture wording." Show me the exact
entry before saving it.
```

## Cloud Work through Secure MCP Tunnel

This is the private path for using the same Mac-hosted memory from Work on the
web. It requires ChatGPT developer-mode access plus Platform tunnel permissions.

1. Create a Python environment for the bridge and install the official SDK:

   ```bash
   python3 -m venv .venv-chatgpt-work
   .venv-chatgpt-work/bin/pip install -r adapters/chatgpt_work/requirements.txt
   ```

2. In Platform tunnel settings, create a tunnel associated with both the
   intended Platform organization and ChatGPT workspace. Download the current
   `tunnel-client` from that page.

3. Initialize the tunnel with this server as the stdio target. Replace the
   repository and tunnel placeholders with real values:

   ```bash
   export CONTROL_PLANE_API_KEY="<runtime API key>"
   tunnel-client init \
     --sample sample_mcp_stdio_local \
     --profile cortex-local \
     --tunnel-id "<tunnel_id>" \
     --mcp-command "/absolute/path/to/claude-cortex/.venv-chatgpt-work/bin/python /absolute/path/to/claude-cortex/adapters/chatgpt_work/server.py --transport stdio"
   tunnel-client doctor --profile cortex-local --explain
   tunnel-client run --profile cortex-local
   ```

4. In ChatGPT, enable Developer mode under Settings → Security and login. Open
   Plugins, add an app, choose **Tunnel**, and select the Cortex tunnel.

5. Scan the tools, verify the annotations against the tool list above, then
   test status, configure, recall, search, and a confirmed note against a
   disposable fixture root before pointing the bridge at real memory.

Keep `tunnel-client` running whenever cloud Work needs Cortex. The tunnel is a
private developer/workspace connection, not a public marketplace deployment.

## Local HTTP diagnostics

For MCP Inspector or a local reverse proxy, run:

```bash
.venv-chatgpt-work/bin/python adapters/chatgpt_work/server.py \
  --transport streamable-http --host 127.0.0.1 --port 8787
```

The endpoint is `http://127.0.0.1:8787/mcp`. The server refuses non-loopback
listeners unless `CORTEX_MCP_ALLOW_NON_LOOPBACK=1` is explicitly set. Do not
set that flag on an internet-facing host without TLS and standards-compliant
OAuth 2.1 authorization. ChatGPT does not support substituting a custom API
key for end-user OAuth on a public MCP connection.

## Public or team-wide deployment

Do not expose the bridge directly from a laptop. A public or broadly shared
deployment needs all of the following before `mcp.json` is changed from stdio
to a remote `streamable-http` URL:

- a stable public HTTPS endpoint;
- OAuth 2.1 authorization with per-user resource and scope enforcement;
- an isolated per-user storage mapping, never one global Cortex path;
- rate limits, audit logs, backups, and secrets management;
- privacy policy, terms, deletion/export flow, and OpenAI plugin review.

The repository intentionally stops before those identity-provider and hosting
choices. The local/tunnel adapter is functional without pretending those
production controls exist.

## Cloud-first sync (v4.29+)

Cloud Work has no device filesystem, so a cloud-first config root is the supported shape:
run `python3 scripts/cortex_cli.py bootstrap --print-env` (with `CORTEX_ORG_REPO` /
`CORTEX_PRIVATE_REPO`) through the Cortex bridge, then `cortex_cli.py sync` after approved
writes. Git credentials for both repos must be available to the bridge; this is
host-specific and untested here. See `references/core-contract.md` §11B.
