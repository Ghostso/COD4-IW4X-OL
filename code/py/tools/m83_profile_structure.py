#!/usr/bin/env python3
"""8/3 解压后 32KB 档案结构:
   - u32#4 == 解压首4字节? (54d3971b)
   - 32KB 的内存字段布局: 哪些区恒定/可变; 找 CODOID/名字/数值
"""
import json, struct, zlib, collections
CORPUS=r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs=json.load(open(CORPUS,"r",encoding="utf-8"))
if isinstance(recs,dict): recs=recs.get("records") or recs.get("data") or list(recs.values())
ps=[bytes.fromhex(r["payload"]) for r in recs if r.get("svc")==8 and r.get("task")==3]

decs=[]
for p in ps:
    idx=p.find(b"\x78\x01")
    dec=zlib.decompress(p[idx:])
    decs.append((p,dec))

# u32#4 (payload offset 12..16) vs 解压首4字节
print("=== u32#4 vs 解压首4字节 ===")
m=0
for p,dec in decs:
    u4=struct.unpack_from("<I",p,12)[0]
    first=struct.unpack_from("<I",dec,0)[0]
    if u4==first: m+=1
print("  相等 %d/%d"%(m,len(decs)))
print("  u32#1..4 样本:",[struct.unpack_from("<I",decs[0][0],i*4)[0] for i in range(4)])
print("  解压首 4 u32:",[struct.unpack_from("<I",decs[0][1],i*4)[0] for i in range(4)])

# 逐字节方差: 32KB 哪些区恒定
N=32768
var=[0]*N
first=decs[0][1]
for p,dec in decs:
    for i in range(N):
        if dec[i]!=first[i]: var[i]=1
segments=[]
i=0
while i<N:
    j=i
    while j<N and var[j]==var[i]: j+=1
    segments.append((i,j,var[i]))
    i=j
print("\n=== 恒定/可变区段 (前 40 段) ===")
for a,b,v in segments[:40]:
    print("  [%5d..%5d) %s len=%d"%(a,b,"VAR" if v else "CONST",b-a))
print("总段数:",len(segments))

# 恒定区里找 CODOID/账号
COD=0xE7C8A98A6B4C2D0E
hits=0
for p,dec in decs:
    if struct.pack("<Q",COD) in dec: hits+=1
print("\n解压里含 CODOID(0xE7C8A98A6B4C2D0E) 的:",hits,"/",len(decs))
# 找非零 u32 值分布
vals=collections.Counter()
for i in range(0,N-3,4):
    v=struct.unpack_from("<I",first,i)[0]
    if v: vals[v]+=1
print("\n首样本非零 u32 值 Top20:",[(hex(k),c) for k,c in vals.most_common(20)])
# 解压后是否含 ASCII
import re
asc=set()
for p,dec in decs:
    for mm in re.finditer(rb"[ -~]{6,}",dec):
        asc.add(mm.group(0)[:30].decode("latin1"))
print("\n解压后 ASCII 串 (%d 种, 前20):"%len(asc))
for s in sorted(asc)[:20]: print("  %r"%s)
