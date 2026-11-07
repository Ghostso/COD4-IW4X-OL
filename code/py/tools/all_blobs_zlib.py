#!/usr/bin/env python3
"""全语料 0x13 blob 里 zlib 头(78 01/78 9c/78 da/78 5e) 的分布; 并试解压."""
import json, struct, zlib, collections
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
SIGS=[b"\x78\x01",b"\x78\x9c",b"\x78\xda",b"\x78\x5e"]
bytask=collections.Counter(); oktask=collections.Counter(); declens=collections.defaultdict(set)
for r in recs:
    for d in blobs(bytes.fromhex(r["payload"])):
        hit=False
        for s in SIGS:
            if d.startswith(s) or d.find(s) in (0,4,10):
                hit=True;break
        if hit:
            k=(r.get("svc"),r.get("task")); bytask[k]+=1
            st=d.find([s for s in SIGS if s in d][0])
            try:
                dec=zlib.decompress(d[st:])
                oktask[k]+=1; declens[k].add(len(dec))
            except Exception: pass
print("=== 含 zlib 头的 blob 按 task ===")
for k in sorted(bytask):
    print("  %-8s zlib头=%d 解压成功=%d 解压长度集=%s"%("%d/%d"%k,bytask[k],oktask[k],sorted(declens[k])[:6]))
