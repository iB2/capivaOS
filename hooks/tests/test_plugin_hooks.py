#!/usr/bin/env python3
"""Scenario tests for the plugin hook layer (CAP-002): run-hook.cmd dispatcher,
session_context.py injection, context-persistence no-op guard, hooks.json shape.

    python3 hooks/tests/test_plugin_hooks.py
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = HOOKS_DIR.parent
IS_WINDOWS = os.name == "nt"


def run_dispatcher(script_base, args, stdin="", project_dir=None, plugin_root=None):
    """Invoke run-hook.cmd the way Claude Code would on this platform."""
    cmd_file = str(HOOKS_DIR / "run-hook.cmd")
    if IS_WINDOWS:
        cmd = ["cmd", "/c", cmd_file, script_base] + args
    else:
        cmd = ["sh", cmd_file, script_base] + args
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(project_dir or PLUGIN_ROOT)
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root or PLUGIN_ROOT)
    r = subprocess.run(cmd, input=stdin, capture_output=True, text=True, env=env, timeout=20)
    return r.returncode, r.stdout, r.stderr


def run_script(script, args, stdin="", project_dir=None, plugin_root=None):
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(project_dir or PLUGIN_ROOT)
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root or PLUGIN_ROOT)
    r = subprocess.run([sys.executable, str(HOOKS_DIR / script)] + args,
                       input=stdin, capture_output=True, text=True, env=env, timeout=20)
    return r.returncode, r.stdout, r.stderr


def make_harness_project(root: Path, phase="IDLE", schema_version=None):
    (root / ".board").mkdir(parents=True, exist_ok=True)
    (root / ".board" / "sprint-state.md").write_text(
        "# Sprint State\n\n## Current Task\n\n"
        f"- **Task ID**: TST-9\n- **Task Title**: test task\n- **Phase**: {phase}\n"
        "- **Quality Gate**: --\n\n## Phase History\n", encoding="utf-8")
    if schema_version:
        (root / ".board" / "harness-schema-version").write_text(schema_version, encoding="utf-8")


def main():
    cases = []

    with tempfile.TemporaryDirectory() as td:
        empty_project = Path(td) / "empty"
        empty_project.mkdir()
        harness_project = Path(td) / "harness"
        make_harness_project(harness_project)

        # --- hooks.json shape (AC1) ---
        hooks_json = json.loads((HOOKS_DIR / "hooks.json").read_text(encoding="utf-8"))
        h = hooks_json["hooks"]
        cases.append(("hooks.json: has all four events",
                      all(k in h for k in ("PreToolUse", "PreCompact", "SessionStart", "Stop"))))
        all_cmds = [hk["command"] for group in h.values() for entry in group for hk in entry["hooks"]]
        cases.append(("hooks.json: every command goes through quoted dispatcher",
                      all('"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd"' in c for c in all_cmds)))
        ss_matchers = [e.get("matcher", "") for e in h["SessionStart"]]
        cases.append(("hooks.json: session_context registered for startup|clear|compact",
                      any("startup" in m and "clear" in m and "compact" in m for m in ss_matchers)))
        pre = [e.get("matcher", "") for e in h["PreToolUse"]]
        cases.append(("hooks.json: phase guard covers write + shell tools",
                      any("Edit" in m for m in pre) and any("Bash" in m for m in pre)))

        # --- dispatcher file invariant: mixed line endings by construction ---
        # cmd.exe needs CRLF for the batch block (LF-only char-shifts lines);
        # sh needs the heredoc terminator + POSIX section CR-free. A normalizing
        # editor or gitattributes change breaks one OS silently — assert bytes.
        raw = (HOOKS_DIR / "run-hook.cmd").read_bytes()
        CR, LF = b"\r", b"\n"
        cases.append(("dispatcher file: line 1 ends LF-only (dash glues CR onto the heredoc delimiter)",
                      raw.startswith(b": <<'CMDBLOCK'" + LF)))
        cases.append(("dispatcher file: batch block is CRLF",
                      b"@echo off" + CR + LF in raw))
        cases.append(("dispatcher file: batch block is ASCII-only",
                      max(raw.split(b"CMDBLOCK")[1]) < 128))
        cases.append(("dispatcher file: heredoc terminator is LF-only",
                      LF + b"CMDBLOCK" + LF in raw and b"CMDBLOCK" + CR not in raw))
        cases.append(("dispatcher file: POSIX section is CR-free",
                      CR not in raw.split(b"CMDBLOCK", 2)[-1]))

        # --- dispatcher (AC2) ---
        rc, out, _ = run_dispatcher("phase_guard", [], stdin=json.dumps(
            {"tool_name": "Edit", "tool_input": {"file_path": str(harness_project / "src" / "x.py")}}),
            project_dir=harness_project)
        cases.append(("dispatcher: stdin/stdout flow through (guard denies at IDLE)",
                      rc == 0 and '"deny"' in out))
        rc, out, err = run_dispatcher("no_such_hook_script", [], project_dir=harness_project)
        cases.append(("dispatcher: missing script -> exit 0, silent", rc == 0 and out.strip() == ""))
        rc, _, _ = run_dispatcher("context-persistence", ["stop"], project_dir=empty_project)
        cases.append(("dispatcher: forwards args (context-persistence stop, no-op project)", rc == 0))

        # --- context-persistence no-op guard (AC3) ---
        rc, out, _ = run_script("context-persistence.py", ["stop"], project_dir=empty_project)
        cases.append(("context-persistence: no .board -> exit 0, no output", rc == 0 and out.strip() == ""))
        cases.append(("context-persistence: no .board -> writes nothing",
                      not (empty_project / ".state").exists()))
        rc, _, _ = run_script("context-persistence.py", ["stop"], project_dir=harness_project)
        cases.append(("context-persistence: harness project -> still saves state",
                      rc == 0 and (harness_project / ".state" / "session-state.md").is_file()))

        # --- session_context (AC3 + AC4) ---
        rc, out, _ = run_script("session_context.py", [], stdin='{"source":"startup"}',
                                project_dir=empty_project)
        cases.append(("session_context: no .board -> exit 0, no output", rc == 0 and out.strip() == ""))

        rc, out, _ = run_script("session_context.py", [], stdin='{"source":"startup"}',
                                project_dir=harness_project)
        ok = False
        ctx = ""
        if rc == 0 and out.strip():
            payload = json.loads(out)
            ctx = payload["hookSpecificOutput"]["additionalContext"]
            ok = (payload["hookSpecificOutput"]["hookEventName"] == "SessionStart"
                  and "Law 1" in ctx and "TST-9" in ctx)
        cases.append(("session_context: startup -> laws + current task injected", ok))
        cases.append(("session_context: unstamped project -> no update nudge",
                      ok and "update-project" not in ctx))

        rc, out, _ = run_script("session_context.py", [], stdin='{"source":"compact"}',
                                project_dir=harness_project)
        compact_ok = False
        if rc == 0 and out.strip():
            ctx2 = json.loads(out)["hookSpecificOutput"]["additionalContext"]
            compact_ok = "Law 1" not in ctx2 and "credo" in ctx2.lower() and "TST-9" in ctx2
        cases.append(("session_context: compact -> credo reminder only, no full laws", compact_ok))

        # version skew nudge (AC4)
        skew_project = Path(td) / "skew"
        make_harness_project(skew_project, schema_version="0.1.0")
        rc, out, _ = run_script("session_context.py", [], stdin='{"source":"startup"}',
                                project_dir=skew_project)
        skew_ok = rc == 0 and out.strip() and "update-project" in \
            json.loads(out)["hookSpecificOutput"]["additionalContext"]
        cases.append(("session_context: schema-version skew -> update-project nudge", bool(skew_ok)))

        # fail-open: unreadable laws (point plugin root somewhere empty)
        rc, out, _ = run_script("session_context.py", [], stdin='{"source":"startup"}',
                                project_dir=harness_project, plugin_root=empty_project)
        lawsless_ok = rc == 0
        if out.strip():
            lawsless_ok = lawsless_ok and "TST-9" in json.loads(out)["hookSpecificOutput"]["additionalContext"]
        cases.append(("session_context: missing laws.md -> fail-open, still exits 0", lawsless_ok))

        # garbage stdin never crashes
        rc, _, _ = run_script("session_context.py", [], stdin="not json", project_dir=harness_project)
        cases.append(("session_context: garbage stdin -> exit 0", rc == 0))

    failed = [name for name, ok in cases if not ok]
    for name, ok in cases:
        print(("PASS" if ok else "FAIL"), name)
    print(f"\n{len(cases) - len(failed)}/{len(cases)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
