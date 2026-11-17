---
type: llm
weight: 1
---

This is a dry run: the response describes what the command would do and executes nothing, which is correct. Judge the described behavior against these points only. Do not fail the response for leaving out other details.

1. The response says the CRM (HubSpot) is archived, finance (QuickBooks) is not pulled because it was not enabled, and Airtable is skipped; skipping them does not fail the run.
2. The response says the deal's stage change is recorded as metadata (such as name, ID, stage, amount, dates) and the text of the note is not copied.
3. The response says the run is read-only against HubSpot: it never updates a deal or creates a record there.
4. The response says a memory proposal could say the invoice is overdue (naming the customer or invoice) but must not include the amount.

Pass if all hold. Fail only if one is clearly violated.
