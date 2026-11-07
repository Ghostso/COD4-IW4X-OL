#!/usr/bin/env python3
"""验证我们语料里魔数 A/B 与 DEADC0DE 家族的结构邻接，及 0xD6?? / 0x8D51E398 分布。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

A = 0xD692ADAB
B = 0x8D51E398

# 1) 是否出现 golden 的 0xD6F01F9B
print("=== 0xD6F01F9B 在全语料出现次数 ===")
cnt = 0
for r in corpus:
    b = bytes.fromhex(r["payload"])
    if b"\x9b\x1f\xf0\xd6" in b:
        cnt += 1
print("  hits =", cnt)

# 2) 魔数 A/B 的邻居元素（前一个、后一个），判断是否紧邻 DEADC0DE
print("\n=== 魔数 A/B 的元素邻接（同一条报文内）===")
def neigh(target, label):
    c = collections.Counter()
    n = 0
    for r in corpus:
        if (r["svc"], r["task"]) not in ((21,1),(21,12),(21,5)):
            continue
        b = bytes.fromhex(r["payload"])
        good, els, why = G.parse(b)
        if not good:
            continue
        for i,(t,v) in enumerate(els):
            if isinstance(v, bytes) and len(v)==4 and int.from_bytes(v,"little")==target:
                prev = els[i-1] if i>0 else None
                nxt = els[i+1] if i+1<len(els) else None
                def desc(e):
                    if e is None: return "NONE"
                    tt,vv = e
                    if isinstance(vv,bytes) and len(vv) in (1,2,4,8):
                        return "0x%02x:0x%X" % (tt, int.from_bytes(vv,"little"))
                    if isinstance(vv,bytes):
                        return "0x%02x:len%d" % (tt, len(vv))
                    return "0x%02x" % tt
                c[(desc(prev), desc(nxt))] += 1
                n += 1
    print("  %s (n=%d):" % (label, n))
    for k,v in c.most_common(8):
        print("    prev=%s  next=%s  x%d" % (k[0],k[1],v))

neigh(A, "MAGIC A 0xD692ADAB")
neigh(B, "MAGIC B 0x8D51E398")

# 3) 全语料所有 0xD6?? 高字节的 i32 值（找 query criterion 家族）
print("\n=== 全语料 0xD6?????? 高位 0xD6 的 i32 值 ===")
c = collections.Counter()
for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good: continue
    for t,v in els:
        if t==0x07 and len(v)==4:
            u = int.from_bytes(v,"little")
            if (u>>24)==0xD6:
                c[u]+=1
for k,v in c.most_common(20):
    print("  0x%08X x%d" % (k,v))

# 4) 全语料所有 0x8D?????? 高字节 0x8D 的 i32
print("\n=== 全语料高位 0x8D 的 i32 值 ===")
c = collections.Counter()
for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good: continue
    for t,v in els:
        if t==0x07 and len(v)==4:
            u = int.from_bytes(v,"little")
            if (u>>24)==0x8D:
                c[u]+=1
for k,v in c.most_common(20):
    print("  0x%08X x%d" % (k,v))
