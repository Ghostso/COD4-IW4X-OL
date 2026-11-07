#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Self-check for this audit's deliverables.

Checks:
  1. every required file exists
  2. Issue IDs unique and sequential
  3. status / priority values are in the allowed vocabulary
  4. depends_on references resolve to real Issue IDs
  5. every issue carries at least one evidence path
  6. every P0 issue has acceptance criteria
  7. JSON / CSV / Markdown issue counts agree
  8. rollup statistics recompute correctly
  9. SHA256SUMS.txt matches the files on disk
 10. generated markdown does not contradict the register

Run:  python -I verify_audit.py
Exit code 0 = all checks passed.
"""
import csv
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CLOSED = {"RESOLVED_VERIFIED", "OBSOLETE"}
VALID_STATUS = {
    "OPEN", "PARTIALLY_RESOLVED", "BLOCKED", "UNVERIFIED", "REGRESSION",
    "CONTRADICTORY_EVIDENCE", "NOT_IMPLEMENTED", "UNKNOWN",
    "RESOLVED_VERIFIED", "OBSOLETE",
}
VALID_PRIO = {"P0", "P1", "P2", "P3", "NONE"}

REQUIRED_FILES = [
    "00_INDEX.md",
    "01_PROJECT_HISTORY_TIMELINE.md",
    "02_ALL_HISTORICAL_ISSUES.md",
    "03_MASTER_UNRESOLVED_ISSUES.md",
    "04_P0_CRITICAL_BLOCKERS.md",
    "05_PROTOCOL_GAPS.md",
    "06_CLIENT_REVERSE_ENGINEERING_GAPS.md",
    "07_SERVER_IMPLEMENTATION_GAPS.md",
    "08_MAP_AND_ASSET_GAPS.md",
    "09_MOVEMENT_AND_COMBAT_GAPS.md",
    "10_CONTRADICTIONS_AND_FALSE_CLOSURES.md",
    "11_ISSUE_DEPENDENCY_GRAPH.md",
    "12_PRIORITIZED_DEVELOPMENT_ROADMAP.md",
    "13_PROJECT_READINESS_ASSESSMENT.md",
    "14_AUDIT_COVERAGE_AND_MISSING_SOURCES.md",
    "MASTER_ISSUES.json",
    "MASTER_ISSUES.csv",
    "SHA256SUMS.txt",
]

failures = []
checks = 0


def check(cond, msg):
    global checks
    checks += 1
    if not cond:
        failures.append(msg)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    # 1. files
    for name in REQUIRED_FILES:
        p = os.path.join(HERE, name)
        check(os.path.isfile(p), "missing required file: %s" % name)
    if failures:
        report()
        return 1

    # 2. load json
    with open(os.path.join(HERE, "MASTER_ISSUES.json"), encoding="utf-8") as f:
        doc = json.load(f)
    issues = doc["issues"]
    ids = [x["id"] for x in issues]

    check(len(ids) == len(set(ids)), "duplicate issue ids")
    check(all(re.fullmatch(r"CODOL-ISSUE-\d{4}", i) for i in ids), "issue id format")

    # sequential
    nums = sorted(int(i.split("-")[-1]) for i in ids)
    check(nums == list(range(1, len(nums) + 1)),
          "issue ids are not sequential 0001..N: first=%s last=%s" % (nums[:5], nums[-5:]))

    idset = set(ids)
    for it in issues:
        # 3.
        check(it["status"] in VALID_STATUS, "%s bad status %r" % (it["id"], it["status"]))
        check(it["priority"] in VALID_PRIO, "%s bad priority %r" % (it["id"], it["priority"]))
        # 4.
        for d in it.get("depends_on", []):
            check(d in idset, "%s depends on unknown %s" % (it["id"], d))
            check(d != it["id"], "%s depends on itself" % it["id"])
        # 5.
        check(bool(it.get("evidence")), "%s has no evidence path" % it["id"])
        for e in it.get("evidence", []):
            check(isinstance(e, str) and e.strip(), "%s has empty evidence entry" % it["id"])
        # 6.
        if it["priority"] == "P0":
            check(bool(it.get("acceptance")), "%s is P0 without acceptance" % it["id"])
            check(it["status"] not in CLOSED, "%s is P0 but marked closed" % it["id"])
        # sanity: closed issues must not be blockers
        if it["status"] in CLOSED:
            check(not it.get("blocks_playable"),
                  "%s is closed (%s) but still flagged blocks_playable" % (it["id"], it["status"]))

    # 7. csv agreement
    with open(os.path.join(HERE, "MASTER_ISSUES.csv"), encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    check(len(rows) == len(issues), "csv rows (%d) != json issues (%d)" % (len(rows), len(issues)))
    check({r["id"] for r in rows} == idset, "csv ids != json ids")
    for r in rows:
        src = next(x for x in issues if x["id"] == r["id"])
        check(r["status"] == src["status"], "csv status mismatch %s" % r["id"])
        check(r["priority"] == src["priority"], "csv priority mismatch %s" % r["id"])

    # md agreement: 03 has one "### ID — title" detail block per unresolved issue.
    # Cross-references inside prose are allowed and must not count.
    with open(os.path.join(HERE, "03_MASTER_UNRESOLVED_ISSUES.md"), encoding="utf-8") as f:
        md = f.read()
    md_ids = set(re.findall(r"^### (CODOL-ISSUE-\d{4}) —", md, re.M))
    expected_open = {it["id"] for it in issues if it["status"] not in CLOSED}
    check(md_ids == expected_open,
          "03 md detail blocks (%d) != unresolved json ids (%d); missing=%s extra=%s" % (
              len(md_ids), len(expected_open),
              sorted(expected_open - md_ids)[:5], sorted(md_ids - expected_open)[:5]))

    # 04 P0 agreement
    with open(os.path.join(HERE, "04_P0_CRITICAL_BLOCKERS.md"), encoding="utf-8") as f:
        p0md = f.read()
    p0_ids_md = set(re.findall(r"^### (CODOL-ISSUE-\d{4})", p0md, re.M))
    p0_ids_json = {it["id"] for it in issues if it["priority"] == "P0" and it["status"] not in CLOSED}
    check(p0_ids_md == p0_ids_json,
          "04 P0 ids (%s) != json P0 ids (%s)" % (sorted(p0_ids_md), sorted(p0_ids_json)))

    # 8. stats consistency: counts stated in 00_INDEX must match
    total = len(issues)
    unresolved = sum(1 for it in issues if it["status"] not in CLOSED)
    by_prio = {}
    for p in ("P0", "P1", "P2", "P3", "NONE"):
        by_prio[p] = sum(1 for it in issues if it["priority"] == p)
    with open(os.path.join(HERE, "00_INDEX.md"), encoding="utf-8") as f:
        idx = f.read()

    def idx_num(pattern):
        m = re.search(pattern, idx)
        return int(m.group(1)) if m else None

    check(idx_num(r"未解决问题总数为 \*\*(\d+)\*\*") == unresolved,
          "00_INDEX unresolved count != %d" % unresolved)
    check(idx_num(r"发现问题总数 \*\*(\d+)\*\*") == total,
          "00_INDEX total count != %d" % total)
    for p in ("P0", "P1", "P2", "P3"):
        got = idx_num(r"\| %s \| (\d+) \|" % p)
        check(got == by_prio[p], "00_INDEX %s count %r != %d" % (p, got, by_prio[p]))

    # 9. SHA256SUMS
    sums_path = os.path.join(HERE, "SHA256SUMS.txt")
    with open(sums_path, encoding="utf-8") as f:
        listed = {}
        for line in f:
            line = line.strip()
            if not line:
                continue
            h, name = line.split(None, 1)
            listed[name.lstrip("*")] = h
    for name, want in listed.items():
        p = os.path.join(HERE, name)
        check(os.path.isfile(p), "SHA256SUMS lists missing file %s" % name)
        if os.path.isfile(p):
            got = sha256(p)
            check(got == want, "sha256 mismatch for %s" % name)
    # every deliverable except SHA256SUMS itself must be listed
    for name in REQUIRED_FILES:
        if name == "SHA256SUMS.txt":
            continue
        check(name in listed, "SHA256SUMS missing entry for %s" % name)

    report()
    return 0 if not failures else 1


def report():
    print("=" * 60)
    print("verify_audit.py")
    print("=" * 60)
    print("checks run : %d" % checks)
    print("failures   : %d" % len(failures))
    if failures:
        for f in failures:
            print("  FAIL  " + f)
        print("\nRESULT: FAILED")
    else:
        print("RESULT: ALL CHECKS PASSED")


if __name__ == "__main__":
    sys.exit(main())
