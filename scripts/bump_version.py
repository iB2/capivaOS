#!/usr/bin/env python3
"""
bump_version.py — Release helper for the capiva plugin.

Keeps the release contract honest:
  1. .claude-plugin/plugin.json `version` is bumped (single version source —
     the marketplace entry deliberately carries no version).
  2. CHANGELOG.md must contain a `## [<new version>]` entry.
  3. If anything under project-template/ or the parsed-field formats changed
     since the last release tag, skills/update-project/SKILL.md must contain a
     migration row mentioning the new version (schema change without a
     migration is release-blocking, per update-project's rules).

Usage:
  python3 scripts/bump_version.py 1.1.0          # apply the bump
  python3 scripts/bump_version.py 1.1.0 --check  # validate only (CI / dry run)
  python3 scripts/bump_version.py --check        # validate current version's release readiness

Exit 0 on success; exit 1 with reasons otherwise.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN_JSON = ROOT / ".claude-plugin" / "plugin.json"
CHANGELOG = ROOT / "CHANGELOG.md"
MIGRATIONS = ROOT / "skills" / "update-project" / "SKILL.md"

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def fail(msgs):
    print(f"bump_version: {len(msgs)} problem(s)")
    for m in msgs:
        print(f"  ✗ {m}")
    sys.exit(1)


def last_release_tag():
    try:
        r = subprocess.run(["git", "describe", "--tags", "--abbrev=0", "--match", "v*"],
                           capture_output=True, text=True, cwd=ROOT, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def schema_changed_since(tag):
    """True if project-template/ or hook parsers changed since the tag."""
    if not tag:
        return False  # first release: schema is the baseline, no migration needed
    try:
        r = subprocess.run(["git", "diff", "--name-only", f"{tag}..HEAD", "--",
                            "project-template/", "hooks/phase_guard.py",
                            "hooks/context-persistence.py", "hooks/session_context.py"],
                           capture_output=True, text=True, cwd=ROOT, timeout=10)
        return bool(r.stdout.strip())
    except Exception:
        return True  # can't tell -> demand the migration row (safe direction)


def main():
    args = [a for a in sys.argv[1:] if a != "--check"]
    check_only = "--check" in sys.argv[1:]

    manifest = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
    current = manifest.get("version", "")
    new = args[0] if args else current

    problems = []
    if not SEMVER_RE.match(new):
        problems.append(f"version {new!r} is not X.Y.Z semver")
    if args and new == current and not check_only:
        problems.append(f"new version equals current ({current}) — nothing to bump")

    if f"## [{new}]" not in CHANGELOG.read_text(encoding="utf-8"):
        problems.append(f"CHANGELOG.md has no '## [{new}]' entry")

    tag = last_release_tag()
    if schema_changed_since(tag):
        migrations = MIGRATIONS.read_text(encoding="utf-8")
        if new not in migrations:
            problems.append(
                f"schema surface changed since {tag or 'repo start'} but "
                f"skills/update-project/SKILL.md has no migration row mentioning {new} "
                f"(schema change without migration is release-blocking)")

    if problems:
        fail(problems)

    if check_only:
        print(f"bump_version: OK — {new} is releasable "
              f"(changelog entry present, migration contract satisfied)")
        sys.exit(0)

    manifest["version"] = new
    PLUGIN_JSON.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"bump_version: {current} -> {new} written to .claude-plugin/plugin.json")
    print(f"next: commit, tag v{new}, push — users receive the update on their next "
          f"marketplace refresh / /capiva:update")
    sys.exit(0)


if __name__ == "__main__":
    main()
