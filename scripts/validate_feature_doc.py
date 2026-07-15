#!/usr/bin/env python3
"""
validate_feature_doc.py — structural validator for the project-facing feature
docs emitted by the execution docs-generation step (RFN-012). After /capiva:auto
(or the clustered cycle) drives a task to FINISH, it writes/updates
`docs/features/<TASK-ID>.md` (what was built + how to use) and a row in
`docs/features/INDEX.md`.

This checks a feature doc is structurally complete, and that INDEX entries
resolve to real files. It is NOT a quality gate and blocks nothing — the docs
step is a non-blocking aid (same posture as the RFN-007 review packet); a
malformed doc is surfaced, never a merge blocker. The value here is the
--self-test as CI coverage (same pattern as validate_review_packet.py /
validate_decisions.py). Zero deps.

Usage:
  validate_feature_doc.py <path>              validate one feature doc
  validate_feature_doc.py --index <path>      validate an INDEX.md (links resolve)
  validate_feature_doc.py --self-test         seed good/bad, assert caught
"""

import os
import re
import sys

# Substrings that MUST appear (case-insensitive) in a feature doc. The doc's
# task identity is carried by its filename (docs/features/<TASK-ID>.md), so it
# is not re-checked here (that avoids false-matching ADR-/PR- style tokens).
REQUIRED_SECTIONS = ["Summary", "How to use", "Behavior", "Related", "Last updated"]
# An INDEX row links a feature doc: "| RFN-012 | [what](RFN-012.md) | ... |".
_LINK_RE = re.compile(r"\]\(([^)]+\.md)\)")
# HTML comments hold template/example rows — strip them before scanning links.
_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
# Section presence is checked in HEADINGS, not arbitrary prose — otherwise a
# sentence that happens to contain a section name ("...and how to use it")
# would mask a genuinely missing section (AC9).
_HEADING_RE = re.compile(r"^#{1,6}\s+(.*)$", re.MULTILINE)


def _strip_comments(text):
    return _COMMENT_RE.sub("", text)


def validate(text):
    """Return a list of findings for a single feature doc (empty = valid)."""
    stripped = _strip_comments(text)
    low = stripped.lower()
    headings = "\n".join(h.lower() for h in _HEADING_RE.findall(stripped))
    findings = []
    for sec in REQUIRED_SECTIONS:
        # "Last updated" is a trailing italic footer (_Last updated: ..._), not a
        # heading; every other required section must appear as a heading.
        present = ("last updated" in low) if sec == "Last updated" else (sec.lower() in headings)
        if not present:
            findings.append(f"missing required section: {sec!r}")
    return findings


def validate_index(path):
    """Return findings for an INDEX.md: every linked <file>.md must exist."""
    try:
        text = _read(path)
    except OSError as e:
        return [f"cannot read index {path!r}: {e}"]
    base = os.path.dirname(path)
    findings = []
    for m in _LINK_RE.finditer(_strip_comments(text)):
        target = m.group(1)
        if target.startswith(("http://", "https://")):
            continue
        resolved = target if os.path.isabs(target) else os.path.join(base, target)
        if not os.path.isfile(resolved):
            findings.append(f"INDEX links a missing file: {target!r}")
    return findings


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _self_test():
    failures = []
    good = (
        "# Feature: Two-sprint cycle (RFN-013)\n\n"
        "## Summary\nWhat was built and why.\n\n"
        "## How to use\nRun `/capiva:refine` then `/capiva:auto`.\n\n"
        "## Behavior & limits\nNon-blocking; auto/clustered only.\n\n"
        "## Related\nSpec, ADR-0014, PR #61.\n\n"
        "_Last updated: 2026-07-15_\n"
    )
    if validate(good):
        failures.append(f"clean baseline failed: {validate(good)}")

    # one seeded doc per required section removed — each must be caught
    removals = {
        "Summary": ("## Summary", "## S"),
        "How to use": ("## How to use", "## HowTo"),
        "Behavior": ("## Behavior & limits", "## Limits"),
        "Related": ("## Related", "## Refs"),
        "Last updated": ("_Last updated:", "_Updated:"),
    }
    for sec, (old, new) in removals.items():
        f = validate(good.replace(old, new))
        if not any(sec in x for x in f):
            failures.append(f"self-test 'missing-{sec}': expected ~{sec!r}, got {f}")

    # prose-echo (AC9): the "How to use" HEADING is removed but the phrase appears
    # in the Summary prose — a substring check would false-PASS; heading-anchoring
    # must still catch it.
    prose_echo = (good.replace("## How to use\nRun `/capiva:refine` then `/capiva:auto`.\n\n", "")
                      .replace("What was built and why.",
                               "What was built and why, and how to use it."))
    f = validate(prose_echo)
    if not any("How to use" in x for x in f):
        failures.append(f"self-test 'prose-echo': expected ~'How to use', got {f}")

    # index: a link to a missing file must be caught
    here = os.path.dirname(os.path.abspath(__file__))
    seed = os.path.join(here, "_ft_selftest_index.md")
    try:
        with open(seed, "w", encoding="utf-8") as fh:
            fh.write("# Feature Docs Index\n\n| Task | Doc |\n|---|---|\n"
                     "| RFN-999 | [x](RFN-999-does-not-exist.md) |\n")
        idx = validate_index(seed)
        if not any("missing file" in x for x in idx):
            failures.append(f"self-test 'index-missing-file': expected a missing-file finding, got {idx}")
    finally:
        try:
            os.remove(seed)
        except OSError:
            pass

    if failures:
        print("validate_feature_doc --self-test: FAIL")
        for f in failures:
            print("  -", f)
        return 1
    print("validate_feature_doc --self-test: clean "
          f"({len(REQUIRED_SECTIONS)} missing-section + prose-echo + index missing-file caught, baseline OK)")
    return 0


def main(argv):
    if "--self-test" in argv:
        return _self_test()
    paths = [a for a in argv if not a.startswith("-")]
    if not paths:
        print("usage: validate_feature_doc.py <feature-doc.md> | --index <INDEX.md> | --self-test",
              file=sys.stderr)
        return 2
    if "--index" in argv:
        findings = validate_index(paths[0])
    else:
        try:
            findings = validate(_read(paths[0]))
        except OSError as e:
            print(f"validate_feature_doc: cannot read {paths[0]!r}: {e}", file=sys.stderr)
            return 2
    if findings:
        print(f"validate_feature_doc: {paths[0]}: {len(findings)} finding(s)")
        for f in findings:
            print("  -", f)
        return 1
    print(f"validate_feature_doc: {paths[0]}: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
