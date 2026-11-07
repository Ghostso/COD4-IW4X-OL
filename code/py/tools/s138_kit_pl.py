#!/usr/bin/env python3
"""s138_kit_pl: 解出 REF kit 的 mp_playlists_shipRetail_1.0.0.info (zlib), 打印 playlist 列表及 id。"""
import re
import sys
import zlib

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
P = r"D:\BaiduNetdiskDownload\使命召唤OL\GOLDEN-LOBBY-001\REF_LOBBY_KIT\publisher_files\mp_playlists_shipRetail_1.0.0.info"
raw = open(P, "rb").read()
try:
    t = zlib.decompress(raw).decode("latin1")
except Exception:
    t = raw.decode("latin1")
lines = t.splitlines()
print("version:", [l for l in lines if l.strip().startswith("version")][:1])
ids = []
cur = None
info = {}
for i, l in enumerate(lines):
    m = re.match(r"^\s*playlist\s+(\d+)\s*$", l)
    if m:
        cur = int(m.group(1))
        ids.append(cur)
        info[cur] = {"name": None, "gts": set(), "maps": [], "cat": None}
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
        info[cur]["gts"].add(m.group(2))

print("playlist count:", len(ids), "ids:", ids)
for pid in ids:
    d = info[pid]
    print("  id=%-4d name=%-32r cat=%-3s gt=%-8s map0=%s" %
          (pid, d["name"], d["cat"], ",".join(sorted(d["gts"])), d["maps"][0] if d["maps"] else "?"))
print("\nsorted ids:", sorted(ids))
for num in (10, 37, 50):
    s = sorted(ids)
    print("  num=%d 0based_sorted=%s 1based_sorted=%s" % (
        num, s[num] if 0 <= num < len(s) else None, s[num - 1] if 1 <= num <= len(s) else None))
