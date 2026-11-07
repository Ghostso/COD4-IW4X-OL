#!/usr/bin/env python3
"""s138_p21_f17f22: 找 21/1 的 #17/#22 对应 playlist 的哪个属性。
对一个候选属性(displayorder/unlocklevelend/difficulty/minparty/maxparty/maxhuman/...)
统计 #17/#22 与它相等的命中率。
"""
import json
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, "tools")
import s138_21_resolve as R

CORPUS = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
P = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\playlist_plain.txt"

ATTRS = ["displayorder", "unlocklevelend", "difficulty", "minparty", "maxparty",
         "maxhumanplayersperteam", "onboardbonus"]
lines = open(P, encoding="latin1").read().splitlines()
pl = {}
cur = None
for l in lines:
    m = re.match(r"^\s*playlist\s+(\d+)\s*$", l)
    if m:
        cur = int(m.group(1))
        pl[cur] = {a: None for a in ATTRS}
        pl[cur]["nmaps"] = 0
        continue
    if cur is None:
        continue
    for a in ATTRS:
        m = re.match(r"^\s*%s\s+(\S+)" % a, l)
        if m:
            v = m.group(1)
            pl[cur][a] = int(v) if re.match(r"^-?\d+$", v) else v
    m = re.match(r"^\s*[a-z0-9_]+\s*,\s*[a-z0-9_]+\s*,\s*\d+\s*$", l)
    if m:
        pl[cur]["nmaps"] += 1

corpus = json.load(open(CORPUS, encoding="utf-8"))
rows = []
for r in corpus:
    if r["svc"] != 21 or r["task"] != 1:
        continue
    els, _ = R.parse(bytes.fromhex(r["payload"]))
    vals = {i: v & 0xffffffff for i, (t, v) in enumerate(els) if t in (0x07, 0x08)}
    pid = vals.get(20)
    if pid in pl:
        rows.append((pid, vals))

print("rows with known playlist:", len(rows))
for slot in (17, 22):
    print("\n#%02d 与属性匹配:" % slot)
    for a in ATTRS + ["nmaps"]:
        hits = sum(1 for pid, v in rows if v.get(slot) == pl[pid][a])
        print("   %-24s %d/%d" % (a, hits, len(rows)))
    # distinct value distribution
    c = Counter((pl[pid]["maxparty"], pl[pid]["maxhumanplayersperteam"], v.get(slot)) for pid, v in rows)
    print("   (maxparty,maxhuman,#%d) 组合举例:" % slot)
    for k, n in sorted(c.items(), key=lambda x: str(x))[:8]:
        print("      ", k, n)
