#!/usr/bin/env python3
"""Build CSV + markdown roll-up tables from MASTER_ISSUES.json.

Single source of truth: MASTER_ISSUES.json. Everything numeric in the audit
deliverables is derived from it, so counts can be recomputed and cannot drift.

Run:  python -I build_deliverables.py
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.join(HERE, "MASTER_ISSUES.json")

VALID_STATUS = {
    "OPEN", "PARTIALLY_RESOLVED", "BLOCKED", "UNVERIFIED", "REGRESSION",
    "CONTRADICTORY_EVIDENCE", "NOT_IMPLEMENTED", "UNKNOWN", "RESOLVED_VERIFIED",
    "OBSOLETE",
}
VALID_PRIO = {"P0", "P1", "P2", "P3", "NONE"}
CLOSED = {"RESOLVED_VERIFIED", "OBSOLETE"}

CSV_FIELDS = [
    "id", "title", "system", "status", "priority", "severity",
    "blocks_playable", "first_seen_date", "first_seen_source",
    "evidence_paths", "evidence_level", "depends_on",
    "acceptance", "complexity",
]


def load(path=REG):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate(doc):
    errs = []
    issues = doc["issues"]
    seen = set()
    for it in issues:
        i = it["id"]
        if i in seen:
            errs.append("duplicate id %s" % i)
        seen.add(i)
        if it["status"] not in VALID_STATUS:
            errs.append("%s bad status %r" % (i, it["status"]))
        if it["priority"] not in VALID_PRIO:
            errs.append("%s bad priority %r" % (i, it["priority"]))
        if not it.get("evidence"):
            errs.append("%s has no evidence" % i)
        for d in it.get("depends_on", []):
            if d not in seen and d not in {x["id"] for x in issues}:
                errs.append("%s depends on unknown %s" % (i, d))
        if it["priority"] == "P0" and not it.get("acceptance"):
            errs.append("%s is P0 without acceptance criteria" % i)
    return errs


def rollup(issues):
    def count(pred):
        return sum(1 for x in issues if pred(x))
    out = {
        "total": len(issues),
        "by_status": {},
        "by_priority": {},
        "unresolved": count(lambda x: x["status"] not in CLOSED),
        "blocks_playable": count(lambda x: x.get("blocks_playable")),
    }
    for s in sorted(VALID_STATUS):
        n = count(lambda x, s=s: x["status"] == s)
        if n:
            out["by_status"][s] = n
    for p in ("P0", "P1", "P2", "P3", "NONE"):
        n = count(lambda x, p=p: x["priority"] == p)
        if n:
            out["by_priority"][p] = n
    return out


def write_csv(issues, path):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        for it in issues:
            row = {k: it.get(k, "") for k in CSV_FIELDS}
            row["evidence_paths"] = " | ".join(it.get("evidence", []))
            row["depends_on"] = " | ".join(it.get("depends_on", []))
            row["blocks_playable"] = "yes" if it.get("blocks_playable") else "no"
            w.writerow(row)


def main():
    doc = load()
    errs = validate(doc)
    if errs:
        print("VALIDATION FAILED")
        for e in errs:
            print("  -", e)
        return 1
    issues = doc["issues"]
    write_csv(issues, os.path.join(HERE, "MASTER_ISSUES.csv"))
    r = rollup(issues)
    print(json.dumps(r, indent=2, ensure_ascii=False))
    with open(os.path.join(HERE, "_work", "rollup.json"), "w", encoding="utf-8") as f:
        json.dump(r, f, indent=2, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
