#!/usr/bin/env python3
"""s138_p21_1dist: 21/1 每个槽位分布, 并交叉 playlist 属性(试图给 #02/#17/#22/#29 命名)。"""
import json
import re
import sys
from collections import Counter, defaultdict

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
        pl[cur] = {"maxparty": None, "maxhuman": None, "vs": None, "cat": None, "mapn": 0}
        continue
    if cur is None:
        continue
    for key in ("maxparty", "maxhumanplayersperteam"):
        m = re.match(r"^\s*%s\s+(\S+)" % key, l)
        if m:
            pl[cur][key.split("max")[1] if False else ("maxparty" if key == "maxparty" else "maxhuman")] = m.group(1)
    m = re.match(r'^\s*vsrule\s+"?([0-9Vv]+)"?', l)
    if m:
        pl[cur]["vs"] = m.group(1)
    m = re.match(r"^\s*category\s+(\S+)", l)
    if m:
        pl[cur]["cat"] = m.group(1)
    m = re.match(r"^\s*[a-z0-9_]+\s*,\s*[a-z0-9_]+\s*,\s*\d+", l)
    if m:
        pl[cur]["mapn"] += 1

corpus = json.load(open(CORPUS, encoding="utf-8"))
slotvals = defaultdict(Counter)
rows = []
for r in corpus:
    if r["svc"] != 21 or r["task"] != 1:
        continue
    els, _ = R.parse(bytes.fromhex(r["payload"]))
    vals = {}
    for i, (t, v) in enumerate(els):
        if t in (0x07, 0x08):
            vals[i] = v & 0xffffffff
        elif t == 0x10:
            vals[i] = "str"
        elif t == 0x13:
            vals[i] = "blob%d" % len(v)
        elif t == 0x0a:
            vals[i] = "u64"
    for i, v in vals.items():
        slotvals[i][v] += 1
    rows.append((vals, r["run"]))

for i in sorted(slotvals):
    c = slotvals[i]
    if i in (3, 5):    # client name strings
        print("#%02d: %s" % (i, dict(c)))
    else:
        top = c.most_common(8)
        print("#%02d: %s" % (i, top))

print("\n#02 vs playlist:")
cnt = Counter()
for vals, run in rows:
    pid = vals.get(20)
    d = pl.get(pid)
    cnt[(vals.get(2), pid, d["vs"] if d else None, d["maxparty"] if d else None,
         d["maxhuman"] if d else None)] += 1
for k, v in sorted(cnt.items(), key=lambda x: str(x)):
    print("  #02=%-4s playlist=%-4s vs=%-4s maxparty=%-3s maxhuman=%-3s x%d" % (k + (v,)))
