#!/usr/bin/env python3
"""s138_p21_1x: 逐字段验证 21/1 的 #02/#17/#22/#24/#29 与 playlist 属性的硬对应。"""
import json
import re
import sys
import zlib
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, "tools")
import s138_21_resolve as R

CORPUS = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
P = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\playlist_plain.txt"

lines = open(P, encoding="latin1").read().splitlines()
pl = {}
cur = None
for l in lines:
    m = re.match(r"^\s*playlist\s+(\d+)\s*$", l)
    if m:
        cur = int(m.group(1))
        pl[cur] = {"r3265": None, "r1011": None, "maxparty": None, "maxhuman": None,
                   "vs": None, "cat": None, "gts": set(), "maps": []}
        continue
    if cur is None:
        continue
    for key, name in (("3265", "r3265"), ("1011", "r1011")):
        m = re.match(r"^\s*rule\s+%s\s+(\S+)" % key, l)
        if m:
            pl[cur][name] = int(m.group(1)) if m.group(1).isdigit() else m.group(1)
    for key, name in (("maxparty", "maxparty"), ("maxhumanplayersperteam", "maxhuman")):
        m = re.match(r"^\s*%s\s+(\S+)" % key, l)
        if m:
            pl[cur][name] = int(m.group(1)) if m.group(1).isdigit() else m.group(1)
    m = re.match(r'^\s*vsrule\s+"?([0-9Vv]+)"?', l)
    if m:
        pl[cur]["vs"] = m.group(1)
    m = re.match(r"^\s*category\s+(\S+)", l)
    if m:
        pl[cur]["cat"] = m.group(1)
    m = re.match(r"^\s*([a-z0-9_]+)\s*,\s*([a-z0-9_]+)\s*,\s*\d+", l)
    if m:
        pl[cur]["maps"].append(m.group(1))
        pl[cur]["gts"].add(m.group(2))

corpus = json.load(open(CORPUS, encoding="utf-8"))
n = 0
stat = Counter()
for r in corpus:
    if r["svc"] != 21 or r["task"] != 1:
        continue
    els, _ = R.parse(bytes.fromhex(r["payload"]))
    vals = {}
    for i, (t, v) in enumerate(els):
        if t in (0x07, 0x08):
            vals[i] = v & 0xffffffff
    pid = vals.get(20)
    d = pl.get(pid)
    if not d:
        continue
    ok3265 = (vals.get(2) == d["r3265"])
    stat[("3265==#02", ok3265)] += 1
    stat[("#17", vals.get(17), "r1011", d["r1011"])] += 1
    stat[("#22", vals.get(22), "mapn", len(d["maps"]))] += 1
    if n < 20:
        print("pl=%-4s #02=%-3s r3265=%-3s %s | #17=%s r1011=%s | #22=%s mapn=%d | #29=%s" % (
            pid, vals.get(2), d["r3265"], "OK" if ok3265 else "X",
            vals.get(17), d["r1011"], vals.get(22), len(d["maps"]), vals.get(29)))
    n += 1
print("\nsamples", n)
for k, c in sorted(stat.items(), key=lambda x: str(x)):
    print("  ", k, c)
