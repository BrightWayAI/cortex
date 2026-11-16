---
max_turns: 10
allowed_tools: [Read, Glob, Grep, Skill]
---

Dry run: load the `/start-nucleus` instructions with the Skill tool (loading them runs
nothing), then walk Step 3 for this exact scenario without executing any step.

My memory instruction file has an Autonomy policy with `## Always`, `## Ask first` and
`## Never` sections and no risk-tier sections. It matches the old default except for one
line I added under Ask first: "Post in the #clients Slack channel." My acknowledgment
file says `policy_version: 1.0.0`.

Tell me what you say to me, what my choices are, and exactly what gets written in each
case.
