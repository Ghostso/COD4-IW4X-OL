#!/usr/bin/env python3
"""137 卷独立复核: 8/3 解压体的头条数字(样本数/长度/恒定字节占比/[12,3862) 内容)."""
import json
import sys
import zlib

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CORPUS = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs = json.load(open(CORPUS, encoding="utf-8"))
tgt = [r for r in recs if r["svc"] == 8 and r["task"] == 3]
print("8/3 记录数 =", len(tgt))

decs = []
for r in tgt:
    p = bytes.fromhex(r["payload"])
    # 找 zlib 流 (78 01)
    i = p.find(b"\x78\x01")
    ok = False
    if i >= 0:
        try:
            d = zlib.decompress(p[i:])
            decs.append(d)
            ok = True
        except Exception as e:
            print("  解压失败:", e)
    if not ok:
        print("  未找到/未解压, len(payload)=", len(p))
print("解压成功 =", len(decs))
print("长度集合 =", sorted({len(x) for x in decs}))

if decs:
    n = len(decs)
    L = len(decs[0])
    const = [all(x[i] == decs[0][i] for x in decs) for i in range(L)]
    c = sum(const)
    print("恒定字节 = %d / %d = %.2f%%" % (c, L, 100.0 * c / L))
    # [12,3862) 是否全 0
    seg = decs[0][12:3862]
    print("[12,3862) 全0 =", set(seg) == {0}, " byte set size=", len(set(seg)))
    # payload u32#4 == dec[0:4] ?
    ok4 = 0
    for r, d in zip(tgt, decs):
        p = bytes.fromhex(r["payload"])
        if len(p) >= 4 and p[:4] == d[:4]:
            ok4 += 1
    print("payload[:4] == dec[:4] :", ok4, "/", n)
    # 高熵字节
    hi = [i for i in range(L) if len({x[i] for x in decs}) > 6]
    print("取值>6 的偏移数 =", len(hi), hi[:20])
    # 尾部恒定区间
    tail_const = all(const[i] for i in range(15756, L))
    print("[15756,32768) 全恒定 =", tail_const)
