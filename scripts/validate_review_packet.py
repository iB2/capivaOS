#!/usr/bin/env python3
"""
validate_review_packet.py — structural validator for the end-of-run review
packet (RFN-007). The packet is the batched-HITL backstop: after /capiva:auto
or /capiva:refine clears the board, the human reviews everything once. This
checks the packet is complete and self-consistent — it is NOT a quality gate
and approves nothing (the human still reads the PRs; the merge gate is theirs).

Usage:
  validate_review_packet.py <path>   validate a specific packet
  validate_review_packet.py --self-test   seed good/bad packets, assert caught

Packets live under docs/reports/ (per-project runtime, gitignored), so there is
no fixed file to check in the engine repo — the --self-test is the CI coverage
(same pattern as validate_fixtures.py / validate_decisions.py). Zero deps.
"""

import re
import sys

REQUIRED_SECTIONS = ["PR", "Spec", "AC", "Quality", "Verdict", "Deviations", "Parks"]
# A task row: "| RFN-007 | #55 | ... | Done |" — Done rows must carry a #<n> PR ref.
_ROW_RE = re.compile(r"^\|\s*([A-Z]+-\d+)\s*\|(.*)\|\s*$", re.MULTILINE)


def validate(text):
    findings = []
    low = text.lower()
    for sec in REQUIRED_SECTIONS:
        if sec.lower() not in low:
            findings.append(f"missing required section/column: {sec!r}")
    if "run-log" not in low and "run_log" not in low:
        findings.append("missing run-log reconciliation reference (packet must reconcile against .state/run-log.jsonl)")
    for m in _ROW_RE.finditer(text):
        task, rest = m.group(1), m.group(2)
        if "done" in rest.lower() and not re.search(r"#\d+", rest):
            findings.append(f"{task}: row marked Done but has no PR reference (#N)")
    return findings


def _self_test():
    failures = []
    good = (
        "# Review Packet — 2026-07-13\n"
        "Reconciled against .state/run-log.jsonl.\n\n"
        "| Task | PR | Spec | AC | Quality | Verdict | Deviations | Parks | Status |\n"
        "|---|---|---|---|---|---|---|---|---|\n"
        "| RFN-007 | #56 | spec.md | 5/5 | quality.md | CLEAR | 1 (path) | none | Done |\n"
    )
    if validate(good):
        failures.append(f"clean baseline failed: {validate(good)}")

    def expect(name, text, needle):
        f = validate(text)
        if not any(needle in x for x in f):
            failures.append(f"self-test '{name}': expected ~{needle!r}, got {f}")

    expect("missing-section", good.replace("| Verdict ", "| "), "Verdict")
    expect("done-no-pr",
           good.replace("| RFN-007 | #56 |", "| RFN-007 | -- |"),
           "no PR reference")
    expect("no-runlog", good.replace("Reconciled against .state/run-log.jsonl.", ""),
           "run-log reconciliation")

    if failures:
        print("validate_review_packet --self-test: FAIL")
        for x in failures:
            print("  -", x)
        return 1
    print("validate_review_packet --self-test: clean (3 seeded packets caught + baseline OK)")
    return 0


def main(argv):
    if "--self-test" in argv:
        return _self_test()
    paths = [a for a in argv if not a.startswith("-")]
    if not paths:
        print("validate_review_packet: no packet path given — nothing to validate (clean skip)")
        return 0
    from pathlib import Path
    p = Path(paths[0])
    if not p.is_file():
        print(f"validate_review_packet: {p} not found — clean skip")
        return 0
    findings = validate(p.read_text(encoding="utf-8"))
    if findings:
        print(f"validate_review_packet: FAIL ({p})")
        for x in findings:
            print("  -", x)
        return 1
    print(f"validate_review_packet: clean — {p} has all sections; every Done row has a PR")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
