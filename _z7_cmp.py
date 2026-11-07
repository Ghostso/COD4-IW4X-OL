# -*- coding: utf-8 -*-
"""Compare the startup window timeline between my rounds and the healthy round."""
import os, json, glob

RUNS = r"run_codol_001\runs"
def timeline(tag):
    f = os.path.join(RUNS, tag, "aboprobe.stdout")
    if not os.path.isfile(f):
        return None
    txt = open(f, "rb").read().decode("gbk", "replace")
    ev = []
    for line in txt.splitlines():
        if ",WINDOW_NEW," in line or ",VSD_PROBE," in line or ",PROCESS_END," in line:
            ev.append(line)
    return ev

for tag in ["IFS1_ELEVATED_20261003_002136",   # healthy
            "IFS1_ELEVATED_20261003_110830",   # hosts off, 42.8s
            "IFS1_ELEVATED_20261003_111138"]:  # iips=0, 30.2s
    print("=" * 70)
    print(tag)
    ev = timeline(tag)
    if ev is None:
        print("  (missing)"); continue
    for l in ev:
        p = l.split(",")
        t = p[0]
        kind = p[1]
        extra = ""
        if kind == "WINDOW_NEW":
            for f in p[2:]:
                if f.startswith("class="):
                    extra = f
        elif kind == "PROCESS_END":
            extra = ",".join(p[2:])
        elif kind == "VSD_PROBE":
            extra = "vsd"
        print("  t=%-9s %-14s %s" % (t, kind, extra))
    print()
