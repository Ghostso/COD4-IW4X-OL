#!/usr/bin/env python3
"""(A) §七 #8: 全语料 0x00 连续run的最大长度与上下文 (是否>9)
   (B) ready族 u16@[10:13] 与 run内 idx 的相关性
"""
import json, struct, collections
CORPUS=r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs=json.load(open(CORPUS,"r",encoding="utf-8"))
if isinstance(recs,dict): recs=recs.get("records") or recs.get("data") or list(recs.values())

# (A) 零run
runs=collections.Counter()
maxrun=0; maxtask=None
for r in recs:
    p=bytes.fromhex(r["payload"])
    i=0
    while i<len(p):
        if p[i]==0:
            j=i
            while j<len(p) and p[j]==0: j+=1
            L=j-i; runs[L]+=1
            if L>maxrun: maxrun=L; maxtask=(r.get("svc"),r.get("task"))
            i=j
        else: i+=1
print("### 0x00 连续run长度分布:")
for L in sorted(runs): print("  run=%2d : %d 次"%(L,runs[L]))
print("最长 run=%d @ %s"%(maxrun,maxtask))

# 最长run的上下文
print("\n最长run样本上下文:")
for r in recs:
    p=bytes.fromhex(r["payload"])
    if maxrun in [len(s) for s in p.split(b'\x01')]: pass
    # find run==maxrun
    i=0
    while i<len(p):
        if p[i]==0:
            j=i
            while j<len(p) and p[j]==0: j+=1
            if j-i==maxrun:
                print("  %s/%s: %s"%(r.get("svc"),r.get("task"),p[max(0,i-8):j+8].hex()))
                break
            i=j
        else: i+=1

# (B) ready counter vs idx
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
print("\n### ready族 counter vs idx (单run)")
byrun=collections.defaultdict(list)
for r in recs:
    if r.get("svc")==11 and r.get("task")==4:
        run=str(r.get("run") or r.get("source"))
        for d in blobs(bytes.fromhex(r["payload"])):
            if len(d)>=4 and struct.unpack_from("<I",d,0)[0]==len(d)-4:
                x=d[4:]
                if x and x[0]==0x18:
                    byrun[run].append((r.get("idx",0),int.from_bytes(x[10:13],"little")))
for run,lst in list(byrun.items())[:5]:
    lst.sort()
    print("  run %s:"%run[:22])
    print("    (idx, counter):",lst)
