#!/usr/bin/env python3
"""11/4 与 6/14 的 blob 内层 (剥 4B 长度前缀) 逐字节分析:
- 首 4 字节 02 0X 00 00 分布 (X 取值)
- 内层后续结构: 是否 [02][len][payload]? 与 67字节 P2P 表 / ready 批次关系?
"""
import json, collections, struct
CORPUS=r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs=json.load(open(CORPUS,"r",encoding="utf-8"))
if isinstance(recs,dict): recs=recs.get("records") or recs.get("data") or list(recs.values())

def extract_blobs(p):
    """走 TLV, 返回所有 0x13 blob 的原始字节 (含长度前缀在内)"""
    out=[]; i=0
    while i < len(p):
        t=p[i]; i+=1
        if t==0x00: continue
        if t==0x03: i+=1
        elif t in (0x06,): i+=2
        elif t in (0x07,0x08): i+=4
        elif t in (0x09,0x0a): i+=8
        elif t==0x10:
            while i<len(p) and p[i]!=0: i+=1
            i+=1
        elif t==0x13:
            if i+4>len(p): break
            L=struct.unpack_from("<I",p,i)[0]; i+=4
            out.append(p[i:i+L]); i+=L
        elif t in (0x6b,0x6c):
            if i+4>len(p): break
            L=struct.unpack_from("<I",p,i)[0]; i+=4
            out.append(b"[ARR]"+p[i:i+L]); i+=L+4
        else:
            break
    return out

for svc,task in [(11,4),(6,14)]:
    print("\n=== %d/%d blob 内层 ==="%(svc,task))
    first4=collections.Counter(); inner_lens=collections.Counter()
    n=0
    samples=[]
    for r in recs:
        if r.get("svc")==svc and r.get("task")==task:
            p=bytes.fromhex(r["payload"])
            for b in extract_blobs(p):
                if b[:1]==b"[": continue
                n+=1
                inner_lens[len(b)]+=1
                first4[b[:4].hex()]+=1
                if len(samples)<8: samples.append(b)
    print("blob 数:", n)
    print("内层长度分布 (top):", inner_lens.most_common(10))
    print("首4字节分布 (top):", first4.most_common(12))
    for s in samples[:5]:
        print("  len=%d %s"%(len(s), s[:40].hex()))
