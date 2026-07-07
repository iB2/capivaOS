#!/usr/bin/env python3
"""
validate_impl_report.py — Schema validator for dev-subagent completion reports.

/implement subagents end their final message with one fenced JSON completion
report (ADR-0012; schema documented in .claude/agents/dev.md). The orchestrator
runs this validator before accepting a task as complete — an invalid report is
an incomplete task.

Usage:
  python3 scripts/validate_impl_report.py report.json   # validate a file
  python3 scripts/validate_impl_report.py -             # validate stdin
  python3 scripts/validate_impl_report.py --self-test   # validator self-check

Exit 0 = valid; exit 1 = findings (printed one per line).
"""

import json
import sys

STATUSES = {"complete", "blocked"}
ACTIONS = {"CREATE", "MODIFY"}
RESULT_KEYS = {"passed", "failed", "skipped"}


def validate(data):
    findings = []

    def need_str(key):
        if not isinstance(data.get(key), str) or not data.get(key):
            findings.append(f"missing or non-string '{key}'")

    if not isinstance(data, dict):
        return ["report is not a JSON object"]

    need_str("task_id")
    need_str("task_title")
    if not isinstance(data.get("task_number"), int) or data.get("task_number") < 1:
        findings.append("'task_number' must be a positive integer")
    if data.get("status") not in STATUSES:
        findings.append(f"'status' {data.get('status')!r} not in {sorted(STATUSES)}")
    if not isinstance(data.get("attempts"), int) or data.get("attempts") < 1:
        findings.append("'attempts' must be a positive integer")

    files = data.get("files_changed")
    if not isinstance(files, list):
        findings.append("'files_changed' must be a list")
    else:
        if data.get("status") == "complete" and not files:
            findings.append("'files_changed' empty on a complete task")
        for i, f in enumerate(files):
            if not isinstance(f, dict):
                findings.append(f"files_changed[{i}] is not an object")
                continue
            if not isinstance(f.get("path"), str) or not f.get("path"):
                findings.append(f"files_changed[{i}] missing 'path'")
            if f.get("action") not in ACTIONS:
                findings.append(f"files_changed[{i}] action {f.get('action')!r} not in {sorted(ACTIONS)}")
            if not isinstance(f.get("purpose"), str) or not f.get("purpose"):
                findings.append(f"files_changed[{i}] missing 'purpose'")

    tests = data.get("tests_added")
    if not isinstance(tests, list):
        findings.append("'tests_added' must be a list")
    else:
        if data.get("status") == "complete" and not tests:
            findings.append("'tests_added' empty on a complete task (TDD: no test, no implementation)")
        for i, t in enumerate(tests):
            if not isinstance(t, dict):
                findings.append(f"tests_added[{i}] is not an object")
                continue
            for key in ("name", "file"):
                if not isinstance(t.get(key), str) or not t.get(key):
                    findings.append(f"tests_added[{i}] missing '{key}'")
            if not isinstance(t.get("acs"), list) or not all(isinstance(a, str) for a in t.get("acs") or []):
                findings.append(f"tests_added[{i}] 'acs' must be a list of AC id strings (may be empty)")

    commits = data.get("commits")
    if not isinstance(commits, list) or not all(isinstance(c, str) and c for c in (commits or [])):
        findings.append("'commits' must be a list of non-empty hash strings")
    elif data.get("status") == "complete" and len(commits) < 2:
        findings.append("'commits' has fewer than 2 entries — TDD requires test commit(s) before implementation commit(s)")

    results = data.get("test_results")
    if not isinstance(results, dict) or set(results) != RESULT_KEYS or \
            not all(isinstance(results.get(k), int) and results.get(k) >= 0 for k in RESULT_KEYS):
        findings.append(f"'test_results' must be an object with integer {sorted(RESULT_KEYS)}")
    else:
        if data.get("status") == "complete" and results["failed"] > 0:
            findings.append("status 'complete' with failing tests — a task is complete only when green")

    if not isinstance(data.get("tdd_order_confirmed"), bool):
        findings.append("'tdd_order_confirmed' must be a boolean")
    elif data.get("status") == "complete" and data.get("tdd_order_confirmed") is not True:
        findings.append("status 'complete' but tdd_order_confirmed is false — revert and respawn per TDD enforcement")

    if not isinstance(data.get("flags"), list) or not all(isinstance(x, str) for x in data.get("flags") or []):
        findings.append("'flags' must be a list of strings (may be empty)")
    if data.get("status") == "blocked" and not data.get("flags"):
        findings.append("status 'blocked' requires at least one flag explaining why")

    return findings


GOOD = {
    "task_id": "COS-42", "task_number": 1, "task_title": "expiration sweep",
    "status": "complete", "attempts": 1,
    "files_changed": [{"path": "src/svc.py", "action": "MODIFY", "purpose": "sweep logic"}],
    "tests_added": [{"name": "test_sweep_expires", "file": "tests/test_svc.py", "acs": ["AC1"]}],
    "commits": ["aaa1111", "bbb2222"],
    "test_results": {"passed": 5, "failed": 0, "skipped": 0},
    "tdd_order_confirmed": True, "flags": [],
}


def self_test():
    cases = []
    cases.append(("good report: valid", validate(dict(GOOD)) == []))

    def bad(**kw):
        d = dict(GOOD); d.update(kw); return validate(d)

    cases.append(("bad status caught", any("'status'" in f for f in bad(status="done"))))
    cases.append(("complete w/o tests caught", any("tests_added" in f for f in bad(tests_added=[]))))
    cases.append(("complete w/ failures caught", any("failing tests" in f for f in bad(test_results={"passed": 1, "failed": 2, "skipped": 0}))))
    cases.append(("single commit caught", any("fewer than 2" in f for f in bad(commits=["only1"]))))
    cases.append(("tdd_order false caught", any("tdd_order_confirmed" in f for f in bad(tdd_order_confirmed=False))))
    cases.append(("blocked w/o flags caught", any("requires at least one flag" in f
                                                  for f in bad(status="blocked", flags=[]))))
    cases.append(("bad action caught", any("action" in f for f in bad(
        files_changed=[{"path": "x", "action": "DELETE", "purpose": "y"}]))))
    cases.append(("non-object caught", validate("nope") == ["report is not a JSON object"]))

    failed = [name for name, ok in cases if not ok]
    for name, ok in cases:
        print(("PASS" if ok else "FAIL"), name)
    print(f"\n{len(cases) - len(failed)}/{len(cases)} passed")
    return not failed


def main():
    if "--self-test" in sys.argv:
        sys.exit(0 if self_test() else 1)
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    raw = sys.stdin.read() if sys.argv[1] == "-" else open(sys.argv[1], encoding="utf-8").read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"invalid JSON: {e}")
        sys.exit(1)
    findings = validate(data)
    if findings:
        print(f"validate_impl_report: {len(findings)} finding(s)")
        for f in findings:
            print(f"  ✗ {f}")
        sys.exit(1)
    print("validate_impl_report: valid")
    sys.exit(0)


if __name__ == "__main__":
    main()
