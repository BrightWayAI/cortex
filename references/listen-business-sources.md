# /listen business sources

Three optional sources `/listen` Step 1 can archive alongside calendar, mail, Slack,
Drive and transcripts: the CRM, the accounting system, and Airtable. Each is
read-only, metadata-first, and capped. The command file holds the rules; this file
holds what to pull and how to write it.

## Rules for all three

- **Read-only.** `/listen` never creates, updates, sends or deletes anything in these
  systems. Use only search, list and get tools.
- **Metadata first.** Record names, identifiers, dates, statuses and amounts. Do not
  copy note bodies, comment text, email bodies, line-item descriptions, attachments or
  free-text fields. A record's own title or name is metadata.
- **Changed that day only.** Pull records created or modified on `target_date` in the
  user's time zone. One date-filtered query per object type; never page through the
  whole system.
- **Capped.** At most 50 rows per section. Past the cap, write the count and the line
  `(<N> more not archived)`.
- **Skipped cleanly.** A source that is not enabled, not connected, or fails is listed
  in `_index.md` under `## Sources pulled` (`skipped (not configured)`) or `## Errors`
  and the run continues. A missing business source is never a failed run.
- **Identifiers are citations.** Every row carries the record ID so a proposal mined
  from it can cite `archive/<date>/<file>#<record-id>`.

## Enabling

In `<config-root>/plugins/cortex.user-context.md`:

```yaml
listen:
  business_sources:
    crm: true            # default: true when a CRM connector is connected
    finance: false       # default: false; turn on explicitly
    airtable:            # default: none; list the bases and tables to watch
      - base: <base id>
        tables: [<table id>, <table id>]
```

Finance is off until the user turns it on. Airtable has no default because there is
no safe way to guess which bases matter.

## CRM → `crm.md`

Capability: `connector.crm.read` (HubSpot or the configured CRM).

Pull, for `target_date`:

| Section | What | Fields |
|---|---|---|
| `## Deals changed` | Deals created, or whose stage, amount, close date or owner changed | deal ID, name, stage (and previous stage if the CRM returns it), amount, close date, owner, associated company |
| `## Tasks` | Tasks created, completed or newly overdue, owned by the user | task ID, subject, status, due date, associated record |
| `## Contacts and companies` | Records created, or whose lifecycle stage changed | record ID, name, company, lifecycle stage |
| `## Activity counts` | Logged emails, calls, meetings and notes | counts per associated deal or contact only; no bodies |

Format:

```markdown
# CRM — YYYY-MM-DD

## Deals changed
- <deal-id> — <name> — stage: <from> → <to> — amount: <amount> — close: <date> — owner: <owner>

## Tasks
- <task-id> — <subject> — <created | completed | overdue> — due <date> — on: <record>

## Contacts and companies
- <record-id> — <name> (<company>) — <created | lifecycle: <from> → <to>>

## Activity counts
- <record name> (<record-id>): <n> emails, <n> calls, <n> meetings, <n> notes
```

## Finance → `finance.md`

Capability: `connector.finance.read` (QuickBooks or the configured accounting system).

Pull, for `target_date`:

| Section | What | Fields |
|---|---|---|
| `## Invoices` | Invoices created, sent, paid, or that became overdue that day | invoice number, customer, total, balance, status, issue date, due date |
| `## Payments received` | Payments recorded | payment ID, customer, amount, date, invoice number |
| `## Estimates` | Estimates created, sent, accepted or declined | estimate number, customer, total, status |
| `## Receivables snapshot` | One line from the aging summary | total outstanding and total overdue |

Never pull payroll, employee, bank-account, tax or lending data, and never line items.

Format:

```markdown
# Finance — YYYY-MM-DD

## Invoices
- <invoice-number> — <customer> — total <amount> — balance <amount> — <sent | paid | overdue> — due <date>

## Payments received
- <payment-id> — <customer> — <amount> — <date> — invoice <invoice-number>

## Estimates
- <estimate-number> — <customer> — <amount> — <status>

## Receivables snapshot
- Outstanding: <amount> · Overdue: <amount>
```

**Amounts stay in the archive.** The archive is private; shared memory is not.
A proposal mined from `finance.md` may say that an invoice was sent, was paid, or is
overdue, and name the customer and invoice number. It never carries an amount, a
balance, a rate or a total. This matches the access-zone rule that pricing is
finance-only.

## Airtable → `airtable.md`

Capability: `connector.tables.read` (Airtable).

For each base and table listed under `listen.business_sources.airtable`, pull records
created or modified on `target_date`.

Fields: record ID, the table's primary field, and any single-select, date, number,
checkbox or linked-record field. Skip long-text, rich-text, attachment and comment
fields.

Format:

```markdown
# Airtable — YYYY-MM-DD

## <base name> / <table name>
- <record-id> — <primary field> — <created | modified> — <field>: <value>; <field>: <value>
```

## What mining does with these files

`note-taker` `mode: activity` reads all three with the other activity files. It
proposes, and never writes:

- from `crm.md`: deal and stage changes on the matching `bizdev/` or `client/` node,
  open-thread updates, and commitments implied by new tasks;
- from `finance.md`: open-thread updates and next actions about invoices (status
  only, no amounts);
- from `airtable.md`: status changes on the node the record's primary field matches;
  a record that matches no node is left out.

Every proposal cites the archive file and record ID, so the verifier can check it.
