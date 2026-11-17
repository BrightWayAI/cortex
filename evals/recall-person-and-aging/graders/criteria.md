---
type: llm
weight: 1
---

This is a dry run: the response describes what the command would do and executes
nothing, which is correct. Judge the described behavior against these points only. Do
not fail the response for leaving out other details.

1. Third recall of a person with no page: the response says the user is asked whether
   to graduate them to a person page, and the page is created only if the user says
   yes.
2. The dormant entry is shown with a flag on the displayed line (dormant, with how long
   since it was confirmed), and the response says that flag is display-only: it is not
   written into the entry's text in the file.
3. After an explicit `/recall`, the response says the user is offered a triage of the
   aging entries (re-confirm, select one by one, demote, or skip).
4. The response says that triage offer is not made during automatic recall at the start
   of a conversation.

Pass if all four hold. Fail only if one is clearly violated.
