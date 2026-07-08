# Contributing to capivaOS

Thanks for looking under the hood. Honest expectations first:

**This is presently a single-maintainer project.** CODEOWNERS routes every
path to one account, which means "reviewed" is self-review plus the CI gates.
External PRs are welcome and read with care, but review turnaround is
best-effort — an issue describing the problem before a large PR saves both of
us time. Security reports go through the process in [SECURITY.md](SECURITY.md),
not public issues.

## Running the quality gates locally

Everything CI runs, in order — all stdlib-only Python 3.10+, no installs:

```
python scripts/harness_lint.py --self-test   # the linter proves it catches seeded drift
python scripts/harness_lint.py               # 13 cross-reference/parity checks
python scripts/validate_impl_report.py --self-test
python scripts/bump_version.py --check       # release contract
python hooks/tests/scenario_phase_guard.py   # guard deny/allow scenarios
python hooks/tests/scenario_plugin_hooks.py  # dispatcher, injection, persistence
```

(The scenario files are deliberately not named `test_*.py` — `pytest` would
collect zero tests and exit green. They are self-contained runners.)

CI additionally installs the plugin with two pinned real CLI versions —
`harness_lint` once said "clean" while the real CLI rejected the manifest.

## House rules the CI will hold you to

1. **Claim and code land in the same commit.** Anything described as
   "mechanically enforced" must exist in `ENFORCED_SURFACES`
   (`hooks/phase_guard.py`) with its `<!-- enforced: X -->` markers in
   README + SECURITY.md, its deny logic, and its scenarios — lint check 13
   fails any partial landing, in either direction.
2. **A bug class found = a lint check added.** Fixing an instance without
   its detector just schedules the regression. Every check ships with a
   seeded fragment in `--self-test` proving it catches what it claims.
3. **Fail-open is the posture.** Hooks must never brick a project: reads
   fail open loudly; missing interpreters exit 0. If your change can block
   a session on its own failure, it's wrong.
4. **Zero dependencies, zero network** in anything that ships (hooks,
   scripts). Dev-time tooling on your machine is your business.
5. **Schema changes need a migration row** in
   `skills/update-project/SKILL.md` in the same release —
   `bump_version.py --check` blocks the release without it.
6. **Decisions of consequence get an ADR** (`docs/adr/`, indexed in
   DESIGN.md — the lint checks both directions). Match the depth of the
   existing ones; rubber stamps stand out here.

## What's most useful right now

- Running the harness on a real project and reporting where it fought you
  (ergonomics reports are as valuable as bug reports)
- A fourth blueprint (Go, Java, Rails…) — validate with
  `python scripts/harness_lint.py --check-blueprint <dir>`
- Breaking the guard: if you find a deny bypass that isn't in SECURITY.md's
  documented limits, that's a finding we want
