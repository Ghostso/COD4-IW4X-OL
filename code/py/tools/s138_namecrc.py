#!/usr/bin/env python3
"""s138_namecrc: 对 playlist 明文里的英文名/LOGAS名/category 值做 crc32, 找 A/B 来源。"""
import re
import zlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
A = 0xD692ADAB
O = 0xD6F01F9B
B = 0x8D51E398
T = {A: "A", O: "OLD", B: "B"}

P = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\playlist_plain.txt"
t = open(P, encoding="latin1").read()

names = set()
for m in re.finditer(r'name\s+english\s+"([^"]*)"', t):
    names.add(m.group(1))
for m in re.finditer(r'@LOGAS="([^"]*)"', t):
    names.add(m.group(1))
for m in re.finditer(r'^\s*name\s+(\S+)\s*$', t, re.M):
    names.add(m.group(1))

print("names:", len(names))
hits = []
for n in names:
    for cand in (n, n.lower(), n.upper(), n.strip()):
        c = zlib.crc32(cand.encode("latin1")) & 0xffffffff
        if c in T:
            hits.append((T[c], n))
print("hits:", hits)

# category numbers + typical attribute literals
for kw in ["Skirmish", "Combat Training", "Charge - Skirmish", "Combat", "combat",
           "Onboarding", "War God", "Battle City", "PVE", "TDM", "Skirmish TDM"]:
    c = zlib.crc32(kw.encode()) & 0xffffffff
    print("  %-22r %08X %s" % (kw, c, T.get(c, "")))
