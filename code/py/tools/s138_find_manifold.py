#!/usr/bin/env python3
"""138 · 全语料搜 Manifold 样本（含任意偏移的滑动窗口扫描）。

判据（Manifold 结构，来自 0x6256C0）：
  bit0      = 1            hasCodes
  bit1..5   = 00011        code(3)   ← 3
  bit6..13  = 00000001     type = 1  ← Manifold 自标识
  bit14..18 = 01000        code(8)
  bit19..50 = N            (<=0x800)

同时搜"任意偏移"的版本（不只 bit0 对齐）。
"""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CORPUS = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"


def bits(data, start, n):
    v = 0
    for i in range(n):
        p = start + i
        if p >= len(data) * 8:
            return None
        v = (v << 1) | ((data[p >> 3] >> (7 - (p & 7))) & 1)
    return v


recs = json.load(open(CORPUS, encoding="utf-8"))
print("语料 %d 条" % len(recs))

hit_align0 = []
hit_any = []

for r in recs:
    p = bytes.fromhex(r["payload"])
    nbits = len(p) * 8
    # ① 只测 bit0 对齐
    if nbits >= 51:
        if bits(p, 0, 1) == 1 and bits(p, 1, 5) == 3 and bits(p, 6, 8) == 1:
            N = bits(p, 19, 32)
            hit_align0.append((r["svc"], r["task"], r["run"], N))
    # ② 任意偏移滑动（步长 1 位）
    for off in range(0, min(nbits - 51, 4096)):
        if bits(p, off, 1) != 1:
            continue
        if bits(p, off + 1, 5) != 3:
            continue
        if bits(p, off + 6, 8) != 1:
            continue
        N = bits(p, off + 19, 32)
        if N is not None and 0 <= N <= 0x800:
            hit_any.append((r["svc"], r["task"], r["run"], off, N))
            break   # 每 payload 只记第一个

print("\n① bit0 对齐的 Manifold: %d 条" % len(hit_align0))
for h in hit_align0[:20]:
    print("   svc=%d task=%d N=%s run=%s" % (h[0], h[1], h[3], h[2]))

print("\n② 任意偏移的 Manifold: %d 条" % len(hit_any))
from collections import Counter
c = Counter((h[0], h[1]) for h in hit_any)
print("   按 (svc,task) 分布:", dict(c.most_common(10)))
for h in hit_any[:15]:
    print("   svc=%d task=%d off=%d位 N=%s" % (h[0], h[1], h[3], h[4]))
