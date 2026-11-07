#!/usr/bin/env python3
"""s138_pl_info: 打印 playlist id -> 名称/类别/模式/首图 摘要。"""
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
P = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\playlist_plain.txt"
lines = open(P, encoding="latin1").read().splitlines()
pl = {}
cur = None
for l in lines:
    m = re.match(r"^\s*playlist\s+(\d+)\s*$", l)
    if m:
        cur = int(m.group(1))
        pl[cur] = {"name": None, "cat": None, "maps": [], "gts": [], "vsrule": None}
        continue
    if cur is None:
        continue
    m = re.match(r'^\s*name\s+english\s+"([^"]*)"', l)
    if m:
        pl[cur]["name"] = m.group(1)
    m = re.match(r"^\s*category\s+(\S+)", l)
    if m:
        pl[cur]["cat"] = m.group(1)
    m = re.match(r"^\s*([a-z0-9_]+)\s*,\s*([a-z0-9_]+)\s*,\s*\d+", l)
    if m:
        pl[cur]["maps"].append(m.group(1))
        pl[cur]["gts"].append(m.group(2))
    m = re.match(r'^\s*vsrule\s+"?([0-9Vv]+)"?', l)
    if m:
        pl[cur]["vsrule"] = m.group(1)

for pid in [int(x) for x in (sys.argv[1] if len(sys.argv) > 1 else "1,10,19,50,148,123,182,195,206").split(",")]:
    d = pl.get(pid)
    if not d:
        print("playlist %d NOT FOUND" % pid)
        continue
    print("playlist %-4d name=%-32r cat=%-4s vs=%-4s gt0=%-6s map0=%s (n_maps=%d)" % (
        pid, d["name"], d["cat"], d["vsrule"],
        d["gts"][0] if d["gts"] else "?", d["maps"][0] if d["maps"] else "?", len(d["maps"])))
