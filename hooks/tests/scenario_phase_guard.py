#!/usr/bin/env python3
"""Scenario tests for phase_guard.py. Run with any python3; exit 0 iff all pass.

    python3 hooks/tests/scenario_phase_guard.py

Named scenario_* deliberately (AUD-010): the old test_* names made
`pytest hooks/tests/` collect ZERO tests and exit green — a green-but-empty
trap for any CI author. These are self-contained runners, not pytest suites.
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

        set_state("IDLE")
        cases.append(("IDLE: allow capiva-blueprints (project blueprint config)",
                      run_guard(root, "Write", {"file_path": str(root / "capiva-blueprints" / "x" / "reference.md")})[0] is False))

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

        # fast lane (ADR-0010): SPEC_PLAN behaves like PLAN; VERIFY_FINISH
        # combines TEST_VERIFY (test writes) + FINISH (gated pr create)
        set_state("SPEC_PLAN")
        cases.append(("SPEC_PLAN: deny src edit", run_guard(root, "Edit", {"file_path": src})[0] is True))
        cases.append(("SPEC_PLAN: allow PLAN.md", run_guard(root, "Write", {"file_path": str(root / "PLAN.md")})[0] is False))
        cases.append(("SPEC_PLAN: deny gh pr create", run_guard(root, "Bash", {"command": "gh pr create"})[0] is True))

        set_state("VERIFY_FINISH", "--")
        cases.append(("VERIFY_FINISH: allow test edit", run_guard(root, "Edit", {"file_path": test})[0] is False))
        cases.append(("VERIFY_FINISH: deny src edit", run_guard(root, "Edit", {"file_path": src})[0] is True))
        cases.append(("VERIFY_FINISH+no-gate: deny gh pr create", run_guard(root, "Bash", {"command": "gh pr create"})[0] is True))

        set_state("VERIFY_FINISH", "PASS")
        cases.append(("VERIFY_FINISH+PASS: allow gh pr create", run_guard(root, "Bash", {"command": "gh pr create --fill"})[0] is False))

        set_state("FINISH", "PASS")
        cases.append(("FINISH+PASS: allow gh pr create", run_guard(root, "Bash", {"command": "gh pr create --fill"})[0] is False))
        cases.append(("FINISH+PASS: allow src? no — deny", run_guard(root, "Edit", {"file_path": src})[0] is True))

        set_state("FINISH", "--")
        cases.append(("FINISH+no-gate: deny gh pr create", run_guard(root, "Bash", {"command": "gh pr create"})[0] is True))

        set_state("FINISH", "ACCEPTED_SOFT_FAIL")
        cases.append(("FINISH+SOFT_FAIL: allow gh pr create", run_guard(root, "Bash", {"command": "gh pr create"})[0] is False))

        # merge verbs (AUD-004 / ADR-0014 never-list item 1): denied in EVERY
        # phase — even at FINISH+PASS, the most PR-permissive state
        set_state("FINISH", "PASS")
        cases.append(("FINISH+PASS: deny gh pr merge", run_guard(root, "Bash", {"command": "gh pr merge 5 --squash"})[0] is True))
        cases.append(("FINISH+PASS: deny gh pr merge --auto", run_guard(root, "PowerShell", {"command": "gh pr merge --auto --rebase"})[0] is True))
        cases.append(("FINISH+PASS: deny push to main", run_guard(root, "Bash", {"command": "git push origin main"})[0] is True))
        cases.append(("FINISH+PASS: deny force-push to master", run_guard(root, "Bash", {"command": "git push -f origin master"})[0] is True))
        cases.append(("FINISH+PASS: deny refspec push HEAD:main", run_guard(root, "Bash", {"command": "git push origin HEAD:main"})[0] is True))
        cases.append(("FINISH+PASS: deny push -u origin main", run_guard(root, "Bash", {"command": "git push -u origin main"})[0] is True))
        cases.append(("FINISH+PASS: deny push --delete main", run_guard(root, "Bash", {"command": "git push origin --delete main"})[0] is True))
        cases.append(("FINISH+PASS: deny push --all", run_guard(root, "Bash", {"command": "git push --all origin"})[0] is True))
        cases.append(("FINISH+PASS: deny compound push to main", run_guard(root, "Bash", {"command": "git add -A && git commit -m x && git push origin main"})[0] is True))
        cases.append(("FINISH+PASS: allow push feature branch", run_guard(root, "Bash", {"command": "git push -u origin fix/manifest-install"})[0] is False))
        cases.append(("FINISH+PASS: allow refspec dst != default", run_guard(root, "Bash", {"command": "git push origin main:backup-main"})[0] is False))
        cases.append(("FINISH+PASS: allow branch containing 'main'", run_guard(root, "Bash", {"command": "git push origin feature/main-menu"})[0] is False))
        set_state("IMPLEMENT")
        cases.append(("IMPLEMENT: deny gh pr merge (never-phase)", run_guard(root, "Bash", {"command": "gh pr merge"})[0] is True))
        cases.append(("IMPLEMENT: deny push to main (never-phase)", run_guard(root, "Bash", {"command": "git push origin main"})[0] is True))
        cases.append(("IMPLEMENT: allow bare git push (documented limit)", run_guard(root, "Bash", {"command": "git push"})[0] is False))

        # approval-policy protection (LOOP-006 / ADR-0014): denied in EVERY phase
        policy = str(root / ".board" / "approval-policy.md")
        set_state("IDLE")
        cases.append(("IDLE: deny approval-policy write", run_guard(root, "Write", {"file_path": policy})[0] is True))
        set_state("IMPLEMENT")
        cases.append(("IMPLEMENT: deny approval-policy write (self-licensing)", run_guard(root, "Edit", {"file_path": policy})[0] is True))
        cases.append(("IMPLEMENT: other board writes still allowed", run_guard(root, "Write", {"file_path": str(root / ".board" / "tasks.md")})[0] is False))

        # kill-switch marker protection (AUD-003 / ADR-0014): the guard's own
        # off-switch is agent-unwritable in EVERY phase — .state general
        # writability must not bypass it
        marker = str(root / ".state" / "phase-guard-off")
        set_state("IDLE")
        cases.append(("IDLE: deny kill-switch marker write", run_guard(root, "Write", {"file_path": marker})[0] is True))
        set_state("GRILL_SPEC")
        cases.append(("GRILL_SPEC: deny kill-switch marker write", run_guard(root, "Edit", {"file_path": marker})[0] is True))
        set_state("IMPLEMENT")
        cases.append(("IMPLEMENT: deny kill-switch marker write (self-licensing)", run_guard(root, "Write", {"file_path": marker})[0] is True))
        cases.append(("IMPLEMENT: other .state writes still allowed", run_guard(root, "Write", {"file_path": str(root / ".state" / "session-state.md")})[0] is False))
        set_state("FINISH", "PASS")
        cases.append(("FINISH+PASS: deny kill-switch marker write", run_guard(root, "Write", {"file_path": marker})[0] is True))

        # shell write parity (AUD-005): a Bash write to X is denied iff Write
        # to X would be — same decision function, both routes
        set_state("GRILL_SPEC")
        cases.append(("GRILL_SPEC: deny redirect into src", run_guard(root, "Bash", {"command": "cat > src/service.py <<EOF\nx = 1\nEOF"})[0] is True))
        cases.append(("GRILL_SPEC: deny append redirect into src", run_guard(root, "Bash", {"command": "echo x >> src/service.py"})[0] is True))
        cases.append(("GRILL_SPEC: deny tee into src", run_guard(root, "Bash", {"command": "echo y | tee src/service.py"})[0] is True))
        cases.append(("GRILL_SPEC: deny sed -i on src", run_guard(root, "Bash", {"command": "sed -i 's/a/b/' src/service.py"})[0] is True))
        cases.append(("GRILL_SPEC: deny MultiEdit on src", run_guard(root, "MultiEdit", {"file_path": src})[0] is True))
        cases.append(("GRILL_SPEC: allow redirect into .board (parity)", run_guard(root, "Bash", {"command": "echo note >> .board/notes.md"})[0] is False))
        cases.append(("GRILL_SPEC: allow quoted '>' prose (no false deny)", run_guard(root, "Bash", {"command": "git commit -m \"bump 1.1.0 -> 1.1.1 and a > b\""})[0] is False))
        cases.append(("GRILL_SPEC: allow heredoc body with '>' prose", run_guard(root, "Bash", {"command": "git commit -m \"$(cat <<'EOF'\nfix: 1.1.0 -> 1.1.1\nEOF\n)\""})[0] is False))
        cases.append(("GRILL_SPEC: allow redirect to /dev/null (outside project)", run_guard(root, "Bash", {"command": "pytest -q > /dev/null"})[0] is False))
        cases.append(("GRILL_SPEC: allow $VAR target (unresolvable = fail-open)", run_guard(root, "Bash", {"command": "pytest > $LOGFILE"})[0] is False))
        set_state("IMPLEMENT")
        cases.append(("IMPLEMENT: allow redirect into src (parity)", run_guard(root, "Bash", {"command": "cat > src/service.py <<EOF\nx = 1\nEOF"})[0] is False))
        cases.append(("IMPLEMENT: allow MultiEdit on src (parity)", run_guard(root, "MultiEdit", {"file_path": src})[0] is False))
        cases.append(("IMPLEMENT: deny touch kill-switch via shell", run_guard(root, "Bash", {"command": "touch .state/phase-guard-off"})[0] is True))
        cases.append(("IMPLEMENT: deny append to approval-policy via shell", run_guard(root, "Bash", {"command": "echo '- **Auto-Approve Quality Gate**: yes' >> .board/approval-policy.md"})[0] is True))
        cases.append(("IMPLEMENT: deny sed -i on approval-policy via shell", run_guard(root, "Bash", {"command": "sed -i 's/no/yes/' .board/approval-policy.md"})[0] is True))
        set_state("TEST_VERIFY")
        cases.append(("TEST_VERIFY: allow redirect into tests (parity)", run_guard(root, "Bash", {"command": "echo t > tests/test_new.py"})[0] is False))
        cases.append(("TEST_VERIFY: deny redirect into src (parity)", run_guard(root, "Bash", {"command": "echo s > src/service.py"})[0] is True))

        # conflict markers in sprint-state: LOUD fail-open, never first-match
        (root / ".board" / "sprint-state.md").write_text(
            "# Sprint State\n<<<<<<< HEAD\n- **Phase**: IMPLEMENT\n=======\n"
            "- **Phase**: GRILL_SPEC\n>>>>>>> theirs\n- **Quality Gate**: --\n",
            encoding="utf-8")
        denied, rc, err = run_guard(root, "Edit", {"file_path": src})
        cases.append(("conflicted state: fail-open allow", denied is False and rc == 0))
        cases.append(("conflicted state: loud conflict warning", "merge-conflict" in err and "RESOLVE" in err))

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
