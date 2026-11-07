#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""s137f: 字节级周期检验 (单样本 + 全样本聚合), 判定记录步长。"""
import json, sys, zlib, collections
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

def period_test(S, A, B, maxp=400):
    """对 [A,B) 检验字节周期: 聚合所有样本, 计 (i,i+p) 任一样本不同的对数。"""
    res=[]
    for p in range(1,maxp):
        bad=0; tot=0
        for i in range(A, B-p):
            tot+=1
            for s in S:
                if s[i]!=s[i+p]:
                    bad+=1; break
        res.append((bad,p))
    res.sort()
    return res

def main():
    corpus=json.load(open(sys.argv[1],encoding="utf-8"))
    S=load(corpus); d=S[0]
    print("samples",len(S))
    # 全样本恒定位置
    nv=collections.Counter()
    const=[True]*32768
    for s in S[1:]:
        for i in range(32768):
            if s[i]!=d[i]: const[i]=False
    # 大范围周期
    for (A,B) in [(4362,8498),(9886,13122),(13322,14422)]:
        r=period_test(S,A,B)
        print("\n[%d,%d) 周期检验 top6: %s"%(A,B,[(p,b) for b,p in r[:6]]))
    # 精确检验 228
    for p in (114,228,342,456,285,57,19):
        bad=0
        for i in range(4362,8498-p):
            for s in S:
                if s[i]!=s[i+p]: bad+=1;break
        print("  p=%d 失配=%d / %d"%(p,bad,8498-p-4362))
    # 记录数: 假设步长 P, 从 A 起
    print()
    # 输出 [4362,4362+228) 的始段 hex 供人读
    print("=== [4362,4362+228) hex ===")
    for off in range(4362,4362+228,16):
        row=d[off:off+16]
        print("%5d  %s"%(off," ".join("%02x"%x for x in row)))
    print("=== [4590,4590+228) hex (下一个周期) ===")
    for off in range(4590,4590+228,16):
        row=d[off:off+16]
        print("%5d  %s"%(off," ".join("%02x"%x for x in row)))

if __name__=="__main__":
    main()
