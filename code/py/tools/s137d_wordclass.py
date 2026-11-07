#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""s137d: 把 [3862,15756) 按 4 字节字分类 (bool/ID/other)，找记录结构。"""
import collections, json, struct, sys, zlib
sys.path.insert(0, "tools")
import lobby_grammar_v5 as G
SIGS=[b"\x78\x01",b"\x78\x9c",b"\x78\xda",b"\x78\x5e"]

def load(corpus):
    rs=[r for r in corpus if r["svc"]==8 and r["task"]==3]
    out=[]
    for r in rs:
        b=bytes.fromhex(r["payload"]); good,els,why=G.parse(b)
        if not good: continue
        blob=[v for t,v in els if t==0x13][0]
        st=next((i for s in SIGS for i in [blob.find(s)] if i>=0),-1)
        dec=zlib.decompress(blob[st:])
        if len(dec)==32768: out.append(dec)
    return out

def cls(v):
    if v==0: return "Z"
    if v==1: return "1"
    if v<=0x100: return "s"      # small
    if 0x2700<=v<=0x27ff: return "A"   # ~10000 range
    if 0xea00<=v<=0xeaff: return "B"   # ~60000 range
    if v>0xffff: return "X"
    return "o"

def main():
    corpus=json.load(open(sys.argv[1],encoding="utf-8"))
    S=load(corpus); d=S[0]
    N=32768
    # 每 4 字节字 (基址 3862)
    base=3862
    seq=[]
    for i in range(base, 15756-3, 4):
        v=struct.unpack_from("<I",d,i)[0]
        seq.append((i,v,cls(v)))
    # 压缩为游程
    print("=== 4字节字分类游程 (base=%d) ==="%base)
    runkind=seq[0][2]; runstart=seq[0][0]; cnt=1
    out=[]
    for i,v,k in seq[1:]:
        if k==runkind:
            cnt+=1
        else:
            out.append((runstart, i, cnt, runkind))
            runkind=k; runstart=i; cnt=1
    out.append((runstart, seq[-1][0]+4, cnt, runkind))
    for a,b,c,k in out:
        print("  [%5d,%5d) n=%3d  kind=%s"%(a,b,c,k))
    print()
    print("=== 各 kind 总计数 ===")
    cnt=collections.Counter(k for i,v,k in seq)
    print(dict(cnt))
    # 找连续的 Z/1 混合区 (bool 数组)
    print()
    print("=== 疑似 bool 数组区 (值∈{0,1}) 的连续范围 ===")
    boolish=[(i,v) for i,v,k in seq if k in("Z","1")]
    # 连续: 相邻 4 字节
    runs=[]
    s=boolish[0][0]; p=boolish[0][0]
    for i,v in boolish[1:]:
        if i==p+4: p=i
        else:
            runs.append((s,p+4)); s=p=i
    runs.append((s,p+4))
    for a,b in runs:
        if b-a>=40:
            print("  [%5d,%5d) len=%d (%d 字)"%(a,b,b-a,(b-a)//4))

if __name__=="__main__":
    main()
