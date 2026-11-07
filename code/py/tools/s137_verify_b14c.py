#!/usr/bin/env python3
"""137 复核 3: (a) [12,3862) 里 6 个非零字节的偏移与取值;
(b) 验证 B14 的核心结构claim「u16 细胞、间距 4」."""
import json
import struct
import sys
import zlib
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CORPUS = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs = json.load(open(CORPUS, encoding="utf-8"))
tgt = [(r, bytes.fromhex(r["payload"])) for r in recs if r["svc"] == 8 and r["task"] == 3]
decs = []
for r, p in tgt:
    i = p.find(b"\x78\x01")
    decs.append(zlib.decompress(p[i:]))

d0 = decs[0]
nz = [(i, d0[i]) for i in range(12, 3862) if d0[i] != 0]
print("[12,3862) 非零字节 =", [(hex(i), hex(v), chr(v) if 32 <= v < 127 else "") for i, v in nz])

# u16 细胞间距
allgap_even = Counter()
allgap_any = Counter()
for d in decs:
    offs_even = [o for o in range(3862, 15756 - 1, 2) if struct.unpack_from("<H", d, o)[0] != 0]
    offs_any = [o for o in range(3862, 15756 - 1) if struct.unpack_from("<H", d, o)[0] != 0]
    for a, b in zip(offs_even, offs_even[1:]):
        allgap_even[b - a] += 1
    for a, b in zip(offs_any, offs_any[1:]):
        allgap_any[b - a] += 1
print("偶数偏移非零 u16 间距 top:", allgap_even.most_common(6))
print("任意偏移非零 u16 间距 top:", allgap_any.most_common(6))
print("每样本偶数非零 u16 数(样本0) =",
      sum(1 for o in range(3862, 15756 - 1, 2) if struct.unpack_from("<H", d0, o)[0] != 0))
