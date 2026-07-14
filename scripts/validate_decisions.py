#!/usr/bin/env python3
"""
validate_decisions.py — no-orphan validator + read-back metric for the two-tier
decision-log (RFN-005; ADR-0017 invariant 2: the write-back loop must close, or
it is not built).

`.board/decisions.md` is per-project runtime state (gitignored), so on the
engine repo this validator finds no file and exits clean. Its `--self-test`
seeds malformed logs and asserts each is caught — that is the CI coverage
(same pattern as evals/context-answerer/validate_fixtures.py).

Two tiers (ADR-0017): a decision-log entry is task-scoped NON-dispositive prior
art. Only a human promoting it to an ADR/CONTEXT term (status: promoted, with a
Promoted-to target) makes it dispositive. A promoted-then-superseded decision is
marked retired.

Read-back metric: answerer-consulted events in .state/run-log.jsonl divided by
the number of decision-log entries. If this stays ~0 across sprints the log is
dead text and the write-back should be removed — a HUMAN decision (R2-Q8), never
automatic. This script only reports the rate.

Zero dependencies. Exit 0 clean; exit 1 with findings. `--self-test` → exit 0/1.
"""

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DECISIONS = PROJECT_ROOT / ".board" / "decisions.md"
RUN_LOG = PROJECT_ROOT / ".state" / "run-log.jsonl"

STATUSES = {"open", "promoted", "retired"}
_HEADER_RE = re.compile(r"^##\s+(DEC-\d+)\s+—\s+\[([^\]]+)\]\s+(.+?)\s+—\s+status:\s*(\S+)\s*$",
                        re.MULTILINE)


def parse_decisions(md_text):
    """Return {id: {task, status, body}} from decisions.md."""
    out = {}
    matches = list(_HEADER_RE.finditer(md_text))
    for i, m in enumerate(matches):
        did, task, _topic, status = m.group(1), m.group(2), m.group(3), m.group(4)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md_text)
        out[did] = {"task": task, "status": status, "body": md_text[start:end]}
    return out


def _field(body, name):
    m = re.search(rf"^-\s+\*\*{re.escape(name)}\*\*:\s*(.*)$", body, re.MULTILINE)
    return m.group(1).strip() if m else None


def validate(decisions):
    """Pure validation. Returns findings list."""
    findings = []
    for did, d in decisions.items():
        if d["status"] not in STATUSES:
            findings.append(f"{did}: status {d['status']!r} not in {sorted(STATUSES)}")
        if not d["task"].strip():
            findings.append(f"{did}: empty task reference (orphan)")
        constraints = _field(d["body"], "Constraints")
        if not constraints or constraints in ("", "--"):
            findings.append(f"{did}: missing Constraints/rationale — a bare verdict is not allowed (ADR-0017)")
        promoted_to = _field(d["body"], "Promoted-to")
        if d["status"] == "promoted" and (not promoted_to or promoted_to == "--"):
            findings.append(f"{did}: status promoted but no Promoted-to target (orphan promotion)")
    return findings


def read_back_rate(decisions, run_log_text):
    consulted = 0
    for line in run_log_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            if json.loads(line).get("event") == "answerer-consulted":
                consulted += 1
        except Exception:
            continue
    n = len(decisions)
    return consulted, n, (consulted / n if n else 0.0)


def _self_test():
    failures = []

    def expect(name, decisions, needle):
        found = validate(decisions)
        if not any(needle in f for f in found):
            failures.append(f"self-test '{name}': expected finding ~{needle!r}, got {found}")

    good = {"DEC-001": {"task": "RFN-004", "status": "open",
                        "body": "- **Question**: q\n- **Decision**: d\n- **Constraints**: because X under Y\n- **Promoted-to**: --"}}
    if validate(good):
        failures.append(f"clean baseline unexpectedly failed: {validate(good)}")

    expect("bad-status", {"DEC-1": {"task": "T", "status": "maybe",
            "body": "- **Constraints**: r"}}, "not in")
    expect("orphan-task", {"DEC-1": {"task": "  ", "status": "open",
            "body": "- **Constraints**: r"}}, "empty task")
    expect("bare-verdict", {"DEC-1": {"task": "T", "status": "open",
            "body": "- **Question**: q\n- **Decision**: yes"}}, "bare verdict")
    expect("promoted-no-target", {"DEC-1": {"task": "T", "status": "promoted",
            "body": "- **Constraints**: r\n- **Promoted-to**: --"}}, "no Promoted-to")

    # read-back metric sanity
    _, n, rate = read_back_rate(good, '{"event":"answerer-consulted"}\n{"event":"deny"}\n')
    if n != 1 or rate != 1.0:
        failures.append(f"read-back metric wrong: n={n} rate={rate}")

    if failures:
        print("validate_decisions --self-test: FAIL")
        for f in failures:
            print("  -", f)
        return 1
    print("validate_decisions --self-test: clean (4 seeded corpora caught + read-back metric OK)")
    return 0


def main(argv):
    if "--self-test" in argv:
        return _self_test()
    if not DECISIONS.is_file():
        print("validate_decisions: no .board/decisions.md — clean skip (per-project runtime state)")
        return 0
    decisions = parse_decisions(DECISIONS.read_text(encoding="utf-8"))
    findings = validate(decisions)
    run_log_text = RUN_LOG.read_text(encoding="utf-8") if RUN_LOG.is_file() else ""
    consulted, n, rate = read_back_rate(decisions, run_log_text)
    if findings:
        print("validate_decisions: FAIL")
        for f in findings:
            print("  -", f)
        return 1
    print(f"validate_decisions: clean — {n} entries, no orphans; "
          f"read-back {consulted}/{n} = {rate:.0%} (surfaced metric; human owns the kill decision)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
