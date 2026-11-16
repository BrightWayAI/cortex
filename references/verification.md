# Verification

How Nucleus checks a claim before a person is asked to trust it.

A producer (an agent that mines, drafts, or summarizes) is not a good judge of its own
output. Verification is a second, independent pass: a script checks what a script can
check, then the `verifier` agent checks whether each cited source really supports the
claim.

Introduced in cortex 4.32.0. This file is the contract; `agents/verifier.md` is the
agent's working instructions.

## The two passes

### 1. Deterministic pass

`python3 scripts/cortex_cli.py check-citations --config-root <root> --draft <date|path>`

Read-only. For every proposal in a `/listen` commit draft it reports one status:

| Status | Meaning |
|---|---|
| `fail` | No source cited, the cited file is missing, the path leaves the config root, or the cited line does not exist. Reasons: `no-source-cited`, `source-file-missing`, `source-outside-config-root`, `cited-line-out-of-range`. |
| `pass-verbatim` | The source exists and the proposed text appears in it, ignoring case, punctuation, and Markdown. |
| `needs-verifier` | The source exists but the text is a paraphrase, or the source is not a file (a thread or record ID: `source-is-not-a-file-path`). |

It also reports `citation_count` per proposal. The report holds proposal numbers, node
names, file names, and statuses. It never holds proposal text or source text.

A `fail` here is final: the verifier does not re-check it.

### 2. Verifier agent

The `verifier` agent receives the claims and their sources and returns, per claim, a
verdict (`pass`, `fail`, `unverifiable`), a confidence (`high`, `medium`, `low`), the
quoted evidence, and reason codes. Its return shape is in `agents/verifier.md`.

## Independence rules

These are what make the second pass worth having. A caller must keep all four.

1. **Fresh context.** The verifier is invoked as a sub-agent and is given only the
   claims, their sources, and optional reference material. Never pass the producer's
   reasoning, the conversation, or a hint about the expected answer.
2. **Different model.** The verifier's model differs from the producer's. Today the
   producers are `sonnet` and the verifier is `opus`.
3. **Read-only by allowlist.** The verifier's tools are `Read, Grep, Glob`. It cannot
   write, send, or run commands.
4. **No self-repair.** The verifier does not rewrite a failed claim, and the caller does
   not ask the producer to "fix it until it passes". A failed claim is shown to the
   user as failed, with the evidence.

## What a verdict allows

A verdict is evidence for the user's decision. It does not make the decision.

- `pass` does not write anything to durable memory. Unattended runs still stage
  proposals only (`references/autonomy-policy.md`).
- `fail` and `unverifiable` do not delete a proposal. It stays in the draft, marked, so
  the user can see what was caught.
- A `pass` at `low` confidence does not exist: the agent returns `unverifiable`.

## Where the result is recorded

Callers record the result next to the claim, using these field names:

- `Citation check:` — the deterministic pass result: `pass-verbatim`, `needs-verifier`, or `fail`
- `Verification:` — `pass`, `fail`, `unverifiable`, or `not-run`
- `Verifier confidence:` — `high`, `medium`, or `low`
- `Evidence:` — source, locator, and a quote of 25 words or fewer
- `Verification reasons:` — reason codes, or `none`

`not-run` is the honest value when the verifier was unavailable or errored. A caller
never writes `pass` for a claim that was not checked.

For a `/listen` commit draft these fields are written by
`python3 scripts/cortex_cli.py record-verification --config-root <root> --draft <date> [--verifier-results <file|->]`,
never by hand. The script enforces the merge rules:

- a deterministic `fail` stays `fail` whatever the verifier returned;
- a proposal with no valid verifier result is `not-run`;
- a `pass` at `low` confidence, or a `pass` with no evidence, is recorded as `unverifiable`;
- quotes are cut to 25 words;
- re-running replaces the earlier fields.

It also writes a `## Verification` section with the four counts above `## Proposals`.

## Callers

| Caller | Claims checked | Reference material | Since |
|---|---|---|---|
| cortex `/listen` Step 4.5 | every mined memory proposal in the night's commit draft (explicit brief marks are skipped) | none | 4.33.0 |
| clients `/sow` Step 5.5 | amounts, rates, caps, dates, deliverables, party names in the drafted SOW | the proposal; the prior agreement if one was used | clients 0.9.0 |
| clients `/client-status` Step 3.5 | every factual statement in each status draft | the SOW terms on file, for budget lines | clients 0.9.0 |
| admin `/invoices` Step 4.5 | every line item: customer, project, product/service, quantity, rate, amount, period, and the totals | the billing register and the time log | admin 0.6.0 |

## Checking a drafted document

`/listen` checks proposals. Other commands check a document they just drafted (a SOW, a
status update, an invoice packet) before showing it as ready. The procedure is the same
for all of them:

1. **List the checkable claims.** One claim per fact a reader would act on: every
   amount, rate, cap, quantity, date, deadline, name, deliverable, and commitment. Skip
   greetings, opinions, and vetted boilerplate copied verbatim.
2. **Give each claim its source.** The source is the file the fact came from. When the
   material is not already a file (pasted text, a connector result, a calendar or CRM
   pull), save it to a temporary file outside `<config-root>` and cite that absolute
   path. Do not cite a source you did not actually read while drafting.
3. **Invoke the `verifier` agent** with the claims, their sources, and any reference
   material the document must agree with. Pass nothing about how the draft was written.
4. **Show the result with the draft**, before asking for any approval: the counts, then
   every `fail` and `unverifiable` claim with the verifier's evidence and reason.
5. **Do not silently fix.** If the user asks for a correction, make it, then re-check
   the changed claims. Never present a claim as checked after editing it unchecked.
6. **If the verifier is unavailable** (cortex not installed, the agent errored), say
   "Not independently checked" with the reason. Never say or imply the draft was
   checked.

A clean result does not replace the command's own approval step. A send, a SOW, and an
invoice still need the user's explicit approval.

## Measuring it

The verifier is only useful if it is right. Two numbers say whether it is:

- **Overturn rate** — of the claims it passed, how many the user rejected or edited.
- **Catch rate** — of the claims it failed, how many the user agreed were wrong.

Recording these is part of wiring each caller. No unattended write is considered until
they have been observed over real use.
