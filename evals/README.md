# Evals

Run from the repository root:

```
claude plugin eval . --scaffold --ablation none --judge-model sonnet
```

`--scaffold` is required. The three morning cases (`good-morning`, `morning`,
`run-my-morning`) each run `seed.sh`, which calls `_fixtures/seed-config-root.sh`. That
script builds a small, fictional config root in the run's workspace and writes the
`~/.cortex/config-root` pointer in the run's temporary home. Without it the run has no
config root, the session-start check reports that, and `/morning` correctly stops.

The two onboarding cases (`lets-get-started`, `start-nucleus`) run with no config root
on purpose: they test a fresh install.

The fixture is invented data. Never copy real memory into it.
