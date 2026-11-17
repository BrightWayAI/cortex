# /morning display formats

The blocks `/morning` shows. The command file holds the logic; these are only how each thing is laid out. Fill every `<...>`; leave out a line whose value does not apply.

## Overnight summary (Step 1)

```
Good morning. Overnight /listen ingested yesterday:

  <N> calendar events
  <M> inbox threads (you in To/Cc)
  <K> Slack mentions
  <L> Drive changes
  <T> transcripts (<adapter1>: <count>, <adapter2>: <count>, ...)

Proposals staged: <P> total
Checked overnight: <p> pass, <f> fail, <u> unverifiable, <n> not run
  - <a> knowledge entries (INSIGHT / MODEL / GOTCHA / LESSON / RECIPE / CORRECTION)
  - <b> person-page updates
  - <c> commitment captures (to/from others)
  - <d> thread updates / closures

Sources status: <K> ok, <U> skipped/missing, <E> errors
(see archive/<date>/_index.md for details if errors)

To review: <R> need your decision one at a time, <B> verified and ready to accept together, <M> from yesterday's brief

Needs a nudge: <N> (<a> quiet deals, <b> with no reply, <c> you owe)

Ready to go through them? (y/n/skim)
```

## Proposal (Step 2b)

```
[Proposal N of P] <node-path> — <type> from <agent>
  Confidence: <high | medium | low>
  Source: archive/<date>/<file> · <section/line>
  Check: <Verification> (<Verifier confidence>) — <Evidence, or the Verification reasons if it failed>
  Conflicts: <list or "none">

  Current state in `<node-path>`:
  > <verbatim quote of relevant existing entry, or "no entry — new">

  Proposed:
  > <verbatim proposed content>

  (a)ccept / (r)eject / (e)dit / (d)efer / (s)kip-remaining
```

## Verified batch (Step 2c)

```
Verified overnight — <B> updates, each checked against its source, none conflicting:

  1. <node-path> — <type>: <one-line summary of the proposed content>
       evidence: <source> (<locator>) — "<quote>"
  2. ...

Accept all <B>? (y / drop <numbers> / open <number> / one-by-one / later)
```

## Nudge (Step 2.95)

```
[Nudge N of M] <subject> — <quiet deal | no reply | you owe this>
  Quiet since <date> (<days quiet>)
  Source: <source>

  Draft:
  > <the drafted message, or "none — <why>">

  (u)se it / (e)dit / s(n)ooze / (d)ismiss / (l)ater
```

## Closing report (Step 5)

```
Morning merge complete.

  Accepted: <a> proposals → <k> nodes updated, <p> changelog entries written
  Rejected: <r> proposals → reject-log updated
  Deferred: <d> proposals → still in draft

  hot.md: refreshed (<w> words)
  memory/index.md: refreshed (<n> nodes catalogued)
  Reflection: captured · Today's priorities/outreach: <c> seeded to briefs/<today>.seed.json

Run /brief to start the day with today's working surface? (y/N)
```

## Reflection (Step 4)

```markdown
## Reflection

- **Biggest thing that got done yesterday:** <answer or "—">
- **What blocked you:** <answer or "—">
- **The one thing today has to move:** <answer or "—">
- _Captured by /morning at <HH:MM>._
```
