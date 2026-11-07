#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""s137b: 逐区域 hexdump 单样本，辅助判定记录结构。"""
import json, struct, sys, zlib
sys.path.insert(0, "tools")
import lobby_grammar_v5 as G
SIGS=[b"\x78\x01",b"\x78\x9c",b"\x78\xda",b"\x78\x5e"]
corpus=json.load(open(sys.argv[1],encoding="utf-8"))
rs=[r for r in corpus if r["svc"]==8 and r["task"]==3]
d=None
for r in rs:
    b=bytes.fromhex(r["payload"]); good,els,why=G.parse(b)
    if not good: continue
    blob=[v for t,v in els if t==0x13][0]
    st=next((i for s in SIGS for i in [blob.find(s)] if i>=0),-1)
    dec=zlib.decompress(blob[st:])
    if len(dec)==32768: d=dec; break
print("sample len",len(d))
def dump(a,b):
    print("--- [%d,%d) ---"%(a,b))
    for off in range(a,b,16):
        row=d[off:off+16]
        print("%5d  %-47s  %s"%(off, " ".join("%02x"%x for x in row),
              "".join(chr(x) if 32<=x<127 else "." for x in row)))
for a,b in [(0,64),(3850,3900),(4360,4460),(4980,5120),(5300,5460),(8450,8520),
            (9580,9620),(13100,13560),(14340,14400),(14980,15060),(15680,15770),
            (15740,15900),(17400,17500),(30000,30080),(32680,32768)]:
    dump(a,b)
