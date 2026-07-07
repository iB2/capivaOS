#!/usr/bin/env python3
"""Scenario tests for phase_guard.py. Run with any python3; exit 0 iff all pass.

    python3 .claude/hooks/tests/test_phase_guard.py
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

GUARD = Path(__file__).resolve().parent.parent / "phase_guard.py"

STATE_TEMPLATE = """# Sprint State
## Current Task
- **Task ID**: TST-1
- **Phase**: {phase}
- **Quality Gate**: {gate}
"""


def run_guard(project_dir, tool_name, tool_input, extra_env=None):
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    env.pop("CAPIVA_PHASE_GUARD", None)
    if extra_env:
        env.update(extra_env)
    payload = json.dumps({"tool_name": tool_name, "tool_input": tool_input})
    r = subprocess.run(
        [sys.executable, str(GUARD)],
        input=payload, capture_output=True, text=True, env=env, timeout=15,
    )
    denied = False
    if r.stdout.strip():
        try:
            out = json.loads(r.stdout)
            denied = out.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"
        except json.JSONDecodeError:
            pass
    return denied, r.returncode, r.stderr


def main():
    results = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / ".board").mkdir()

        def set_state(phase, gate="--"):
            (root / ".board" / "sprint-state.md").write_text(
                STATE_TEMPLATE.format(phase=phase, gate=gate), encoding="utf-8")

        src = str(root / "src" / "service.py")
        test = str(root / "tests" / "test_service.py")
        doc = str(root / "docs" / "specs" / "TST-1-spec.md")

        cases = []

        set_state("IDLE")
        cases.append(("IDLE: deny src edit", run_guard(root, "Edit", {"file_path": src})[0] is True))
        cases.append(("IDLE: allow docs edit", run_guard(root, "Write", {"file_path": doc})[0] is False))
        cases.append(("IDLE: allow PLAN.md", run_guard(root, "Write", {"file_path": str(root / "PLAN.md")})[0] is False))
        cases.append(("IDLE: allow scripts/ tooling", run_guard(root, "Write", {"file_path": str(root / "scripts" / "lint.py")})[0] is False))
        cases.append(("IDLE: allow .github/ CI config", run_guard(root, "Write", {"file_path": str(root / ".github" / "workflows" / "ci.yml")})[0] is False))
        cases.append(("IDLE: deny gh pr create", run_guard(root, "Bash", {"command": "gh pr create --title t"})[0] is True))
        cases.append(("IDLE: allow other bash", run_guard(root, "Bash", {"command": "git status"})[0] is False))

        set_state("GRILL_SPEC")
        cases.append(("GRILL_SPEC: deny src edit", run_guard(root, "Edit", {"file_path": src})[0] is True))

        set_state("IMPLEMENT")
        cases.append(("IMPLEMENT: allow src edit", run_guard(root, "Edit", {"file_path": src})[0] is False))
        cases.append(("IMPLEMENT: allow test edit", run_guard(root, "Write", {"file_path": test})[0] is False))
        cases.append(("IMPLEMENT: deny gh pr create", run_guard(root, "PowerShell", {"command": "gh pr create -t x"})[0] is True))

        set_state("TEST_VERIFY")
        cases.append(("TEST_VERIFY: allow test edit", run_guard(root, "Edit", {"file_path": test})[0] is False))
        cases.append(("TEST_VERIFY: allow x.spec.ts", run_guard(root, "Edit", {"file_path": str(root / "src" / "auth.spec.ts")})[0] is False))
        cases.append(("TEST_VERIFY: deny src edit", run_guard(root, "Edit", {"file_path": src})[0] is True))

        set_state("FINISH", "PASS")
        cases.append(("FINISH+PASS: allow gh pr create", run_guard(root, "Bash", {"command": "gh pr create --fill"})[0] is False))
        cases.append(("FINISH+PASS: allow src? no — deny", run_guard(root, "Edit", {"file_path": src})[0] is True))

        set_state("FINISH", "--")
        cases.append(("FINISH+no-gate: deny gh pr create", run_guard(root, "Bash", {"command": "gh pr create"})[0] is True))

        set_state("FINISH", "ACCEPTED_SOFT_FAIL")
        cases.append(("FINISH+SOFT_FAIL: allow gh pr create", run_guard(root, "Bash", {"command": "gh pr create"})[0] is False))

        # fail-open: missing state file
        (root / ".board" / "sprint-state.md").unlink()
        denied, rc, err = run_guard(root, "Edit", {"file_path": src})
        cases.append(("missing state: fail-open allow", denied is False and rc == 0))
        cases.append(("missing state: warns on stderr", "failing open" in err))

        # escape hatch (env)
        set_state("IDLE")
        denied, _, err = run_guard(root, "Edit", {"file_path": src}, {"CAPIVA_PHASE_GUARD": "off"})
        cases.append(("escape hatch env: allow + logged", denied is False and "disabled" in err))

        # escape hatch (marker file — works when env can't reach the hook process)
        (root / ".state").mkdir(exist_ok=True)
        (root / ".state" / "phase-guard-off").write_text("", encoding="utf-8")
        denied, _, err = run_guard(root, "Edit", {"file_path": src})
        cases.append(("escape hatch marker: allow + logged", denied is False and "marker" in err))
        (root / ".state" / "phase-guard-off").unlink()
        cases.append(("marker removed: deny again", run_guard(root, "Edit", {"file_path": src})[0] is True))

        # outside project root
        set_state("IDLE")
        outside = str(Path(tempfile.gettempdir()) / "scratch-note.py")
        cases.append(("IDLE: allow path outside project", run_guard(root, "Edit", {"file_path": outside})[0] is False))

        # garbage stdin never blocks
        env = dict(os.environ); env["CLAUDE_PROJECT_DIR"] = str(root)
        r = subprocess.run([sys.executable, str(GUARD)], input="not json", capture_output=True, text=True, env=env)
        cases.append(("garbage stdin: exit 0, no deny", r.returncode == 0 and "deny" not in r.stdout))

        results = cases

    failed = [name for name, ok in results if not ok]
    for name, ok in results:
        print(("PASS" if ok else "FAIL"), name)
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
