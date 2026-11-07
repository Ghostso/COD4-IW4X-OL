#!/usr/bin/env python3
"""2486/2489/2574/2500 在语料哪里? 是否与 21/5 的 playlist 号 10/50、6/14 的 playlist 相关?
查所有 2 字节(0x06)与 4 字节(0x08/0x07)值 == 这些数。"""
import json, collections, struct
CORPUS=r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs=json.load(open(CORPUS,"r",encoding="utf-8"))
if isinstance(recs,dict): recs=recs.get("records") or recs.get("data") or list(recs.values())
TARGETS={2486,2489,2574,2500,3265}
for T in sorted(TARGETS):
    print("\n=== %d ==="%T)
    # 搜 as u16 LE / u32 LE 字节串
    p16=struct.pack("<H",T); p32=struct.pack("<I",T)
    c16=collections.Counter(); c32=collections.Counter()
    for r in recs:
        p=bytes.fromhex(r["payload"])
        k="%d/%d"%(r["svc"],r["task"])
        if p16 in p: c16[k]+=p.count(p16)
        if p32 in p: c32[k]+=p.count(p32)
    print("  u16 命中:", dict(c16) if c16 else "无")
    print("  u32 命中:", dict(c32) if c32 else "无")

# 另: 搜字符串形态 '2486' 等 (mmstart 明文)
print("\n=== 字符串形态 (mmstart 明文等) ===")
for T in sorted(TARGETS):
    s=str(T).encode()
    c=collections.Counter()
    for r in recs:
        p=bytes.fromhex(r["payload"])
        if s in p:
            c["%d/%d"%(r["svc"],r["task"])]+=p.count(s)
    print("  '%d' -> %s"%(T, dict(c) if c else "无"))
