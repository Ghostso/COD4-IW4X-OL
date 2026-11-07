# -*- coding: utf-8 -*-
import os

p_curr = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929\Ayria\Plugins\CodolGameServer.Localnet32"
p_bak  = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929\Ayria\Plugins\CodolGameServer.Localnet32.bak"

with open(p_curr, "rb") as f: d_curr = f.read()
with open(p_bak, "rb") as f: d_bak = f.read()

diffs = []
for i in range(len(d_curr)):
    if d_curr[i] != d_bak[i]:
        diffs.append((i, d_bak[i], d_curr[i]))

print(f"Total byte differences: {len(diffs)}")
# Group contiguous diffs
groups = []
for d in diffs:
    if not groups or d[0] > groups[-1][-1][0] + 1:
        groups.append([d])
    else:
        groups[-1].append(d)

for g in groups:
    start = g[0][0]
    end = g[-1][0]
    orig_b = bytes([x[1] for x in g])
    curr_b = bytes([x[2] for x in g])
    print(f"Diff @ 0x{start:X}..0x{end:X} (len {len(g)}):")
    print(f"  Orig: {orig_b.hex()}")
    print(f"  Curr: {curr_b.hex()}")