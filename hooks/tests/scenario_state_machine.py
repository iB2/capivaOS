#!/usr/bin/env python3
"""
scenario_state_machine.py — deterministic behavioral eval of the pipeline's
core logic (PRD-005). No LLM, no subprocess: it imports the guard's transition
rules and exercises them against the normative state machine, and asserts the
guard's encoded edges match the documented Valid Transitions.

The skills/agents had ZERO behavioral tests (only prose cross-reference lint);
this is the rules-based tier the review's Principle 4 puts FIRST. Covered here:
the transition matrix (guard code vs the documented machine), the ADR-0010
fast-lane predicate as a FULL truth table, and the Law 5 / ADR-0014 gate-routing
matrix including never-list precedence (PRD-007 — the predicate and routing are
normative tables encoded from the prose, with doc-parity assertions so the
encoding cannot silently drift from the documents). Golden transcripts of full
skill runs remain future work that grows from real adopter traces.

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

    # 3) ADR-0010 fast-lane predicate — FULL truth table (PRD-007).
    #    Normative: fast iff priority is P2/P3 AND no new source files AND no
    #    schema/migration changes AND no architectural changes AND no new deps.
    def fast_lane(priority, new_files, schema, arch, deps):
        return (priority in ("P2", "P3")
                and not (new_files or schema or arch or deps))

    from itertools import product
    rows = list(product(("P0", "P1", "P2", "P3"),
                        (False, True), (False, True), (False, True), (False, True)))
    fast_rows = [r for r in rows if fast_lane(*r)]
    # structural properties — non-tautological assertions ABOUT the table:
    cases.append(("predicate: 64-row table, exactly 2 rows qualify fast (P2/P3, all-clean)",
                  len(rows) == 64 and
                  set(fast_rows) == {("P2", False, False, False, False),
                                     ("P3", False, False, False, False)}))
    cases.append(("predicate: P0/P1 never fast, even all-clean",
                  not fast_lane("P0", False, False, False, False) and
                  not fast_lane("P1", False, False, False, False)))
    cases.append(("predicate: any single true flag forces full lane",
                  all(not fast_lane(p, *flags)
                      for p in ("P2", "P3")
                      for flags in ((True, False, False, False),
                                    (False, True, False, False),
                                    (False, False, True, False),
                                    (False, False, False, True)))))
    # doc-parity: every conjunct is stated in ADR-0010's Decision section, and
    # laws.md carries the P0/P1 exclusion — encoding drift = fail.
    adr10 = ROOT / "docs" / "adr" / "0010-fast-lane-pipeline.md"
    adr_text = adr10.read_text(encoding="utf-8") if adr10.is_file() else ""
    cases.append(("predicate doc-parity: all 5 conjuncts present in ADR-0010",
                  all(s in adr_text for s in
                      ("P2/P3", "no new source files", "schema/migration",
                       "architectural changes", "no new dependencies"))))
    laws = ROOT / "rules" / "laws.md"
    laws_text = laws.read_text(encoding="utf-8") if laws.is_file() else ""
    cases.append(("predicate doc-parity: laws.md states P0/P1 can never go fast",
                  "P0/P1 can never go fast" in laws_text))

    # 4) Gate-routing matrix — Law 5 Modes / ADR-0014 (PRD-007). AUTO mode
    #    routes gates: policy clears what it covers; a context-fresh judge
    #    clears zero-anomaly cases; everything else escalates. The never-list
    #    takes PRECEDENCE over both — no machine may clear those, ever.
    def route(gate, priority, policy_covers, zero_anomaly, interlocutor=True):
        if gate == "merge":
            return "escalate"                    # never-list (1)
        if priority in ("P0", "P1"):
            return "escalate"                    # never-list (2)
        if gate == "spec" and not interlocutor:
            return "escalate"                    # never-list (3); board-AC carve-out = interlocutor True
        if policy_covers:
            return "policy"
        if zero_anomaly:
            return "judge"
        return "escalate"                        # never-list (4): silence means escalate

    # curated matrix rows (hand assertions):
    cases.append(("routing: merge gate escalates even when policy covers it",
                  route("merge", "P3", True, True) == "escalate"))
    cases.append(("routing: P0 quality gate escalates even when policy covers it",
                  route("quality", "P0", True, True) == "escalate"))
    cases.append(("routing: P1 spec gate escalates even for zero-anomaly",
                  route("spec", "P1", False, True) == "escalate"))
    cases.append(("routing: no-interlocutor spec escalates; board-AC carve-out clears",
                  route("spec", "P3", True, True, interlocutor=False) == "escalate" and
                  route("spec", "P3", True, True, interlocutor=True) == "policy"))
    cases.append(("routing: covered P2 gate clears via policy",
                  route("quality", "P2", True, False) == "policy"))
    cases.append(("routing: uncovered zero-anomaly P3 clears via judge",
                  route("plan", "P3", False, True) == "judge"))
    cases.append(("routing: uncovered anomalous case escalates (silence = escalate)",
                  route("plan", "P3", False, False) == "escalate"))
    # exhaustive never-list sweep: across the whole matrix, NOTHING machine-
    # clears a merge gate or any P0/P1 gate — the hard-coded precedence.
    all_combos = list(product(("spec", "plan", "quality", "merge"),
                              ("P0", "P1", "P2", "P3"),
                              (False, True), (False, True), (False, True)))
    cases.append(("routing: exhaustive sweep — merge and P0/P1 never machine-cleared",
                  all(route(g, p, pc, za, il) == "escalate"
                      for g, p, pc, za, il in all_combos
                      if g == "merge" or p in ("P0", "P1"))))
    # doc-parity: the never-list items this matrix encodes are stated in laws.md.
    cases.append(("routing doc-parity: never-list items present in laws.md",
                  all(s in laws_text for s in
                      ("(1) the merge decision", "(2) any gate on a P0/P1 task",
                       "(3) spec approval", "silence means escalate"))))

    failed = [n for n, ok in cases if not ok]
    for n, ok in cases:
        print(("PASS" if ok else "FAIL"), n)
    print(f"\n{len(cases) - len(failed)}/{len(cases)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
