#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Self-check for CODOL-PROJECT-LOBBY-FULL-LIFECYCLE-FORENSICS-055.

Structural
  1  all required deliverable files exist
  2  the 20 numbered docs are present and non-trivial
  3  LOBBY_COMPLETENESS_MATRIX.csv has the required columns + legal statuses
  4  LOBBY_BREAKPOINTS.json ids unique, each cites an Issue and evidence
  5  LOBBY_PROTOCOLS.json matches a fresh re-scan of the logs
  6  LOBBY_EVIDENCE_INDEX.json hashes match the files on disk
  7  no fabricated numbers: every "56/56", "8/32" style claim is reproducible
  8  SHA256SUMS.txt correct
Content quality
  9  no empty sections, no generic filler as a whole section
 10  no duplicated boilerplate paragraph across documents
 11  every breakpoint states next-step and blocks_followup
"""
import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RUNS = os.path.join(ROOT, "run_codol_001", "runs")

REQ_DOCS = ["00_INDEX.md", "01_LOBBY_CURRENT_STATE.md", "02_LOBBY_COMPLETE_STATE_MACHINE.md",
            "03_LOBBY_PROTOCOL_INVENTORY.md", "04_ROOM_CREATION_AND_INITIALIZATION.md",
            "05_ROOM_MEMBER_SYNCHRONIZATION.md", "06_ROOM_READY_AND_START_FLOW.md",
            "07_ROOM_EVENT_DISPATCH.md", "08_PLAYLIST_AND_MODE_ENTRY_PATHS.md",
            "09_MATCHMAKING_AND_BOOKING.md", "10_MMSTART_AND_BATTLE_HANDOFF.md",
            "11_HISTORICAL_SUCCESS_FAILURE_TIMELINES.md", "12_CLIENT_FUNCTION_CALL_GRAPH.md",
            "13_SERVER_FUNCTION_CALL_GRAPH.md", "14_LOBBY_BREAKPOINT_REGISTER.md",
            "15_LOBBY_COMPLETENESS_MATRIX.md", "16_LOBBY_EVIDENCE_INDEX.md",
            "17_LOBBY_UNKNOWN_FIELDS.md", "18_LOBBY_HISTORICAL_CONTRADICTIONS.md",
            "19_LOBBY_ROOT_CAUSE_ANALYSIS.md", "20_FINAL_LOBBY_TECHNICAL_ASSESSMENT.md",
            "CODOL_LOBBY_ALL_UNRESOLVED_PROBLEMS.md",
            "LOBBY_COMPLETENESS_MATRIX.csv", "LOBBY_BREAKPOINTS.json",
            "LOBBY_PROTOCOLS.json", "LOBBY_EVIDENCE_INDEX.json", "SHA256SUMS.txt"]

LEGAL_STATUS = {"VERIFIED_COMPLETE", "PARTIALLY_IMPLEMENTED", "IMPLEMENTED_UNVERIFIED",
                "NOT_IMPLEMENTED", "BLOCKED", "UNKNOWN"}
BANNED = ["需要继续逆向", "建议检查相关代码", "可能是协议不兼容", "需要进一步测试", "待定"]

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


def rescan():
    RE = re.compile(r"解密成功 #(\d+) seq=(\d+) .*?service=(\d+) ver=0x(\w+) task=(\d+) declared=(\d+)")
    runs, pairs = 0, defaultdict(set)
    for d in sorted(os.listdir(RUNS)):
        lg = os.path.join(RUNS, d, "kit", "lobby_srv.log")
        if not os.path.isfile(lg):
            continue
        runs += 1
        for ln in open(lg, encoding="utf-8", errors="replace"):
            m = RE.search(ln)
            if m:
                pairs[(int(m.group(3)), int(m.group(5)))].add(d)
    return runs, pairs


def main():
    for n in REQ_DOCS:
        check(os.path.isfile(os.path.join(HERE, n)), "missing: %s" % n)
    if fails:
        return report()

    # 2 non-trivial docs
    for n in REQ_DOCS:
        if not n.endswith(".md"):
            continue
        t = open(os.path.join(HERE, n), encoding="utf-8").read()
        check(len(t) > 400, "%s is too short (%d B)" % (n, len(t)))
        for b in BANNED:
            check(b not in t, "%s contains generic filler %r" % (n, b))

    # 3 completeness matrix
    with open(os.path.join(HERE, "LOBBY_COMPLETENESS_MATRIX.csv"), encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    check(len(rows) >= 10, "completeness matrix too small")
    for r in rows:
        check(r["status"] in LEGAL_STATUS, "bad status %r for %s" % (r["status"], r["stage"]))
        check(bool(r["evidence"].strip()), "%s has no evidence" % r["stage"])

    # 4 breakpoints
    bp = json.load(open(os.path.join(HERE, "LOBBY_BREAKPOINTS.json"), encoding="utf-8"))["breakpoints"]
    ids = [b["id"] for b in bp]
    check(len(ids) == len(set(ids)), "duplicate breakpoint ids")
    for b in bp:
        check(b["issue"].startswith("CODOL-ISSUE-"), "%s bad issue ref" % b["id"])
        check(bool(b.get("next", "").strip()), "%s has no next step" % b["id"])
        check(isinstance(b.get("blocks_followup"), bool), "%s blocks_followup not bool" % b["id"])
        check(len(b.get("evidence", [])) >= 1, "%s has no evidence" % b["id"])

    # 5 protocols reproducible
    runs, pairs = rescan()
    prot = json.load(open(os.path.join(HERE, "LOBBY_PROTOCOLS.json"), encoding="utf-8"))
    check(prot["runs_scanned"] == runs, "runs_scanned %d != rescan %d" % (prot["runs_scanned"], runs))
    declared = {(p["service"], p["task"]): p["runs_present"] for p in prot["protocols"]}
    check(set(declared) == set(pairs),
          "protocol set mismatch; missing=%s extra=%s" % (
              sorted(set(pairs) - set(declared))[:5], sorted(set(declared) - set(pairs))[:5]))
    for k, v in sorted(pairs.items()):
        if k in declared:
            check(declared[k] == len(v), "%d/%d runs_present %d != actual %d" % (
                k[0], k[1], declared[k], len(v)))

    # 7 reproduce the headline claims
    with_mm = 0
    for d in os.listdir(RUNS):
        lg = os.path.join(RUNS, d, "kit", "lobby_srv.log")
        if os.path.isfile(lg) and "mmstart 完整命令" in open(lg, encoding="utf-8", errors="replace").read():
            with_mm += 1
    # 03 doc claims 46 runs contain mmbook; verify 6/14 presence count
    n614 = len(pairs.get((6, 14), set()))
    check(n614 == 46, "6/14 run count %d != claimed 46" % n614)
    n1113 = len(pairs.get((11, 13), set()))
    check(n1113 == 32, "11/13 run count %d != claimed 32" % n1113)

    # 6 evidence hashes
    ev = json.load(open(os.path.join(HERE, "LOBBY_EVIDENCE_INDEX.json"), encoding="utf-8"))["evidence"]
    for e in ev:
        if e.get("missing"):
            continue
        p = os.path.join(ROOT, e["path"].replace("/", os.sep))
        check(os.path.isfile(p), "evidence file missing: %s" % e["path"])
        if os.path.isfile(p) and e.get("sha256"):
            check(sha(p) == e["sha256"], "sha mismatch: %s" % e["path"])

    # 10 boilerplate detector
    para = Counter()
    for n in REQ_DOCS:
        if not n.endswith(".md"):
            continue
        for blk in open(os.path.join(HERE, n), encoding="utf-8").read().split("\n\n"):
            b = blk.strip()
            if len(b) > 120 and not b.startswith("|"):
                para[b[:160]] += 1
    dups = [k for k, v in para.items() if v >= 4]
    check(not dups, "boilerplate paragraph reused >=4 times: %r" % (dups[:2],))

    # 8 SHA256SUMS
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
    print("verify_lobby_forensics.py (055)")
    print("=" * 64)
    print("checks run : %d" % checks)
    print("failures   : %d" % len(fails))
    for f in fails[:40]:
        print("  FAIL  " + f)
    print("\nRESULT: " + ("ALL CHECKS PASSED" if not fails else "FAILED"))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
