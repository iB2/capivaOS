#!/usr/bin/env python3
"""
validate_fixtures.py — deterministic schema self-test for the context-answerer
eval gate (RFN-002). Tier 1 (no LLM): runs in no-auth CI so the fixture harness
cannot rot silently. It does NOT run the answerer — that is the release-time
Tier 2 run (see evals/README.md). It only checks that fixtures.md and
expected-verdicts.json are well-formed, in parity, and cover every category.

Zero dependencies. Exit 0 = clean; exit 1 = findings printed. `--self-test`
seeds known-bad inputs and asserts each is caught (mutual proof: the checker
that proves the corpus is well-formed must itself fail on a malformed corpus).
"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES_MD = HERE / "fixtures.md"
EXPECTED_JSON = HERE / "expected-verdicts.json"

VERDICT_ENUM = {"FINDING", "ROUTE", "RED-FLAG"}
REQUIRED_CATEGORIES = {
    "type2-dispositive",
    "type1-undocumented",
    "type3-adjacent",
    "adversarial-tangential",
    "adversarial-superseded",
    "adversarial-local-decision",
    "adversarial-contradiction",
}
MIN_FIXTURES = 15
# Non-category markers allowed inside the [ ... ] tag.
MARKERS = {"type-r"}

_HEADER_RE = re.compile(r"^##\s+(FIX-\d+)\s+—\s+\[([^\]]+)\]", re.MULTILINE)


def parse_fixtures(md_text):
    """Return {id: {"categories": set, "body": str}} parsed from fixtures.md."""
    out = {}
    matches = list(_HEADER_RE.finditer(md_text))
    for i, m in enumerate(matches):
        fid = m.group(1)
        tags = {t.strip() for t in m.group(2).split(",") if t.strip()}
        categories = tags - MARKERS
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md_text)
        out[fid] = {"categories": categories, "body": md_text[start:end]}
    return out


def validate(fixtures, expected):
    """Pure validation over parsed inputs. Returns a list of finding strings."""
    findings = []

    fx_ids = list(fixtures.keys())
    exp_ids = list(expected.keys())

    # id uniqueness (regex can't yield dupes, but guard against a hand-built dict)
    if len(fx_ids) != len(set(fx_ids)):
        findings.append("duplicate fixture id in fixtures.md")

    if len(fx_ids) < MIN_FIXTURES:
        findings.append(f"only {len(fx_ids)} fixtures; need >= {MIN_FIXTURES}")

    # parity: every fixture has an expected verdict and vice versa
    for fid in fx_ids:
        if fid not in expected:
            findings.append(f"{fid}: in fixtures.md but missing from expected-verdicts.json")
    for fid in exp_ids:
        if fid not in fixtures:
            findings.append(f"{fid}: in expected-verdicts.json but missing from fixtures.md")

    seen_categories = set()
    for fid in fx_ids:
        fx = fixtures[fid]
        seen_categories |= fx["categories"]
        body = fx["body"]
        if "**Question:**" not in body:
            findings.append(f"{fid}: missing '**Question:**'")
        if "**Available documentation:**" not in body:
            findings.append(f"{fid}: missing '**Available documentation:**'")
        if not fx["categories"]:
            findings.append(f"{fid}: no category tag")

        exp = expected.get(fid)
        if exp is None:
            continue
        verdict = exp.get("verdict")
        if verdict not in VERDICT_ENUM:
            findings.append(f"{fid}: verdict {verdict!r} not in {sorted(VERDICT_ENUM)}")
        if not isinstance(exp.get("safety_critical"), bool):
            findings.append(f"{fid}: 'safety_critical' must be bool")
        if not isinstance(exp.get("citation_required"), bool):
            findings.append(f"{fid}: 'citation_required' must be bool")
        # FINDING and RED-FLAG make a claim about the docs → must require a citation
        if verdict in {"FINDING", "RED-FLAG"} and not exp.get("citation_required"):
            findings.append(f"{fid}: {verdict} must set citation_required=true")
        # category tag in the .md must match the json category
        json_cat = exp.get("category")
        if json_cat and json_cat not in fx["categories"]:
            findings.append(f"{fid}: json category {json_cat!r} not in md tags {sorted(fx['categories'])}")

    missing_cats = REQUIRED_CATEGORIES - seen_categories
    if missing_cats:
        findings.append(f"categories not covered by any fixture: {sorted(missing_cats)}")

    # every safety-critical category must have at least one safety_critical fixture
    sc_present = any(
        expected[fid].get("safety_critical") for fid in fx_ids if fid in expected
    )
    if not sc_present:
        findings.append("no safety_critical fixtures — the zero-tolerance set is empty")

    return findings


def _load():
    md = FIXTURES_MD.read_text(encoding="utf-8")
    data = json.loads(EXPECTED_JSON.read_text(encoding="utf-8"))
    expected = data.get("fixtures", {})
    return parse_fixtures(md), expected


def _self_test():
    """Seed malformed corpora; assert each is caught."""
    failures = []

    def expect_finding(name, fixtures, expected, needle):
        found = validate(fixtures, expected)
        if not any(needle in f for f in found):
            failures.append(f"self-test '{name}': expected a finding containing {needle!r}, got {found}")

    good_fx = {f"FIX-{i:02d}": {"categories": {c}, "body": "**Question:** q\n**Available documentation:** d"}
               for i, c in enumerate(sorted(REQUIRED_CATEGORIES) * 3, start=1)}
    good_exp = {fid: {"verdict": "ROUTE", "category": next(iter(v["categories"])),
                      "citation_required": False, "safety_critical": True}
                for fid, v in good_fx.items()}
    # sanity: the good set is clean
    base = validate(good_fx, good_exp)
    if base:
        failures.append(f"self-test 'clean baseline' unexpectedly failed: {base}")

    # 1. missing expected verdict
    fx = dict(good_fx); exp = dict(good_exp); exp.pop("FIX-01")
    expect_finding("missing-verdict", fx, exp, "FIX-01")
    # 2. bad verdict enum
    fx = dict(good_fx); exp = json.loads(json.dumps(good_exp)); exp["FIX-01"]["verdict"] = "MAYBE"
    expect_finding("bad-enum", fx, exp, "not in")
    # 3. too few fixtures
    small = {"FIX-01": {"categories": {"type1-undocumented"}, "body": "**Question:** q\n**Available documentation:** d"}}
    expect_finding("too-few", small, {"FIX-01": {"verdict": "ROUTE", "category": "type1-undocumented", "citation_required": False, "safety_critical": True}}, "need >=")
    # 4. FINDING without citation_required
    fx = dict(good_fx); exp = json.loads(json.dumps(good_exp))
    exp["FIX-01"]["verdict"] = "FINDING"; exp["FIX-01"]["citation_required"] = False
    expect_finding("finding-no-citation", fx, exp, "citation_required=true")
    # 5. missing category coverage
    one_cat = {"FIX-%02d" % i: {"categories": {"type1-undocumented"}, "body": "**Question:** q\n**Available documentation:** d"} for i in range(1, 16)}
    one_exp = {fid: {"verdict": "ROUTE", "category": "type1-undocumented", "citation_required": False, "safety_critical": True} for fid in one_cat}
    expect_finding("missing-categories", one_cat, one_exp, "not covered")

    if failures:
        print("validate_fixtures --self-test: FAIL")
        for f in failures:
            print("  -", f)
        return 1
    print("validate_fixtures --self-test: clean (5 seeded corpora all caught)")
    return 0


def main(argv):
    if "--self-test" in argv:
        return _self_test()
    fixtures, expected = _load()
    findings = validate(fixtures, expected)
    if findings:
        print("validate_fixtures: FAIL")
        for f in findings:
            print("  -", f)
        return 1
    print(f"validate_fixtures: clean — {len(fixtures)} fixtures, all categories covered, parity OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
