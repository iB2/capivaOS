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
  7. Plugin manifests (.claude-plugin/plugin.json + marketplace.json): parse,
     identical plugin/marketplace-entry names, semver version in plugin.json
     ONLY (single version source), self-referencing "./" source.
  8. Board dependency graphs (.board/tasks.md, live or project-template):
     every Depends ID exists on that board; the graph is acyclic (LOOP-005).

Usage:
  python3 scripts/harness_lint.py              # lint the repo; exit 1 on findings
  python3 scripts/harness_lint.py --self-test  # verify the linter catches seeded drift

Scanned files (plugin layout, ADR-0013): README.md, rules/*.md (incl.
laws.md), skills/*/SKILL.md, agents/*.md, docs/DESIGN.md, docs/SCOPE.md,
project-template/templates/*.md. Excluded: docs/blueprint-migration-map.md
(historical record), .board/ and root docs artifact dirs (untracked dev state).

Path semantics: engine references in scanned content must be
${CLAUDE_PLUGIN_ROOT}/<path> and are resolved against the repo root.
Project-artifact paths (docs/specs, docs/reports, .board/, PLAN.md, ...)
are runtime files in adopter repos and are skipped. Harness skill
references must be namespaced /capiva:<skill>.
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
    "fast", "init", "memory", "review", "plugin", "reload-plugins",
}
NAMESPACE = "capiva"

# Trailing char must be alphanumeric (no mid-backtrack "grill-" matches);
# reject file extensions (/reference.md) and path continuations (/api/v1),
# but allow sentence-final periods ("run /grill-spec.").
SLASH_RE = re.compile(r"(?<![\w./`>])/([a-z][a-z0-9:-]+[a-z0-9])(?!\.\w|[-/\w])")
PATH_RE = re.compile(r"(?<![\w/])((?:docs|templates|\.claude|\.board|scripts|rules|skills|agents|hooks|blueprints|project-template)/[\w./-]+\.(?:md|py|json|mmd|yml|cmd))")
PLUGIN_ROOT_REF_RE = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([\w./ -]+?\.(?:md|py|json|mmd|yml|cmd))")
# Paths that exist only in adopter projects at runtime (never in this repo)
PROJECT_ARTIFACT_PREFIXES = (
    "docs/specs/", "docs/reports/", "docs/tech-context/", "docs/handover/",
    "docs/cab/", "docs/release/", "docs/deviations/", ".board/",
    "capiva-blueprints/",
)
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
    ".claude/settings.json",  # adopter's project hook registration (dev/copy mode)
}
PLACEHOLDER_TOKENS = ("*", "TASK-ID", "NNNN", "000N", "DEV-NNN", "<", "[", "your-", "N-slug")
ACS_STATUSES = {"pending", "pass", "fail"}
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


TASK_HEAD_RE = re.compile(r"^- \[[ x]\] \*\*([A-Z]+-\d+)\*\*", re.MULTILINE)
DEPENDS_RE = re.compile(r"^\s*- \*\*Depends\*\*:\s*(.+)$", re.MULTILINE)


def lint_board_dependencies(board: Path, root: Path):
    """Check 8 (LOOP-005): Depends IDs resolve on-board; graph is acyclic."""
    findings = []
    try:
        text = board.read_text(encoding="utf-8")
    except OSError:
        return findings
    rel = board.resolve()
    try:
        rel = board.resolve().relative_to(root.resolve())
    except ValueError:
        pass
    ids = TASK_HEAD_RE.findall(text)
    id_set = set(ids)
    graph = {}
    # pair each task block with its Depends line
    blocks = re.split(r"(?m)^(?=- \[[ x]\] \*\*[A-Z]+-\d+\*\*)", text)
    for blk in blocks:
        head = TASK_HEAD_RE.match(blk)
        if not head:
            continue
        tid = head.group(1)
        deps = []
        dm = DEPENDS_RE.search(blk)
        if dm:
            raw = dm.group(1)
            deps = [d.strip() for d in re.split(r"[,;]", raw)
                    if d.strip() and d.strip().lower() not in ("none", "all", "--")]
            deps = [d for d in deps if re.fullmatch(r"[A-Z]+-\d+", d)]
        for d in deps:
            if d not in id_set:
                findings.append(f"{rel}: task {tid} depends on unknown task {d}")
        graph[tid] = [d for d in deps if d in id_set]
    # cycle detection (iterative DFS, 3-color)
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {k: WHITE for k in graph}
    for start in graph:
        if color[start] != WHITE:
            continue
        stack = [(start, iter(graph[start]))]
        color[start] = GRAY
        while stack:
            node, it = stack[-1]
            advanced = False
            for nxt in it:
                if color.get(nxt, BLACK) == GRAY:
                    findings.append(f"{rel}: dependency cycle involving {nxt} and {node}")
                elif color.get(nxt, BLACK) == WHITE:
                    color[nxt] = GRAY
                    stack.append((nxt, iter(graph[nxt])))
                    advanced = True
                    break
            if not advanced:
                color[node] = BLACK
                stack.pop()
    return findings


def lint_manifests(root: Path):
    """Check 7: plugin + marketplace manifest validity and parity (ADR-0013)."""
    findings = []
    pj_path = root / ".claude-plugin" / "plugin.json"
    mk_path = root / ".claude-plugin" / "marketplace.json"
    if not pj_path.is_file() and not mk_path.is_file():
        return findings  # not a plugin repo (self-test fixtures without manifests)
    try:
        pj = json.loads(pj_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return [f".claude-plugin/plugin.json: unreadable or invalid ({e})"]
    try:
        mk = json.loads(mk_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return [f".claude-plugin/marketplace.json: unreadable or invalid ({e})"]

    if not SEMVER_RE.match(str(pj.get("version", ""))):
        findings.append(f"plugin.json: version {pj.get('version')!r} is not X.Y.Z semver")
    entries = mk.get("plugins") or []
    if len(entries) != 1:
        findings.append(f"marketplace.json: expected exactly 1 plugin entry, found {len(entries)}")
        return findings
    entry = entries[0]
    if pj.get("name") != entry.get("name") or pj.get("name") != mk.get("name"):
        findings.append(
            f"manifest name parity: plugin.json={pj.get('name')!r} "
            f"marketplace={mk.get('name')!r} entry={entry.get('name')!r} — must be identical")
    if "version" in entry:
        findings.append("marketplace entry declares a version — plugin.json is the single "
                        "version source (Claude Code silently prefers plugin.json)")
    if entry.get("source") != "./":
        findings.append(f"marketplace entry source {entry.get('source')!r} — expected \"./\" (self-marketplace)")
    return findings


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
        "docs/DESIGN.md",
        "docs/SCOPE.md",
        "docs/troubleshooting.md",
    ]
    files = [root / p for p in patterns if (root / p).is_file()]
    for glob in ("rules/*.md", "skills/*/SKILL.md",
                 "agents/*.md", "project-template/templates/*.md"):
        files.extend(sorted(root.glob(glob)))
    return files


def lint(root: Path):
    findings = []
    skills = {p.name for p in (root / "skills").iterdir()
              if p.is_dir()} if (root / "skills").is_dir() else set()
    known_commands = {f"{NAMESPACE}:{s}" for s in skills} | BUILTIN_COMMANDS
    bare_skills = skills  # bare references are flagged: must be namespaced

    blueprints = sorted(p for p in (root / "blueprints").iterdir()
                        if p.is_dir()) if (root / "blueprints").is_dir() else []

    files = scanned_files(root)
    all_text = {f: f.read_text(encoding="utf-8", errors="replace") for f in files}

    # 1. slash-command references (templates/ excluded — they are project-doc
    #    skeletons containing HTTP endpoint paths like /health, not skill refs)
    for f, text in all_text.items():
        if f.parent.name == "templates":
            continue
        for m in SLASH_RE.finditer(text):
            name = m.group(1)
            if name in known_commands:
                continue
            if name in bare_skills:
                findings.append(
                    f"{f.relative_to(root)}: un-namespaced skill reference /{name} "
                    f"(plugin skills are /{NAMESPACE}:{name})")
            else:
                findings.append(f"{f.relative_to(root)}: reference to unknown command /{name}")

    # 2a. ${CLAUDE_PLUGIN_ROOT}/ references must resolve against the repo root
    #     (engine files travel with the plugin).
    for f, text in all_text.items():
        for m in PLUGIN_ROOT_REF_RE.finditer(text):
            ref = m.group(1)
            if any(tok in ref for tok in PLACEHOLDER_TOKENS) or TASK_ID_RE.search(ref):
                continue
            if not (root / ref).exists():
                findings.append(f"{f.relative_to(root)}: dead plugin-root reference {ref}")

    # 2b. bare repo-relative references. Engine paths must NOT appear bare in
    #     skill/rule/agent content (they would resolve against the adopter
    #     project) — they belong behind ${CLAUDE_PLUGIN_ROOT}/. Project
    #     artifacts and placeholders are skipped. Fenced code blocks stripped.
    ENGINE_PREFIXES = ("rules/", "skills/", "agents/", "hooks/", "blueprints/",
                       "scripts/", "project-template/", ".claude/")
    ENGINE_CONTENT_DIRS = {"rules", "skills", "agents"}
    for f, text in all_text.items():
        prose = FENCE_RE.sub("", text)
        in_engine_content = (f.parent.name in ENGINE_CONTENT_DIRS
                             or f.parent.parent.name == "skills")
        for m in PATH_RE.finditer(prose):
            ref = m.group(1)
            if any(tok in ref for tok in PLACEHOLDER_TOKENS):
                continue
            if ref in RUNTIME_ARTIFACTS or TASK_ID_RE.search(ref):
                continue
            if any(ref.startswith(px) for px in PROJECT_ARTIFACT_PREFIXES):
                continue
            if in_engine_content and any(ref.startswith(px) for px in ENGINE_PREFIXES):
                findings.append(
                    f"{f.relative_to(root)}: bare engine path {ref} — must be "
                    f"${{CLAUDE_PLUGIN_ROOT}}/{ref}")
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
    for doc_rel in ("README.md", "rules/laws.md", "docs/SCOPE.md"):
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
            findings.append(f"blueprints/{bp.name}: missing reference.md")
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

    # 7. plugin manifest validity and parity
    findings.extend(lint_manifests(root))

    # 8. board dependency graphs (live board is untracked but linted when present)
    for board in (root / ".board" / "tasks.md",
                  root / "project-template" / ".board" / "tasks.md"):
        if board.is_file():
            findings.extend(lint_board_dependencies(board, root))

    return findings


def self_test():
    """Seed a known-bad fixture tree; the linter must flag every seeded defect."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "skills" / "plan").mkdir(parents=True)
        (root / "rules").mkdir()
        (root / "blueprints" / "alpha").mkdir(parents=True)
        (root / "blueprints" / "beta").mkdir()
        (root / "docs" / "adr").mkdir(parents=True)

        (root / "README.md").write_text(
            "Run /discovery to generate docs. Also run /plan bare and /capiva:plan namespaced.\n"
            "See docs/missing-file.md and blueprint alpha.\n",
            encoding="utf-8")
        (root / "rules" / "laws.md").write_text(
            "alpha beta and §ghost-section\n"
            "Read ${CLAUDE_PLUGIN_ROOT}/rules/gone.md for details.\n"
            "Also read skills/plan/SKILL.md directly.\n", encoding="utf-8")
        (root / "docs" / "DESIGN.md").write_text(
            "| [0001](adr/0001-real.md) | x |\n| [0002](adr/0002-stale.md) | y |\nalpha beta\n",
            encoding="utf-8")
        (root / "docs" / "SCOPE.md").write_text("alpha only\n", encoding="utf-8")  # beta missing
        (root / "docs" / "adr" / "0001-real.md").write_text("# ADR-0001\n", encoding="utf-8")
        (root / "docs" / "adr" / "0003-unindexed.md").write_text("# ADR-0003\n", encoding="utf-8")
        (root / "blueprints" / "alpha" / "reference.md").write_text(
            "## §stack\n## §build-commands\n", encoding="utf-8")
        (root / "blueprints" / "beta" / "reference.md").write_text(
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
        (root / ".board").mkdir()
        (root / ".board" / "tasks.md").write_text(
            "# Board\n"
            "- [ ] **AAA-1** first (P1)\n  - **Depends**: BBB-9\n"
            "- [ ] **AAA-2** second (P1)\n  - **Depends**: AAA-3\n"
            "- [ ] **AAA-3** third (P1)\n  - **Depends**: AAA-2\n"
            "- [ ] **AAA-4** ok (P2)\n  - **Depends**: none\n", encoding="utf-8")
        (root / ".claude-plugin").mkdir()
        (root / ".claude-plugin" / "plugin.json").write_text(
            '{"name": "alpha-plug", "version": "1.0"}', encoding="utf-8")
        (root / ".claude-plugin" / "marketplace.json").write_text(
            '{"name": "alpha-plug", "plugins": [{"name": "other-name", '
            '"source": "./plug", "version": "2.0.0"}]}', encoding="utf-8")

        findings = lint(root)
        expected_fragments = [
            "un-namespaced skill reference /plan",
            "dead plugin-root reference rules/gone.md",
            "bare engine path skills/plan/SKILL.md",
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
            "is not X.Y.Z semver",
            "manifest name parity",
            "marketplace entry declares a version",
            "expected \"./\"",
            "depends on unknown task BBB-9",
            "dependency cycle involving",
        ]
        missed = [frag for frag in expected_fragments
                  if not any(frag in f for f in findings)]
        false_neg_free = not missed
        # /capiva:plan must NOT be flagged; GOOD acs must not be flagged
        no_false_pos = (not any("unknown command /capiva:plan" in f for f in findings)
                        and not any("GOOD-1-acs.json" in f for f in findings))

        print(f"self-test: {len(findings)} findings on seeded fixture")
        for frag in expected_fragments:
            status = "CAUGHT" if frag not in missed else "MISSED"
            print(f"  {status}: {frag}")
        print(f"  {'PASS' if no_false_pos else 'FAIL'}: /capiva:plan (namespaced skill) not flagged")
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
