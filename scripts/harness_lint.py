#!/usr/bin/env python3
"""
harness_lint.py — Cross-reference linter + blueprint parity check for the harness.

Catches the drift class found in the 2026-07 audit (stale counts, dead skill
references, missing blueprint rows, diverged blueprint sections) mechanically,
so it can't silently recur.

Checks:
  1. Slash-command references (`/name`) in docs resolve to a skill directory
     in .claude/skills/ or a known Claude Code built-in.
  2. Repo-relative file references (docs/..., templates/..., .claude/...)
     in docs point at files that exist.
  3. DESIGN.md's ADR index and docs/adr/*.md agree in BOTH directions.
  4. Every blueprint directory is mentioned in CLAUDE.md, README.md, SCOPE.md.
  5. The three blueprint reference.md files share an IDENTICAL §-section set,
     and every §section referenced anywhere in docs exists in ALL blueprints.
  6. docs/specs/*-acs.json files (machine-readable AC lists, ADR-0009) conform
     to the schema: task/spec strings, non-empty acs list, unique ids, every
     entry has id/text, status in {pending, pass, fail}.

Usage:
  python3 scripts/harness_lint.py              # lint the repo; exit 1 on findings
  python3 scripts/harness_lint.py --self-test  # verify the linter catches seeded drift

Scanned files: README.md, .claude/CLAUDE.md, .claude/rules/*.md,
.claude/skills/*/SKILL.md, .claude/agents/roles/*.md, docs/DESIGN.md,
docs/SCOPE.md, templates/*.md. Excluded: docs/audits/ (session artifacts),
docs/blueprint-migration-map.md (historical record), .board/ (mutable).
"""

import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Claude Code built-ins and common non-skill slash mentions
BUILTIN_COMMANDS = {
    "clear", "compact", "resume", "model", "config", "hooks", "help",
    "fast", "init", "memory", "review",
}

# Trailing char must be alphanumeric (no mid-backtrack "grill-" matches);
# reject file extensions (/reference.md) and path continuations (/api/v1),
# but allow sentence-final periods ("run /grill-spec.").
SLASH_RE = re.compile(r"(?<![\w./`>])/([a-z][a-z0-9-]+[a-z0-9])(?!\.\w|[-/\w])")
PATH_RE = re.compile(r"(?<![\w/])((?:docs|templates|\.claude|\.board|scripts)/[\w./-]+\.(?:md|py|json|mmd|yml))")
ADR_LINK_RE = re.compile(r"adr/(\d{4}-[\w-]+\.md)")
SECTION_HEADING_RE = re.compile(r"^##+ *(§[\w-]+)", re.MULTILINE)
SECTION_REF_RE = re.compile(r"(§[\w-]+)")
FENCE_RE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)
TASK_ID_RE = re.compile(r"[A-Z]{2,}-\d")

# Files the pipeline creates at RUNTIME in adopter projects — referenced
# normatively throughout the harness but absent from the shipped template.
RUNTIME_ARTIFACTS = {
    "docs/specs/INTAKE-summary.md",
    "docs/solution-document.md",
    "docs/CONTEXT.md",
}
PLACEHOLDER_TOKENS = ("*", "TASK-ID", "NNNN", "000N", "DEV-NNN", "<", "[", "your-", "N-slug")
ACS_STATUSES = {"pending", "pass", "fail"}


def lint_acs_file(path: Path, root: Path):
    """Validate one machine-readable AC list (docs/specs/*-acs.json, ADR-0009)."""
    rel = path.relative_to(root)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return [f"{rel}: unreadable or invalid JSON ({e})"]
    findings = []
    for key in ("task", "spec"):
        if not isinstance(data.get(key), str) or not data.get(key):
            findings.append(f"{rel}: missing or non-string '{key}' field")
    acs = data.get("acs")
    if not isinstance(acs, list) or not acs:
        findings.append(f"{rel}: 'acs' must be a non-empty list")
        return findings
    seen_ids = set()
    for i, entry in enumerate(acs):
        if not isinstance(entry, dict):
            findings.append(f"{rel}: acs[{i}] is not an object")
            continue
        ac_id = entry.get("id")
        if not isinstance(ac_id, str) or not ac_id:
            findings.append(f"{rel}: acs[{i}] missing 'id'")
        elif ac_id in seen_ids:
            findings.append(f"{rel}: duplicate AC id '{ac_id}'")
        else:
            seen_ids.add(ac_id)
        if not isinstance(entry.get("text"), str) or not entry.get("text"):
            findings.append(f"{rel}: acs[{i}] missing 'text'")
        if entry.get("status") not in ACS_STATUSES:
            findings.append(
                f"{rel}: acs[{i}] status {entry.get('status')!r} not in "
                f"{sorted(ACS_STATUSES)}")
    return findings


def scanned_files(root: Path):
    patterns = [
        "README.md",
        ".claude/CLAUDE.md",
        "docs/DESIGN.md",
        "docs/SCOPE.md",
    ]
    files = [root / p for p in patterns if (root / p).is_file()]
    for glob in (".claude/rules/*.md", ".claude/skills/*/SKILL.md",
                 ".claude/agents/roles/*.md", "templates/*.md"):
        files.extend(sorted(root.glob(glob)))
    return files


def lint(root: Path):
    findings = []
    skills = {p.name for p in (root / ".claude" / "skills").iterdir()
              if p.is_dir()} if (root / ".claude" / "skills").is_dir() else set()
    known_commands = skills | BUILTIN_COMMANDS

    blueprints = sorted(p for p in (root / ".claude" / "blueprints").iterdir()
                        if p.is_dir()) if (root / ".claude" / "blueprints").is_dir() else []

    files = scanned_files(root)
    all_text = {f: f.read_text(encoding="utf-8", errors="replace") for f in files}

    # 1. slash-command references (templates/ excluded — they are project-doc
    #    skeletons containing HTTP endpoint paths like /health, not skill refs)
    for f, text in all_text.items():
        if f.parent.name == "templates":
            continue
        for m in SLASH_RE.finditer(text):
            name = m.group(1)
            if name not in known_commands:
                findings.append(f"{f.relative_to(root)}: reference to unknown command /{name}")

    # 2. repo-relative file references. Fenced code blocks are stripped first —
    #    worked examples live there with fictional paths. Runtime artifacts and
    #    placeholder/example paths are skipped.
    for f, text in all_text.items():
        prose = FENCE_RE.sub("", text)
        for m in PATH_RE.finditer(prose):
            ref = m.group(1)
            if any(tok in ref for tok in PLACEHOLDER_TOKENS):
                continue
            if ref in RUNTIME_ARTIFACTS or TASK_ID_RE.search(ref):
                continue
            if not (root / ref).exists():
                findings.append(f"{f.relative_to(root)}: dead file reference {ref}")

    # 3. ADR index sync (DESIGN.md <-> docs/adr/)
    design = root / "docs" / "DESIGN.md"
    adr_dir = root / "docs" / "adr"
    if design.is_file() and adr_dir.is_dir():
        indexed = set(ADR_LINK_RE.findall(design.read_text(encoding="utf-8")))
        on_disk = {p.name for p in adr_dir.glob("[0-9][0-9][0-9][0-9]-*.md")}
        for missing in sorted(on_disk - indexed):
            findings.append(f"docs/DESIGN.md: ADR {missing} exists on disk but is not in the Design Decisions Index")
        for stale in sorted(indexed - on_disk):
            findings.append(f"docs/DESIGN.md: index references adr/{stale} which does not exist")

    # 4. blueprint presence in the three entry docs
    for doc_rel in ("README.md", ".claude/CLAUDE.md", "docs/SCOPE.md"):
        doc = root / doc_rel
        if not doc.is_file():
            continue
        text = doc.read_text(encoding="utf-8", errors="replace")
        for bp in blueprints:
            if bp.name not in text:
                findings.append(f"{doc_rel}: blueprint '{bp.name}' exists but is not mentioned")

    # 5. blueprint §-section parity + referenced sections exist everywhere
    section_sets = {}
    for bp in blueprints:
        ref = bp / "reference.md"
        if not ref.is_file():
            findings.append(f".claude/blueprints/{bp.name}: missing reference.md")
            continue
        section_sets[bp.name] = set(SECTION_HEADING_RE.findall(ref.read_text(encoding="utf-8", errors="replace")))
    if len(section_sets) > 1:
        names = sorted(section_sets)
        base_name, base = names[0], section_sets[names[0]]
        for other in names[1:]:
            missing = base - section_sets[other]
            extra = section_sets[other] - base
            for s in sorted(missing):
                findings.append(f"blueprint parity: {other}/reference.md is missing {s} (present in {base_name})")
            for s in sorted(extra):
                findings.append(f"blueprint parity: {other}/reference.md has {s} not present in {base_name}")
    if section_sets:
        common = set.intersection(*section_sets.values())
        referenced = set()
        for text in all_text.values():
            referenced.update(SECTION_REF_RE.findall(text))
        for s in sorted(referenced - common):
            findings.append(f"§-reference: {s} is referenced in docs but missing from at least one blueprint reference.md")

    # 6. machine-readable AC lists conform to the ADR-0009 schema
    specs_dir = root / "docs" / "specs"
    if specs_dir.is_dir():
        for acs_file in sorted(specs_dir.glob("*-acs.json")):
            findings.extend(lint_acs_file(acs_file, root))

    return findings


def self_test():
    """Seed a known-bad fixture tree; the linter must flag every seeded defect."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / ".claude" / "skills" / "plan").mkdir(parents=True)
        (root / ".claude" / "rules").mkdir()
        (root / ".claude" / "blueprints" / "alpha").mkdir(parents=True)
        (root / ".claude" / "blueprints" / "beta").mkdir()
        (root / "docs" / "adr").mkdir(parents=True)

        (root / "README.md").write_text(
            "Run /discovery to generate docs. Also run /plan.\n"
            "See docs/missing-file.md and blueprint alpha.\n",
            encoding="utf-8")
        (root / ".claude" / "CLAUDE.md").write_text("alpha beta and §ghost-section\n", encoding="utf-8")
        (root / "docs" / "DESIGN.md").write_text(
            "| [0001](adr/0001-real.md) | x |\n| [0002](adr/0002-stale.md) | y |\nalpha beta\n",
            encoding="utf-8")
        (root / "docs" / "SCOPE.md").write_text("alpha only\n", encoding="utf-8")  # beta missing
        (root / "docs" / "adr" / "0001-real.md").write_text("# ADR-0001\n", encoding="utf-8")
        (root / "docs" / "adr" / "0003-unindexed.md").write_text("# ADR-0003\n", encoding="utf-8")
        (root / ".claude" / "blueprints" / "alpha" / "reference.md").write_text(
            "## §stack\n## §build-commands\n", encoding="utf-8")
        (root / ".claude" / "blueprints" / "beta" / "reference.md").write_text(
            "## §stack\n## §extra-section\n", encoding="utf-8")
        (root / "docs" / "specs").mkdir()
        (root / "docs" / "specs" / "BAD-1-acs.json").write_text(
            '{"task": "BAD-1", "acs": ['
            '{"id": "AC1", "text": "x", "status": "pending"},'
            '{"id": "AC1", "status": "maybe"}]}', encoding="utf-8")
        (root / "docs" / "specs" / "GOOD-1-acs.json").write_text(
            '{"task": "GOOD-1", "spec": "docs/specs/GOOD-1-spec.md", "acs": '
            '[{"id": "AC1", "text": "works", "status": "pass"}]}', encoding="utf-8")
        (root / "docs" / "specs" / "BROKEN-1-acs.json").write_text(
            "not json {", encoding="utf-8")

        findings = lint(root)
        expected_fragments = [
            "unknown command /discovery",
            "dead file reference docs/missing-file.md",
            "adr/0002-stale.md which does not exist",
            "0003-unindexed.md exists on disk but is not",
            "docs/SCOPE.md: blueprint 'beta'",
            "beta/reference.md is missing §build-commands",
            "beta/reference.md has §extra-section",
            "§ghost-section is referenced",
            "BAD-1-acs.json: missing or non-string 'spec'",
            "duplicate AC id 'AC1'",
            "missing 'text'",
            "status 'maybe' not in",
            "BROKEN-1-acs.json: unreadable or invalid JSON",
        ]
        missed = [frag for frag in expected_fragments
                  if not any(frag in f for f in findings)]
        false_neg_free = not missed
        # /plan must NOT be flagged (skill exists); GOOD acs must not be flagged
        no_false_pos = (not any("/plan" in f for f in findings)
                        and not any("GOOD-1-acs.json" in f for f in findings))

        print(f"self-test: {len(findings)} findings on seeded fixture")
        for frag in expected_fragments:
            status = "CAUGHT" if frag not in missed else "MISSED"
            print(f"  {status}: {frag}")
        print(f"  {'PASS' if no_false_pos else 'FAIL'}: /plan (real skill) not flagged")
        return false_neg_free and no_false_pos


def main():
    if "--self-test" in sys.argv:
        ok = self_test()
        print("self-test:", "PASS" if ok else "FAIL")
        sys.exit(0 if ok else 1)

    findings = lint(ROOT)
    if findings:
        print(f"harness_lint: {len(findings)} finding(s)\n")
        for f in findings:
            print(f"  ✗ {f}")
        sys.exit(1)
    print("harness_lint: clean — cross-references resolve, blueprints in parity")
    sys.exit(0)


if __name__ == "__main__":
    main()
