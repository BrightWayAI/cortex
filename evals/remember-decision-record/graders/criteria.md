---
type: llm
weight: 1
---

This is a dry run: the response describes what it would do and executes nothing, which
is correct. Judge the described plan against these five points only. Do not fail the
response for leaving out other details, for asking the user to confirm a date, or for
describing additional ordinary updates.

1. The response says the decision would be written as its own record under
   `memory/decision/` using `cortex_cli.py record-decision`.
2. The response says the record names the user as the one who decided, and includes
   what was decided, why, and the inputs (the growing scope and Dana's agreement).
3. The response says the September record would be passed as superseded, and that it
   is kept and marked superseded rather than deleted or rewritten.
4. The response says the Northwind node gets the returned one-line pointer.
5. The response does not fabricate a reason for the decision that the user did not
   give.

Pass if all five hold. Fail only if one is clearly violated.
