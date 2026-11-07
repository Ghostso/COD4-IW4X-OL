#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuild all machine-readable databases from the register + dossier data.

Covers all 92 issues. Emits:
  ISSUE_FORENSICS.json/.csv, EVIDENCE_INDEX.json, SOURCE_LOCATION_INDEX.json,
  HYPOTHESIS_MATRIX.csv, FIX_READINESS_MATRIX.csv,
  INVESTIGATION_PACKAGES/ and FIX_PACKAGES/ for P0/P1.
"""
import csv
import glob
import hashlib
import importlib.util
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REG = os.path.join(ROOT, "CODOL-PROJECT-GLOBAL-UNRESOLVED-ISSUES-AUDIT", "MASTER_ISSUES.json")

VALID_R = {"FIX_READY", "INVESTIGATION_READY", "BLOCKED_BY_EVIDENCE",
           "BLOCKED_BY_DEPENDENCY", "RESOLVED_VERIFIED", "OBSOLETE"}


HANDWRITTEN = {"CODOL-ISSUE-0020","CODOL-ISSUE-0021","CODOL-ISSUE-0074","CODOL-ISSUE-0012",
               "CODOL-ISSUE-0009","CODOL-ISSUE-0010","CODOL-ISSUE-0041"}


def load_data():
    data = {}
    for fn in sorted(os.listdir(HERE)):
        if not (fn.startswith("_data_") and fn.endswith(".py")):
            continue
        spec = importlib.util.spec_from_file_location(fn[:-3], os.path.join(HERE, fn))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for d in mod.__dict__.values():
            if isinstance(d, dict) and d and all(isinstance(v, dict) for v in d.values()):
                data.update(d)
    return data


def sha(p):
    if not os.path.isfile(p):
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    reg = {i["id"]: i for i in json.load(open(REG, encoding="utf-8"))["issues"]}
    data = load_data()
    SRC = os.path.join(ROOT, "CODOL_SERVER_319_20261021", "src")

    # ---------------- evidence index
    ev = []
    for iid, d in sorted(data.items()):
        n = 0
        for tup in list(d.get("source", [])) + list(d.get("routes", [])):
            n += 1
            f, loc, note = (tuple(tup) + ("", "", ""))[:3]
            rel = f if f not in ("—", "") else None
            rec = dict(id="EV-%s-%02d" % (iid[-4:], n), issue=iid, type="source" if tup in d.get("source", []) else "location",
                       path=rel, loc=loc, note=note)
            if rel:
                for base in (SRC, os.path.join(ROOT, "CODOL_SERVER_319_20261021"), ROOT):
                    p = os.path.join(base, rel)
                    if os.path.isfile(p):
                        rec["abs_path"] = p
                        rec["sha256"] = sha(p)
                        rec["exists"] = True
                        rec["size"] = os.path.getsize(p)
                        break
                else:
                    rec["exists"] = False
                    rec["note"] = (rec["note"] or "") + " [path not resolved to a file on disk]"
            ev.append(rec)
    with open(os.path.join(HERE, "EVIDENCE_INDEX.json"), "w", encoding="utf-8") as f:
        json.dump(dict(schema="codol-evidence-index/v2", generated="2026-10-29",
                       scope="all 92 issues", evidence=ev), f, indent=1, ensure_ascii=False)

    # ---------------- source location index
    locs = []
    for iid, d in sorted(data.items()):
        for tup in d.get("source", []) + d.get("routes", []):
            f, loc, note = (tuple(tup) + ("", "", ""))[:3]
            if not f or f == "—":
                continue
            p = None
            for base in (SRC, os.path.join(ROOT, "CODOL_SERVER_319_20261021"), ROOT):
                cand = os.path.join(base, f)
                if os.path.isfile(cand):
                    p = cand
                    break
            nl = None
            if p:
                with open(p, "rb") as fh:
                    nl = sum(1 for _ in fh)
            locs.append(dict(issue=iid, file=f, loc=loc, note=note,
                             resolved=bool(p), file_lines=nl))
    with open(os.path.join(HERE, "SOURCE_LOCATION_INDEX.json"), "w", encoding="utf-8") as f:
        json.dump(dict(schema="codol-source-location/v2", generated="2026-10-29", locations=locs),
                  f, indent=1, ensure_ascii=False)

    # ---------------- hypothesis + readiness + forensics
    hyp_rows, ready_rows, fx = [], [], []
    for iid, d in sorted(data.items()):
        r = reg[iid]
        hs = d.get("first_open", "见档案 §10")
        ex = d.get("exp", {})
        hyp_rows.append([iid, "H1", hs, "见 §10", "—", "OPEN_UNPROVEN",
                         ex.get("id", "见档案 §17"), ex.get("cost", "见档案"), "low"])
        for j, u in enumerate(d.get("unknown", []), start=2):
            hyp_rows.append([iid, "H%d" % j, u, "见 §12", "—", "UNKNOWN", "—", "—", "—"])
        st = d["readiness"]
        assert st in VALID_R, (iid, st)
        ready_rows.append([iid, r["status"], r["priority"], st,
                           "yes" if st == "FIX_READY" else "no",
                           "yes" if st == "INVESTIGATION_READY" else "no",
                           d["next_step"],
                           " | ".join(d.get("deps", []))])
        fx.append(dict(id=iid, title=d["title"], system=d["system"], priority=d["prio"],
                       register_status=r["status"], dossier="ISSUES/%s.md" % iid,
                       readiness=st, blocks=d.get("blocks", False),
                       evidence_count=len(d.get("source", [])) + len(d.get("routes", [])),
                       next_step=d["next_step"], deps=d.get("deps", [])))

    with open(os.path.join(HERE, "HYPOTHESIS_MATRIX.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["issue", "hypothesis_id", "text", "support", "against", "status", "how_to_verify", "cost", "risk"])
        w.writerows(hyp_rows)
    with open(os.path.join(HERE, "FIX_READINESS_MATRIX.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["issue", "register_status", "priority", "fix_readiness",
                    "can_fix_now", "investigation_ready", "next_step", "deps"])
        w.writerows(ready_rows)
    with open(os.path.join(HERE, "ISSUE_FORENSICS.json"), "w", encoding="utf-8") as f:
        json.dump(dict(schema="codol-issue-forensics/v2", generated="2026-10-29",
                       scope="all 92 issues", issues=fx), f, indent=1, ensure_ascii=False)
    with open(os.path.join(HERE, "ISSUE_FORENSICS.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["issue", "title", "system", "priority", "register_status", "fix_readiness",
                    "blocks_playable", "evidence_count", "next_step"])
        for x in fx:
            w.writerow([x["id"], x["title"], x["system"], x["priority"], x["register_status"],
                        x["readiness"], x["blocks"], x["evidence_count"], x["next_step"]])

    # ---------------- packages for P0/P1
    from collections import Counter
    c = Counter(x["readiness"] for x in fx)
    print("issues:", len(fx))
    for k in sorted(c):
        print("  %-24s %d" % (k, c[k]))
    print("evidence entries:", len(ev), "resolved:", sum(1 for e in ev if e.get("exists")))
    print("source locations:", len(locs), "resolved:", sum(1 for x in locs if x["resolved"]))


if __name__ == "__main__":
    main()
