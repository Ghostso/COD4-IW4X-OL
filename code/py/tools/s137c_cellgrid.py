#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""s137c: 判定可变区细胞栅格 (stride/对齐) 与记录结构。"""
import collections, json, math, struct, sys, zlib
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

def main():
    corpus=json.load(open(sys.argv[1],encoding="utf-8"))
    S=load(corpus); n=len(S)
    print("samples",n)
    N=32768
    # 每个偏移的取值集合大小
    nv=[0]*N
    vals=[None]*N
    for i in range(N):
        st=set(s[i] for s in S)
        nv[i]=len(st)
    # 全体非恒定位置
    var=[i for i in range(N) if nv[i]>1]
    print("非恒定位置总数",len(var),"占比 %.3f%%"%(100*len(var)/N))
    # 对 [3862,32768) 区域: 仅统计"非众数"出现次数 (=每格真正变化的程度)
    # 判定细胞栅格: 把每个样本的 [3862,32768) 视为字节流, 找可变位置集合的 gcd 结构
    tail=[i for i in var if i>=3862]
    print("tail 可变位置数",len(tail))
    # 检查是否所有 tail 可变位置都落在某个 mod K 类
    for K in (2,4):
        c=collections.Counter(i%K for i in tail)
        print("  mod %d 分布: %s"%(K,dict(sorted(c.items()))))
    # 每个样本: 非零 u16 at (even) 的位置
    for off in (0,2):
        pos=collections.Counter()
        for s in S:
            for i in range(3862+off - ((3862+off)%2), N-1, 2):
                if struct.unpack_from("<H",s,i)[0]:
                    pos[i]+=1
        print("  u16(偶) offset base=%d: 非零位置数=%d 首20=%s"%(off,len(pos),sorted(pos)[:20]))
    # 找 stride: 相邻"可变 u16 位置"的差
    # 用全体样本聚合: 某偶数位置是否曾非零
    ever=set()
    for s in S:
        for i in range(3862, N-1, 2):
            if struct.unpack_from("<H",s,i)[0]:
                ever.add(i)
    ev=sorted(ever)
    d=collections.Counter(ev[k+1]-ev[k] for k in range(len(ev)-1))
    print("  ever-nonzero u16(偶) 位置数=%d 相邻差 top15=%s"%(len(ev),d.most_common(15)))
    # 前 60 个 ever 位置
    print("  首 60 ever 位置:",ev[:60])
    # gcd
    g=0
    for x in ev: g=math.gcd(g,x)
    print("  ever 位置 gcd =",g)
    # 分段: 每 1024 字节里 ever 的个数
    seg=collections.Counter(x//1024 for x in ev)
    print("  ever 位置按 1KB 段计数:", [seg.get(k,0) for k in range(32)])

if __name__=="__main__":
    main()
