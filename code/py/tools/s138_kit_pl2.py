#!/usr/bin/env python3
"""s138_kit_pl2: 解 kit golden 的 playlist info 并按 id 打印。"""
import re
import sys
import zlib

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
P = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_VERIFIED_GOLDEN_20261019\publisher_files\mp_playlists_shipRetail_1.0.0.info"
raw = open(P, "rb").read()
t = zlib.decompress(raw).decode("latin1")
lines = t.splitlines()
ids = []
info = {}
cur = None
for l in lines:
    m = re.match(r"^\s*playlist\s+(\d+)\s*$", l)
    if m:
        cur = int(m.group(1))
        ids.append(cur)
        info[cur] = {"name": None, "gt": set(), "maps": [], "cat": None}
        continue
    if cur is None:
        continue
    m = re.match(r'^\s*name\s+english\s+"([^"]*)"', l)
    if m:
        info[cur]["name"] = m.group(1)
    m = re.match(r"^\s*category\s+(\S+)", l)
    if m:
        info[cur]["cat"] = m.group(1)
    m = re.match(r"^\s*([a-z0-9_]+)\s*,\s*([a-z0-9_]+)\s*,\s*\d+", l)
    if m:
        info[cur]["maps"].append(m.group(1))
        info[cur]["gt"].add(m.group(2))

print("count", len(ids), "ids", ids)
for pid in ids:
    d = info[pid]
    print("  id=%-4d name=%-30r cat=%-3s gt=%-8s map0=%s" %
          (pid, d["name"], d["cat"], ",".join(sorted(d["gt"])), d["maps"][0] if d["maps"] else "?"))
