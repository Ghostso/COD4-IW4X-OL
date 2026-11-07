#!/usr/bin/env python3
"""wfUD3\" 密文段定位与定性: 出现在 68/3, 21/1, 21/12, 11/2.
   - 精确定位每个 blob 里这串的位置与长度
   - 看它是不是 AES 块(16 倍数)、熵、是否随会话变、前后结构
"""
import json, struct, collections, math, re
CORPUS=r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs=json.load(open(CORPUS,"r",encoding="utf-8"))
if isinstance(recs,dict): recs=recs.get("records") or recs.get("data") or list(recs.values())
FIXED={0x01:1,0x03:1,0x06:2,0x07:4,0x08:4,0x09:8,0x0a:8}
def blobs(payload):
    out=[];i=0;n=len(payload)
    while i<n:
        t=payload[i];i+=1
        if t==0x00: continue
        if t==0x10:
            j=payload.find(b"\x00",i)
            if j<0: break
            i=j+1;continue
        if t in FIXED: i+=FIXED[t];continue
        if t in (0x13,0x6b,0x6c):
            if i>=n or payload[i]!=0x08: break
            i+=1
            if i+4>n:break
            ln=struct.unpack_from("<I",payload,i)[0];i+=4
            data=payload[i:i+ln];i+=ln
            if t in(0x6b,0x6c): i+=4
            if t==0x13: out.append(data)
            continue
        break
    return out

def ent(b):
    if not b: return 0
    c=collections.Counter(b); n=len(b)
    return -sum(v/n*math.log2(v/n) for v in c.values())

pat=b'wfUD3"'
for svc,task in [(68,3),(21,1),(21,12),(11,2)]:
    print("="*70)
    print("### %d/%d"%(svc,task))
    for r in recs:
        if r.get("svc")==svc and r.get("task")==task:
            p=bytes.fromhex(r["payload"])
            bl=blobs(p)
            for d in bl[:1] if False else bl:
                pos=d.find(pat)
                if pos<0: continue
                seg=d[pos:]
                print("  blob len=%d  pat@%d  seg len=%d  16倍数=%s  熵=%.2f"%(len(d),pos,len(seg),len(seg)%16==0,ent(seg)))
                print("    前16: %s"%seg[:16].hex())
                print("    后16: %s"%seg[-16:].hex())
                print("    blob前段(pat前): %s"%d[:min(pos,40)].hex())
                break
            break
    # 该task所有blob里 seg 的长度集合
    segs=set()
    for r in recs:
        if r.get("svc")==svc and r.get("task")==task:
            for d in blobs(bytes.fromhex(r["payload"])):
                pos=d.find(pat)
                if pos>=0: segs.add(len(d)-pos)
    print("  seg 长度集合:",sorted(segs))
