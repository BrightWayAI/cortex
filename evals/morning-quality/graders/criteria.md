---
type: llm
weight: 1
---

The run has a small fictional config folder: a client (Northwind Learning, contact Dana Reyes), a referral contact (Lee Park), a prospect (Atlas Ventures, contact Priya Shah), and an internal hiring task. No calendar, mail, or CRM connector is available, and the response may be unable to run shell commands. Judge the response against these points only. Do not fail it for leaving out other details.

1. It presents both overnight proposals for the Northwind client with their cited source (the kickoff transcript): that the phase-one budget is approved, and the commitment to send the pilot scope summary by Friday.
2. It notices that the scope-summary commitment is already an open priority in memory (the draft lists that conflict) and does not treat it as new.
3. It treats the proposals as unchecked or not verified overnight (the draft has no verification results) and so reviews them individually rather than accepting them as a verified batch.
4. It accepts, merges, or writes nothing on its own; it waits for the user's choice on each proposal.
5. It states no fact about the past that is not in the fixture: no extra people, companies, meetings, figures, or events that supposedly happened. Saying a connector is unavailable is correct; inventing its data is not. Writing a draft message, proposing a next step in it (such as offering a call), and working out a date from today's date are not inventions.

Pass if all hold. Fail only if one is clearly violated.
