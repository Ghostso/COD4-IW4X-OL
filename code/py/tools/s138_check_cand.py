#!/usr/bin/env python3
"""138 · 检查那条候选 Manifold 的真实性（是不是巧合字节重合）。"""
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
for r in recs:
    if r["svc"] != 21 or r["task"] != 1:
        continue
    p = bytes.fromhex(r["payload"])
    nbits = len(p) * 8
    for off in range(0, min(nbits - 51, 4096)):
        if bits(p, off, 1) != 1:
            continue
        if bits(p, off + 1, 5) != 3:
            continue
        if bits(p, off + 6, 8) != 1:
            continue
        N = bits(p, off + 19, 32)
        if N is not None and 0 <= N <= 0x800:
            print("命中: run=%s len=%d off=%d位(字节%.2f) N=%d"
                  % (r["run"], len(p), off, off / 8.0, N))
            b0 = off // 8
            print("  原始字节(前 24 字节):", p[:24].hex(" "))
            print("  命中处附近:", p[max(0, b0 - 2):b0 + 8].hex(" "))
            print("  ★ 该 payload 是 TLV 结构: 13 08 <len> ...  ⇒ 偏移 %.2f 落在数据体中部，"
                  "很可能是巧合" % (off / 8.0))
            break
    else:
        continue
    break
