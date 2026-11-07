#!/usr/bin/env python3
"""s137: sample-level sub-record / padding test."""
import json, struct, collections
CORPUS = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs = json.load(open(CORPUS, "r", encoding="utf-8"))
if isinstance(recs, dict): recs = recs.get("records") or recs.get("data") or list(recs.values())
FIXED = {0x01:1,0x03:1,0x06:2,0x07:4,0x08:4,0x09:8,0x0a:8}
def blobs(p):
    out=[];i=0;n=len(p)
    while i<n:
        t=p[i];i+=1
        if t==0: continue
        if t==0x10:
            j=p.find(b"\x00",i)
            if j<0: break
            i=j+1; continue
        if t in FIXED: i+=FIXED[t]; continue
        if t in (0x13,0x6b,0x6c):
            if i>=n or p[i]!=0x08: break
            i+=1
            if i+4>n: break
            ln=struct.unpack_from("<I",p,i)[0]; i+=4
            data=p[i:i+ln]; i+=ln
            if t in (0x6b,0x6c): i+=4
            if t==0x13: out.append(data)
            continue
        break
    return out
inner=[]
for r in recs:
    if r.get("svc")==11 and r.get("task")==4:
        for d in blobs(bytes.fromhex(r["payload"])):
            if len(d)>=8 and struct.unpack_from("<I",d,0)[0]==len(d)-4: inner.append(d[4:])
fam=[x for x in inner if x and x[0]==2]
K=lambda x: struct.unpack_from("<I",x,4)[0]>>10
M=lambda x: struct.unpack_from("<H",x,8)[0]>>11
v2b=[x[10:] for x in fam if x[1]==2]
# V=2 bodies: do they always end 0x00? how many trailing zero bytes?
print("V=2 bodies trailing zero bytes:", collections.Counter(
    len(b)-len(b.rstrip(b'\x00')) for b in v2b))
# sample-level maxCP>=K-1
hit=0; tot=0; fails=[]
for x in fam:
    if x[1]==2: continue
    b=x[10:]; k=K(x); tot+=1
    best=0
    for c in v2b:
        n=0
        while n<min(len(b),len(c)) and b[n]==c[n]: n+=1
        if n>best: best=n
    if best>=k-1: hit+=1
    else: fails.append((x[1],k,M(x),len(b)-k,best))
print("V!=2: maxCP>=K-1 : %d/%d" % (hit,tot))
print("failures:", collections.Counter((f[0],f[1],f[2],f[4]) for f in fails))
# same (K,M) restricted
print()
hit2=0
for x in fam:
    if x[1]==2: continue
    b=x[10:]; k=K(x); m=M(x)
    same=[x2[10:] for x2 in fam if x2[1]==2 and K(x2)==k and M(x2)==m]
    if not same:
        continue
    best=max(sum(1 for i in range(min(len(b),len(c))) if b[i]==c[i]) for c in same)
    if best>=k-1: hit2+=1
print("V!=2 with a same-(K,M) V=2 sample and maxCP>=K-1: %d" % hit2)
# tail first byte tag
print()
print("tail[0] (body[K]) distribution per V: K,M")
d=collections.defaultdict(set)
for x in fam:
    if x[1]==2: continue
    b=x[10:]; k=K(x)
    if len(b)>k: d[(x[1],k,M(x))].add(b[k])
for k in sorted(d): print("   V=%X K=%d M=%d tail0=%s"%(k[0],k[1],k[2],sorted(hex(v) for v in d[k])))
