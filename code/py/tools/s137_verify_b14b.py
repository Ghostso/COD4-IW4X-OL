#!/usr/bin/env python3
"""137 复核 2: [12,3862) 是否跨样本恒定 + 其内容; payload 里哪个 u32 == dec[0:4];
并打印 [0,4) 与 [15000,15002) 的全部取值."""
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

n, L = len(decs), len(decs[0])
const = [all(x[i] == decs[0][i] for x in decs) for i in range(L)]

seg = [12, 3862]
print("[%d,%d) 跨样本恒定 = %s" % (seg[0], seg[1], all(const[i] for i in range(*seg))))
print("  样本0 取值分布 =", Counter(decs[0][seg[0]:seg[1]]).most_common(6))
print("  样本0 前 32 字节 =", decs[0][12:44].hex())

# payload 里是否含 == dec[0:4] 的 u32 (含 tag 08 前缀形态)
hit = Counter()
for (r, p), d in zip(tgt, decs):
    v = struct.unpack("<I", d[:4])[0]
    vb = d[:4]
    idx = p.find(vb)
    if idx < 0:
        hit["找不到"] += 1
    else:
        hit["找到 idx=%d" % idx] += 1
print("payload 中含 dec[0:4] 字节串:", dict(Counter(
    (("找到" if p.find(d[:4]) >= 0 else "找不到")) for (r, p), d in zip(tgt, decs))))

print("dec[0:4] 取值集合 =", sorted({d[:4].hex() for d in decs})[:5], "... 共",
      len({d[:4] for d in decs}))
print("[15000,15002) 取值 =", sorted({d[15000:15002].hex() for d in decs}))
