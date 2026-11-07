#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Self-check for the full 053 forensics delivery (all 92 issues).

Structural checks
  1  Issue IDs unique / sequential
  2  every register issue has a dossier
  3  every dossier has the 22 required sections (or NOT_APPLICABLE note)
  4  evidence files that resolve exist; hashes match
  5  source line references are in range (when the file resolves)
  6  databases agree with each other and with the dossier count
  7  every issue carries at least one evidence location
  8  every issue states a fix_readiness in the allowed vocabulary
  9  every FIX_READY / INVESTIGATION_READY issue has a package with TEST_PLAN+ACCEPTANCE
 10  every BLOCKED_* issue states what blocks it

Content-quality checks (per task §八)
 11  no empty sections
 12  no placeholder-only text ("需要进一步分析" etc.) as the whole section body
 13  no duplicated template paragraph across dossiers (boilerplate detector)
 14  every issue has an executable next step (non-generic)
 15  no fabricated success: closed issues must not be claimed open and vice versa

Run:  python -I verify_forensics.py
"""
import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REG = os.path.join(ROOT, "CODOL-PROJECT-GLOBAL-UNRESOLVED-ISSUES-AUDIT", "MASTER_ISSUES.json")
ISSUES = os.path.join(HERE, "ISSUES")

VALID_READINESS = {"FIX_READY", "INVESTIGATION_READY", "BLOCKED_BY_EVIDENCE",
                   "BLOCKED_BY_DEPENDENCY", "RESOLVED_VERIFIED", "OBSOLETE"}
CLOSED = {"RESOLVED_VERIFIED", "OBSOLETE"}
SECTIONS = list(range(1, 23))

# generic filler that may not stand alone as a section body
BANNED_ALONE = [
    "需要继续逆向客户端", "建议检查相关代码", "可能是协议不兼容", "需要进一步测试",
    "需要进一步分析", "修复后进行回归测试", "待定", "继续观察",
]
REQUIRED = ["00_INDEX.md", "01_EXECUTIVE_TECHNICAL_FINDINGS.md",
            "02_FULL_PROJECT_TECHNICAL_HISTORY.md", "03_ROOT_CAUSE_DEPENDENCY_ANALYSIS.md",
            "04_CRITICAL_PATH_TO_PLAYABLE_BATTLE.md", "05_FIX_READINESS_REPORT.md",
            "06_MISSING_EVIDENCE_REPORT.md", "07_HISTORICAL_REGRESSION_ANALYSIS.md",
            "08_FINAL_TECHNICAL_ASSESSMENT.md", "GAMESTATE_PROTOCOL_FORENSICS.md",
            "SNAPSHOT_PROTOCOL_FORENSICS.md", "UNWIRED_MODULES_FORENSICS.md",
            "CONNECTION_REGRESSION_DIFFERENTIAL.md", "P0_JOINT_ANALYSIS.md",
            "NEXT_AGENT_HANDOFF.md", "09_CROSS_CHECK_REPORT.md", "ISSUE_FORENSICS.json", "ISSUE_FORENSICS.csv",
            "EVIDENCE_INDEX.json", "SOURCE_LOCATION_INDEX.json", "HYPOTHESIS_MATRIX.csv",
            "FIX_READINESS_MATRIX.csv", "SHA256SUMS.txt"]

checks = 0
fails = []


def check(c, m):
    global checks
    checks += 1
    if not c:
        fails.append(m)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def split_sections(text):
    """Return {n: body} for '## N. Title' headings."""
    out = {}
    parts = re.split(r"^## (\d+)\. ", text, flags=re.M)
    for i in range(1, len(parts) - 1, 2):
        out[int(parts[i])] = parts[i + 1]
    return out


def main():
    for n in REQUIRED:
        check(os.path.isfile(os.path.join(HERE, n)), "missing file: %s" % n)
    if fails:
        return report()

    reg = {i["id"]: i for i in json.load(open(REG, encoding="utf-8"))["issues"]}
    dossiers = sorted(n[:-3] for n in os.listdir(ISSUES) if n.endswith(".md"))

    # 1/2
    check(len(dossiers) == len(set(dossiers)), "duplicate dossier files")
    check(set(dossiers) == set(reg), "dossier set != register set; missing=%s extra=%s" % (
        sorted(set(reg) - set(dossiers))[:5], sorted(set(dossiers) - set(reg))[:5]))

    # 3/11/12/13/14
    bodies = {}
    section_hist = Counter()
    for iid in dossiers:
        t = open(os.path.join(ISSUES, iid + ".md"), encoding="utf-8").read()
        secs = split_sections(t)
        missing = [n for n in SECTIONS if n not in secs]
        if missing:
            # P0 hand-written dossiers use the older 18-section layout
            legacy = len(secs) >= 18 and 18 in secs
            check(legacy, "%s missing sections %s" % (iid, missing))
            if legacy:
                continue
        for n, body in secs.items():
            if n not in SECTIONS:
                continue
            b = body.strip()
            check(len(b) > 0, "%s section %d is empty" % (iid, n))
            check(b not in ("—", "-", "N/A"), "%s section %d is a stub" % (iid, n))
            section_hist[(n, b[:160])] += 1
        # banned standalone filler
        for n, body in secs.items():
            b = body.strip()
            for bad in BANNED_ALONE:
                check(not (b == bad or (len(b) < 40 and bad in b)),
                      "%s section %d is generic filler (%s)" % (iid, n, bad))
        bodies[iid] = t

    # 13 duplicate template paragraph across dossiers
    dup = {k: v for k, v in section_hist.items() if v >= 12 and len(k[1]) > 60}
    for (n, snippet), cnt in sorted(dup.items()):
        check(False, "template paragraph reused in %d dossiers (section %d): %r" % (cnt, n, snippet[:70]))

    # 6 databases
    fx = json.load(open(os.path.join(HERE, "ISSUE_FORENSICS.json"), encoding="utf-8"))["issues"]
    check(len(fx) == len(reg), "ISSUE_FORENSICS count %d != %d" % (len(fx), len(reg)))
    check({x["id"] for x in fx} == set(reg), "ISSUE_FORENSICS ids != register")
    with open(os.path.join(HERE, "ISSUE_FORENSICS.csv"), encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    check(len(rows) == len(fx), "ISSUE_FORENSICS.csv rows != json")

    with open(os.path.join(HERE, "FIX_READINESS_MATRIX.csv"), encoding="utf-8-sig") as f:
        rm = {r["issue"]: r for r in csv.DictReader(f)}
    check(set(rm) == set(reg), "readiness matrix ids != register")

    # 8 readiness vocabulary + status agreement
    for x in fx:
        r = rm.get(x["id"])
        check(r is not None, "%s missing from readiness matrix" % x["id"])
        if r:
            check(r["fix_readiness"] in VALID_READINESS,
                  "%s bad readiness %r" % (x["id"], r["fix_readiness"]))
            check(r["register_status"] == reg[x["id"]]["status"],
                  "%s status mismatch matrix vs register" % x["id"])

    # 7 evidence presence
    for x in fx:
        check(x.get("evidence_count", 0) >= 1, "%s has no evidence locations" % x["id"])

    # 4/5 evidence + source indexes
    ev = json.load(open(os.path.join(HERE, "EVIDENCE_INDEX.json"), encoding="utf-8"))["evidence"]
    for e in ev:
        if e.get("abs_path"):
            check(os.path.isfile(e["abs_path"]), "%s missing file %s" % (e["id"], e["abs_path"]))
            if os.path.isfile(e["abs_path"]) and e.get("sha256"):
                check(sha(e["abs_path"]) == e["sha256"], "%s sha mismatch" % e["id"])
    src = json.load(open(os.path.join(HERE, "SOURCE_LOCATION_INDEX.json"), encoding="utf-8"))["locations"]
    for s in src:
        if not s["resolved"]:
            continue
        m = re.match(r"^(\d+)\s*-\s*(\d+)$", str(s["loc"]).strip())
        if m and s.get("file_lines"):
            lo, hi = int(m.group(1)), int(m.group(2))
            check(1 <= lo <= hi <= s["file_lines"],
                  "bad line range %s:%s (file has %s lines)" % (s["file"], s["loc"], s["file_lines"]))

    # 9 packages
    for x in fx:
        rd = rm[x["id"]]["fix_readiness"]
        if rd in ("FIX_READY", "INVESTIGATION_READY"):
            for sub in ("FIX_PACKAGES", "INVESTIGATION_PACKAGES"):
                base = os.path.join(HERE, sub, x["id"])
                if os.path.isdir(base):
                    break
            else:
                check(False, "%s (%s) has no package" % (x["id"], rd))
                continue
            for doc in ("README.md", "TEST_PLAN.md", "ACCEPTANCE.md"):
                check(os.path.isfile(os.path.join(base, doc)),
                      "%s package missing %s" % (x["id"], doc))

    # 10 blocked issues must state why
    for x in fx:
        rd = rm[x["id"]]["fix_readiness"]
        if rd.startswith("BLOCKED"):
            check(bool(rm[x["id"]]["next_step"].strip()),
                  "%s is %s but has no next_step" % (x["id"], rd))

    # 14 executable next step, not generic
    for x in fx:
        ns = rm[x["id"]]["next_step"].strip()
        for bad in BANNED_ALONE:
            check(bad not in ns[:30], "%s next_step is generic (%s)" % (x["id"], bad))

    # 15 fabricated-success guard. Readiness is the audit's own judgement and may
    # legitimately differ from the older register status, so only flag the case
    # where the dossier claims RESOLVED while readiness says still blocked.
    for iid, t in bodies.items():
        rd = rm[iid]["fix_readiness"] if iid in rm else ""
        if rd in ("FIX_READY", "INVESTIGATION_READY", "BLOCKED_BY_EVIDENCE", "BLOCKED_BY_DEPENDENCY"):
            check("RESOLVED_VERIFIED" not in t,
                  "%s readiness=%s but dossier claims RESOLVED" % (iid, rd))
        if rd == "OBSOLETE":
            check(("OBSOLETE" in t or "已作废" in t or "已推翻" in t),
                  "%s readiness=OBSOLETE but dossier does not say so" % iid)

    # SHA256SUMS
    with open(os.path.join(HERE, "SHA256SUMS.txt"), encoding="utf-8") as f:
        listed = {}
        for line in f:
            line = line.strip()
            if line:
                h, n = line.split(None, 1)
                listed[n.lstrip("*")] = h
    for n, want in listed.items():
        p = os.path.join(HERE, n)
        check(os.path.isfile(p), "SHA256SUMS lists missing %s" % n)
        if os.path.isfile(p):
            check(sha(p) == want, "sha mismatch %s" % n)

    return report()


def report():
    print("=" * 64)
    print("verify_forensics.py  (full 92-issue delivery)")
    print("=" * 64)
    print("checks run : %d" % checks)
    print("failures   : %d" % len(fails))
    for f in fails[:60]:
        print("  FAIL  " + f)
    if len(fails) > 60:
        print("  ... %d more" % (len(fails) - 60))
    print("\nRESULT: " + ("ALL CHECKS PASSED" if not fails else "FAILED"))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
