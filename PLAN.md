# Plan: LOOP-001 — ADR-0014, the autonomy contract

## Spec Reference
docs/specs/LOOP-001-spec.md — six grill decisions codified: never-list, isolation rollout, human-only policy, zero-network escalation, drafting exclusion, budget mandates.

## Tech Context
Domain-only task (markdown governance docs + one stdlib guard edit). No external libraries → Context7 step skipped; flag recorded in sprint-state Notes. All API surface is our own (`phase_guard.py` allowlist tuple, test harness patterns already in `hooks/tests/`).

## Approach

### Chosen Strategy
Write the governing document first (Task 1) so the amendments (Tasks 2–3) quote a settled source rather than drafting law text twice. Hygiene fixes (Task 4) are TDD'd code and independent — parallelizable with Task 1. Release bookkeeping last (Task 5) because CHANGELOG wording summarizes the final documents. Branch: `feat/loop-001-adr-0014`.

### Rejected Alternatives
- Amending laws.md first, deriving the ADR from it: backwards — the ADR is the decision record; laws are its enforcement surface.
- Bundling the policy-file guard DENY rule here: contract belongs here, implementation belongs with LOOP-006 where its tests and approvals queue land together (spec Deferred).

### Risk Assessment
- **Highest risk**: Task 2 — laws.md is injected into every adopter session; wording must not contradict attended-mode behavior (INTAKE req 1). Mitigation: amendments are additive subsections ("In auto mode…"), never rewrites of existing gate language.
- **Integration risk**: guard allowlist change touches the file bump_version watches → migration-row wording (Task 5) must say "no project-file migration".
- **Testing risk**: none unusual — guard change is one tuple entry + one scenario.

## Task Summary
- Total: 5 | Sequential: 1→2→3→5 | Parallel group A: Task 4 (with 1)
- Estimated total: ~40 min | Wall clock with parallelism: ~30 min

## Dependency Graph
```
Task 1: ADR-0014 document ──→ Task 2: laws.md amendments ──→ Task 3: DESIGN + SCOPE ──→ Task 5: CHANGELOG + migration row + verify
Task 4: hygiene (untrack CONTEXT.md; guard allowlist + test)  [independent; joins before Task 5]
```

## Tasks

### Task 1: Write ADR-0014 (autonomy contract)
**Purpose**: The decision record everything else quotes.
**Files**: `docs/adr/0014-autonomy-contract.md` (CREATE)
**Context**: Follow the depth of ADR-0010/0013 (options with pro/con, live-fire style consequences). Content = the six grill clarifications in spec §Clarifications; never-list verbatim from AC2.
**Implementation**: Sections: Context (why autonomy now; research basis: Anthropic auto-mode classifier delegation, sd0x sentinel gates, ecosystem survey); Options per major axis (delegation model: none / full-auto / policy+judge triage — chosen; policy authorship: agent-editable / human-only hook-enforced — chosen; drafting: in/out — out); Decision (the six contracts); Consequences (incl. anchor-effect rationale, self-licensing prevention, budget invariants).
**Test (write FIRST)**: N/A (document) — verification is lint + AC checklist review against spec AC1–AC6.
**Verify**: `python scripts/harness_lint.py` (index sync will fail until Task 3 adds the DESIGN row — acceptable RED until then; final green at Task 5).
**Depends**: none | **Parallelizable**: with Task 4 | **Estimate**: 12 min | **Risk**: Low

### Task 2: Amend Laws 5 and 6 in rules/laws.md
**Purpose**: Put the contract into the text injected every session.
**Files**: `rules/laws.md` (MODIFY)
**Context**: Law 5 currently: four blocking gates table + "Silence is NOT approval". Law 6: token-bounded + handover rules.
**Implementation**: Law 5 gains "Modes" subsection: attended (default, unchanged) vs auto (opt-in; gates resolved by human-authored policy + independent judge; never-list verbatim; escalations to `.board/approvals.md`; silence in policy = escalate). Law 6 gains "Context strategy" subsection: isolation-first (auto always; attended via `- **Phase Isolation**:` config, default off); budget invariants (no uncapped runs; phase-boundary parking = standard handover). Both reference ADR-0014.
**Test (write FIRST)**: N/A — verify via `python hooks/tests/test_plugin_hooks.py` (laws.md is the injection payload; suite asserts injection still works) + lint.
**Verify**: `python scripts/harness_lint.py && python hooks/tests/test_plugin_hooks.py`
**Depends**: Task 1 | **Estimate**: 8 min | **Risk**: Medium (adopter-facing wording)

### Task 3: Update DESIGN.md and SCOPE.md
**Purpose**: Rationale + public positioning follow the law change.
**Files**: `docs/DESIGN.md` (MODIFY: Law 5/6 rationale paragraphs + ADR index row 0014), `docs/SCOPE.md` (MODIFY: replace "Not Suitable for Fully Autonomous Operation" with two-mode section: attended default / auto opt-in with never-list + budgets; keep the honesty about per-task quality trade)
**Test (write FIRST)**: N/A — lint enforces index sync (this task turns Task 1's RED index finding green).
**Verify**: `python scripts/harness_lint.py`
**Depends**: Tasks 1–2 | **Estimate**: 8 min | **Risk**: Low

### Task 4: Hygiene — untrack CONTEXT.md; guard allows capiva-blueprints (TDD)
**Purpose**: Ship the two self-init findings; project blueprint dir becomes writable config like .board.
**Files**: `hooks/tests/test_phase_guard.py` (MODIFY — RED first), `hooks/phase_guard.py` (MODIFY), git index (`git rm --cached docs/CONTEXT.md`; .gitignore entry already present locally — commit it)
**Context**: `ALWAYS_ALLOWED_DIRS = (".board", ".claude", ".state", ".github", "docs", "scripts", "templates", "reports")` at hooks/phase_guard.py:46.
**Test (write FIRST)**:
```python
set_state("IDLE")
cases.append(("IDLE: allow capiva-blueprints (project blueprint config)",
              run_guard(root, "Write", {"file_path": str(root / "capiva-blueprints" / "x" / "reference.md")})[0] is False))
```
Run → must FAIL (denied) before the tuple gains `"capiva-blueprints"`.
**Verify**: `python hooks/tests/test_phase_guard.py` (33/33) and `git ls-files docs/CONTEXT.md` returns empty.
**Depends**: none | **Parallelizable**: with Task 1 | **Estimate**: 6 min | **Risk**: Low

### Task 5: Release bookkeeping + full verification
**Purpose**: CHANGELOG + migration wording; everything green.
**Files**: `CHANGELOG.md` (MODIFY: add `## [1.1.0] — unreleased` with ADR-0014 summary + guard allowlist note), `skills/update-project/SKILL.md` (MODIFY: migration row `1.0.0 → 1.1.0 | Guard allowlist gains capiva-blueprints; laws text updated — no project-file migration required; config MAY add Phase Isolation field (absent = off)`)
**Test (write FIRST)**: N/A — `python scripts/bump_version.py 1.1.0 --check` must PASS (changelog entry + migration mention) — run it RED before writing, GREEN after.
**Verify**: `python scripts/harness_lint.py && python scripts/harness_lint.py --self-test && python hooks/tests/test_phase_guard.py && python hooks/tests/test_plugin_hooks.py && python scripts/bump_version.py 1.1.0 --check`
**Depends**: Tasks 1–4 | **Estimate**: 6 min | **Risk**: Low

## Quality Checklist
- [ ] Every AC (1–9) maps to a task: AC1–6→T1/T2; AC7→T2/T3; AC8 done at grill (board rows exist); AC9→T4/T5
- [ ] CONTEXT.md terms used consistently (never-list, self-licensing, park)
- [ ] No attended-default behavior change anywhere (INTAKE req 1)
- [ ] Test-first order on Task 4 commits (guard test before guard change)
- [ ] All suites + lint + release check green before TEST_VERIFY
