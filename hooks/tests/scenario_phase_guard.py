#!/usr/bin/env python3
"""Scenario tests for phase_guard.py. Run with any python3; exit 0 iff all pass.

    python3 hooks/tests/scenario_phase_guard.py

Named scenario_* deliberately: the old test_* names made
`pytest hooks/tests/` collect ZERO tests and exit green — a green-but-empty
trap for any CI author. These are self-contained runners, not pytest suites.
"""
import json
import os
import re
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
        # PRD-002: scripts/ and .github/ are NO LONGER always-allowed — they
        # are source (writable only in IMPLEMENT). Self-licensing routes closed.
        cases.append(("IDLE: deny scripts/ write (was self-licensing)", run_guard(root, "Write", {"file_path": str(root / "scripts" / "lint.py")})[0] is True))
        cases.append(("IDLE: deny .github/ CI write (arbitrary code on push)", run_guard(root, "Write", {"file_path": str(root / ".github" / "workflows" / "ci.yml")})[0] is True))
        cases.append(("IMPLEMENT: allow scripts/ write (legit per-task)", (lambda: (set_state("IMPLEMENT"), run_guard(root, "Write", {"file_path": str(root / "scripts" / "lint.py")})[0] is False)[1])()))
        set_state("IDLE")
        cases.append(("IDLE: deny .claude/settings.json (hook dereg)", run_guard(root, "Write", {"file_path": str(root / ".claude" / "settings.json")})[0] is True))
        cases.append(("IMPLEMENT: deny .claude/settings.json (human-only)", (lambda: (set_state("IMPLEMENT"), run_guard(root, "Write", {"file_path": str(root / ".claude" / "settings.json")})[0] is True)[1])()))
        cases.append(("IMPLEMENT: deny root CLAUDE.md (instruction injection)", run_guard(root, "Write", {"file_path": str(root / "CLAUDE.md")})[0] is True))
        set_state("IDLE")
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

        # merge verbs (ADR-0014 never-list item 1): denied in EVERY
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

        # approval-policy protection (ADR-0014): denied in EVERY phase
        policy = str(root / ".board" / "approval-policy.md")
        set_state("IDLE")
        cases.append(("IDLE: deny approval-policy write", run_guard(root, "Write", {"file_path": policy})[0] is True))
        set_state("IMPLEMENT")
        cases.append(("IMPLEMENT: deny approval-policy write (self-licensing)", run_guard(root, "Edit", {"file_path": policy})[0] is True))
        cases.append(("IMPLEMENT: other board writes still allowed", run_guard(root, "Write", {"file_path": str(root / ".board" / "tasks.md")})[0] is False))

        # kill-switch marker protection (ADR-0014): the guard's own
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

        # shell write parity: a Bash write to X is denied iff Write
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

        # claims-parity meta: ENFORCED_SURFACES is the source of
        # truth harness_lint locks the docs to — if this tuple changes, the
        # deny logic, the scenarios above, and both doc tables change with it
        guard_src = GUARD.read_text(encoding="utf-8")
        m = re.search(r"ENFORCED_SURFACES\s*=\s*\(([^)]*)\)", guard_src)
        declared = set(re.findall(r'"([^"]+)"', m.group(1))) if m else set()
        cases.append(("ENFORCED_SURFACES declares exactly the 6 deny classes",
                      declared == {"source-writes-outside-implement", "pr-create-gate",
                                   "human-only-files", "merge-verbs",
                                   "sprint-state-transitions", "board-lock"}))

        # enforcement heartbeat (PRD-001): every enforced invocation drops
        # a proof-of-life marker session_context / auto mode can check
        set_state("IMPLEMENT")
        hb = root / ".state" / "guard-heartbeat"
        if hb.exists():
            hb.unlink()
        run_guard(root, "Edit", {"file_path": src})
        cases.append(("heartbeat: dropped on enforced invocation",
                      hb.is_file() and "phase=IMPLEMENT" in hb.read_text(encoding="utf-8")))

        # ---- PRD-003: sprint-state transition validation ----
        ss_path = str(root / ".board" / "sprint-state.md")

        def ss(phase, gate="--", task="TST-1"):
            return (f"# Sprint State\n## Current Task\n- **Task ID**: {task}\n"
                    f"- **Phase**: {phase}\n- **Quality Gate**: {gate}\n")

        def write_state(tool="Write", **ti):
            return run_guard(root, tool, ti)

        set_state("IDLE")
        cases.append(("transition: IDLE->IMPLEMENT illegal jump denied",
                      write_state(file_path=ss_path, content=ss("IMPLEMENT"))[0] is True))
        cases.append(("transition: IDLE->TRIAGE legal allowed",
                      write_state(file_path=ss_path, content=ss("TRIAGE"))[0] is False))
        cases.append(("transition: same-phase field update allowed",
                      write_state(file_path=ss_path, content=ss("IDLE"))[0] is False))
        cases.append(("transition: IDLE->BLOCKED allowed (escalate)",
                      write_state(file_path=ss_path, content=ss("BLOCKED"))[0] is False))

        # artifact precondition: PLAN->IMPLEMENT needs PLAN.md + acs.json
        (root / ".board" / "sprint-state.md").write_text(ss("PLAN"), encoding="utf-8")
        cases.append(("transition: PLAN->IMPLEMENT without artifacts denied",
                      write_state(file_path=ss_path, content=ss("IMPLEMENT"))[0] is True))
        (root / "PLAN.md").write_text("plan", encoding="utf-8")
        (root / "docs" / "specs").mkdir(parents=True, exist_ok=True)
        (root / "docs" / "specs" / "TST-1-acs.json").write_text("{}", encoding="utf-8")
        cases.append(("transition: PLAN->IMPLEMENT with artifacts allowed",
                      write_state(file_path=ss_path, content=ss("IMPLEMENT"))[0] is False))

        # phase blanking during an active task -> denied
        (root / ".board" / "sprint-state.md").write_text(ss("IMPLEMENT"), encoding="utf-8")
        cases.append(("transition: blanking active Phase denied",
                      write_state(file_path=ss_path, content="# Sprint State\n- **Phase**: \n")[0] is True))

        # forged Quality Gate PASS without a report -> denied; with report -> allowed
        (root / ".board" / "sprint-state.md").write_text(ss("TEST_VERIFY"), encoding="utf-8")
        cases.append(("transition: forged Gate=PASS without report denied",
                      write_state(file_path=ss_path, content=ss("TEST_VERIFY", "PASS"))[0] is True))
        (root / "docs" / "reports").mkdir(parents=True, exist_ok=True)
        (root / "docs" / "reports" / "TST-1-quality.md").write_text("q", encoding="utf-8")
        cases.append(("transition: Gate=PASS with report on disk allowed",
                      write_state(file_path=ss_path, content=ss("TEST_VERIFY", "PASS"))[0] is False))

        # Edit-tool reconstruction: an illegal Phase edit is caught
        (root / ".board" / "sprint-state.md").write_text(ss("IDLE"), encoding="utf-8")
        cases.append(("transition: Edit IDLE->FINISH illegal denied",
                      write_state(tool="Edit", file_path=ss_path,
                                  old_string="- **Phase**: IDLE",
                                  new_string="- **Phase**: FINISH")[0] is True))

        # ---- PRD-003: mechanical board lock ----
        lock = root / ".board" / "board.lock"
        holder = root / ".state" / "lock-holder"
        holder.parent.mkdir(parents=True, exist_ok=True)
        (root / ".board" / "sprint-state.md").write_text(ss("IMPLEMENT"), encoding="utf-8")
        import time as _t
        fresh = f"holder=other-999\nepoch={_t.time():.3f}\n"
        lock.write_text(fresh, encoding="utf-8")
        holder.write_text("me-111", encoding="utf-8")
        cases.append(("lock: foreign fresh lock denies board write",
                      write_state(file_path=str(root / ".board" / "tasks.md"), content="x")[0] is True))
        holder.write_text("other-999", encoding="utf-8")
        cases.append(("lock: own lock allows board write",
                      write_state(file_path=str(root / ".board" / "tasks.md"), content="x")[0] is False))
        lock.write_text(f"holder=other-999\nepoch={_t.time()-9999:.3f}\n", encoding="utf-8")
        holder.write_text("me-111", encoding="utf-8")
        cases.append(("lock: stale foreign lock ignored",
                      write_state(file_path=str(root / ".board" / "tasks.md"), content="x")[0] is False))
        lock.unlink()
        cases.append(("lock: no lock allows board write",
                      write_state(file_path=str(root / ".board" / "tasks.md"), content="x")[0] is False))
        holder.unlink()
        # reset a clean IMPLEMENT state for any trailing cases
        set_state("IMPLEMENT")

        # PRD-004: mechanical run-log (hook-written, append-only)
        set_state("IDLE")
        rl = root / ".state" / "run-log.jsonl"
        if rl.exists():
            rl.unlink()
        run_guard(root, "Edit", {"file_path": src})  # a deny
        run_guard(root, "Write", {"file_path": ss_path, "content": ss("TRIAGE")})  # a transition
        logged = rl.read_text(encoding="utf-8") if rl.is_file() else ""
        cases.append(("run-log: deny event recorded", '"event": "deny"' in logged))
        cases.append(("run-log: transition event recorded", '"event": "transition"' in logged and '"to": "TRIAGE"' in logged))

        # ---- PRD-008: guard-status transitions are run-logged (on CHANGE only) ----
        set_state("IDLE")
        status_file = root / ".state" / "guard-status"
        if status_file.exists():
            status_file.unlink()
        if rl.exists():
            rl.unlink()
        run_guard(root, "Edit", {"file_path": src})
        logged = rl.read_text(encoding="utf-8") if rl.is_file() else ""
        cases.append(("guard-status: first enforced call logs status change to enforcing",
                      '"event": "guard-status"' in logged and '"status": "enforcing"' in logged))
        run_guard(root, "Edit", {"file_path": src})
        logged = rl.read_text(encoding="utf-8") if rl.is_file() else ""
        cases.append(("guard-status: repeat call does NOT re-log (change-only)",
                      logged.count('"event": "guard-status"') == 1))
        marker = root / ".state" / "phase-guard-off"
        marker.write_text("", encoding="utf-8")
        denied_off, _, _ = run_guard(root, "Edit", {"file_path": src})
        logged = rl.read_text(encoding="utf-8") if rl.is_file() else ""
        cases.append(("guard-status: kill-switch marker flip logged as off-marker (and allows)",
                      denied_off is False and '"status": "off-marker"' in logged))
        marker.unlink()
        run_guard(root, "Edit", {"file_path": src})
        logged = rl.read_text(encoding="utf-8") if rl.is_file() else ""
        cases.append(("guard-status: marker removal logged as re-enforcing",
                      logged.count('"status": "enforcing"') == 2))
        denied_env, _, _ = run_guard(root, "Edit", {"file_path": src},
                                     extra_env={"CAPIVA_PHASE_GUARD": "off"})
        logged = rl.read_text(encoding="utf-8") if rl.is_file() else ""
        cases.append(("guard-status: env kill-switch logged as off-env (and allows)",
                      denied_env is False and '"status": "off-env"' in logged))

        # ---- PRD-009: quoted redirect target + fd redirect must not false-deny ----
        set_state("IDLE")
        cases.append(("shell: quoted redirect + 2>/dev/null does NOT capture neighbor token (live bug)",
                      run_guard(root, "Bash", {"command": 'git show x:f.py > "out dir/f.py" 2>/dev/null'})[0] is False))
        cases.append(("shell: unquoted redirect to source still denied with fd-dup present",
                      run_guard(root, "Bash", {"command": "echo hi > src/x.py 2>/dev/null"})[0] is True))

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
