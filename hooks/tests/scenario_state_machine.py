#!/usr/bin/env python3
"""
scenario_state_machine.py — deterministic behavioral eval of the pipeline's
core logic (PRD-005). No LLM, no subprocess: it imports the guard's transition
rules and exercises them against the normative state machine, and asserts the
guard's encoded edges match the documented Valid Transitions.

The skills/agents had ZERO behavioral tests (only prose cross-reference lint);
this is the rules-based tier the review's Principle 4 puts FIRST. The fast-lane
predicate and gate-routing remain prose (skill logic, not code) — those are the
golden-transcript territory that grows from real adopter traces.

    python3 hooks/tests/scenario_state_machine.py   # exit 0 iff all pass
"""
import importlib.util
import re
import sys
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent
ROOT = HOOKS.parent
spec = importlib.util.spec_from_file_location("phase_guard", HOOKS / "phase_guard.py")
pg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pg)


def main():
    cases = []

    # 1) curated transition truth table (non-tautological hand assertions)
    legal = [
        ("IDLE", "TRIAGE"), ("TRIAGE", "GRILL_SPEC"), ("GRILL_SPEC", "PLAN"),
        ("PLAN", "IMPLEMENT"), ("IMPLEMENT", "TEST_VERIFY"), ("TEST_VERIFY", "FINISH"),
        ("FINISH", "IDLE"),
        ("TRIAGE", "SPEC_PLAN"), ("SPEC_PLAN", "IMPLEMENT"),
        ("IMPLEMENT", "VERIFY_FINISH"), ("VERIFY_FINISH", "IDLE"),
        ("SPEC_PLAN", "GRILL_SPEC"), ("VERIFY_FINISH", "TEST_VERIFY"),
        ("GRILL_SPEC", "GRILL_SPEC"),          # self / field update
        ("IMPLEMENT", "BLOCKED"), ("BLOCKED", "IMPLEMENT"),  # escalate / resume
        ("PLAN", "IDLE"),                       # abort
    ]
    illegal = [
        ("IDLE", "IMPLEMENT"), ("IDLE", "FINISH"), ("TRIAGE", "IMPLEMENT"),
        ("GRILL_SPEC", "FINISH"), ("PLAN", "FINISH"), ("PLAN", "TEST_VERIFY"),
        ("IMPLEMENT", "FINISH"),                # must pass TEST_VERIFY (full lane)
        ("TRIAGE", "PLAN"),                     # skips grill
        ("SPEC_PLAN", "TEST_VERIFY"),
    ]
    for a, b in legal:
        cases.append((f"legal {a}->{b}", pg._transition_legal(a, b) is True))
    for a, b in illegal:
        cases.append((f"illegal {a}->{b} rejected", pg._transition_legal(a, b) is False))

    # 2) doc-parity: every forward edge in the template's Valid Transitions block
    #    is encoded in the guard. Drift between the documented machine and the
    #    enforced machine is exactly what this catches.
    tmpl = ROOT / "project-template" / ".board" / "sprint-state.md"
    documented = set()
    phases = {"IDLE", "TRIAGE", "GRILL_SPEC", "PLAN", "IMPLEMENT", "TEST_VERIFY",
              "FINISH", "SPEC_PLAN", "VERIFY_FINISH", "BLOCKED"}
    if tmpl.is_file():
        m = re.search(r"## Valid Transitions\s*\n```(.*?)```",
                      tmpl.read_text(encoding="utf-8"), re.DOTALL)
        if m:
            for line in m.group(1).splitlines():
                # split each chain on arrows; pair consecutive KNOWN phases
                toks = [tok.strip() for tok in re.split(r"→|->", line)]
                toks = [re.sub(r"[^A-Z_]", "", tok) for tok in toks]
                for a, b in zip(toks, toks[1:]):
                    if a in phases and b in phases:
                        documented.add((a, b))
    missing = [e for e in documented if not pg._transition_legal(*e)]
    cases.append((f"doc-parity: all {len(documented)} documented edges are guard-legal",
                  documented and not missing))

    failed = [n for n, ok in cases if not ok]
    for n, ok in cases:
        print(("PASS" if ok else "FAIL"), n)
    print(f"\n{len(cases) - len(failed)}/{len(cases)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
