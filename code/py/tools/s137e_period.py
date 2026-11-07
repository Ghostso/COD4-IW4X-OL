#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""s137e: 周期精确化 + 大值块 dump + 28/4 解析对照。"""
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
    if v<=0x100: return "s"
    if 0x2700<=v<=0x27ff: return "A"
    if 0xea00<=v<=0xeaff: return "B"
    if v>0xffff: return "X"
    return "o"

def main():
    corpus=json.load(open(sys.argv[1],encoding="utf-8"))
    S=load(corpus); d=S[0]
    # 1) 周期: 用 cls 序列自比较
    base=3862
    cs=[cls(struct.unpack_from("<I",d,i)[0]) for i in range(base,8498-3,4)]
    best=[]
    for p in range(1,300):
        mism=sum(1 for k in range(len(cs)-p) if cs[k]!=cs[k+p])
        best.append((mism,p))
    best.sort()
    print("=== cls 序列最佳周期 (前5) ===")
    for m,p in best[:5]:
        print("  period=%d mism=%d / %d"%(p,m,len(cs)-p))
    P=best[0][1]
    print("  -> 采用 period=%d 字节 (%d 字)"%(P*4,P))
    # 2) 大值块 [4150,4342)
    print("\n=== [4150,4342) 48 个字 ===")
    for i in range(4150,4342,4):
        v=struct.unpack_from("<I",d,i)[0]
        print("  @%5d  %08x  %d"%(i,v,v))
    # 3) 9-X 游程 [4530,4566) 的值
    print("\n=== 9-X 游程 [4530,4566) ===")
    for i in range(4530,4566,4):
        v=struct.unpack_from("<I",d,i)[0]
        print("  @%5d  %08x  %d"%(i,v,v))
    # 周期内相对 offset 的 kind 序列
    print("\n=== 一个周期内 (相对 base) 的 kind 序列 ===")
    pat=cs[:P]
    print("  ", "".join(pat))
    # 4) 28/4 解析
    print("\n=== 28/4 ===")
    r28=[r for r in corpus if r["svc"]==28 and r["task"]==4]
    print("  样本数",len(r28))
    allslots=collections.Counter()
    cnts=set()
    for r in r28:
        b=bytes.fromhex(r["payload"]); good,els,why=G.parse(b)
        if not good: continue
        arrs=[v for t,v in els if t in(0x6C,0x6B)]
        cnt,body=arrs[0]
        cnts.add(cnt)
        n=len(body)//4
        sl=struct.unpack_from("<%dI"%n,body,0)
        allslots[tuple(sl)]+=1
    print("  count(尾u32) 取值集:",cnts,"body_u32 数:",len(sl))
    print("  槽值前25:",sl[:25])
    print("  槽值 范围: min=%d max=%d 个数=%d"%(min(sl),max(sl),len(sl)))
    print("  槽值排序:",sorted(sl)[:40],"...")
    print("  唯一序列数:",len(allslots))
    # 5) 8/3 blob 里的 ID (A/B/X) 全集合
    ids=collections.Counter()
    for s in S:
        for i in range(base,15756-3,4):
            v=struct.unpack_from("<I",s,i)[0]
            k=cls(v)
            if k in("A","B","X"): ids[v]+=1
    print("\n=== 8/3 blob A/B/X 值 top40 ===")
    for v,c in ids.most_common(40):
        print("  %08x (%6d) x%d"%(v,v,c))

if __name__=="__main__":
    main()
