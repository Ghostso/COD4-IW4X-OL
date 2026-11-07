#!/usr/bin/env python3
"""(1) ready族(0x18) 精确模板: 哪些字节恒定/哪些变; 变的是否 u16 计数器(同run内Δ=2)
   (2) 0x02族 byte1(02/04/06/08) 与长度/内容的关系
   (3) E镜像搜 ready 常量头 18 1c 5a 98 d6 14 53 91 cf 01
"""
import json, struct, collections
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

# 收集 (run, inner) 便于按run排序
pairs=[]
for r in recs:
    if r.get("svc")==11 and r.get("task")==4:
        run=r.get("run") or r.get("source") or r.get("run_id") or "?"
        for d in blobs(bytes.fromhex(r["payload"])):
            if len(d)>=4 and struct.unpack_from("<I",d,0)[0]==len(d)-4:
                pairs.append((run,d[4:],r.get("idx",0)))

ready=[(run,x,idx) for run,x,idx in pairs if x and x[0]==0x18]
print("### ready族(0x18): %d 条"%len(ready))
# 恒定/可变
const=[i for i in range(17) if len(set(x[i] for _,x,_ in ready))==1]
var=[i for i in range(17) if i not in const]
print("恒定字节位:",const)
print("可变字节位:",var)
print("恒定值:",[ready[0][1][i] for i in const])
# 可变部分
print("\n可变字段样本 (bytes[10:13]):")
for run,x,idx in sorted(ready,key=lambda t:(str(t[0]),t[2]))[:20]:
    u16=struct.unpack_from("<H",x,10)[0]
    print("  run=%-6s idx=%-3s  b10..12=%s  u16@10=%5d  byte12=%d"%(str(run)[:6],idx,x[10:13].hex(),u16,x[12]))
# 同run内 Δ
print("\n同run内 u16@10 是否 Δ=2:")
byrun=collections.defaultdict(list)
for run,x,idx in ready: byrun[str(run)].append((idx,struct.unpack_from("<H",x,10)[0]))
for run,lst in list(byrun.items())[:6]:
    lst.sort()
    vals=[v for _,v in lst]
    deltas=[vals[i+1]-vals[i] for i in range(len(vals)-1)]
    print("  run %s: u16s=%s deltas=%s"%(run[:8],vals[:12],deltas[:12]))

# 0x02族 byte1 分类
print("\n### 0x02族: byte1 分布与长度范围")
fam=collections.defaultdict(list)
for run,x,idx in pairs:
    if x and x[0]==0x02:
        fam[x[1]].append(len(x))
for k in sorted(fam):
    L=sorted(set(fam[k]))
    print("  byte1=0x%02X: n=%d, 长度=%s"%(k,len(fam[k]),L))

# E镜像搜常量头
print("\n### E镜像搜 ready 常量头")
E=r"E:\codol_re\client_image_20261027.bin"
try:
    d=open(E,"rb").read()
    for pat in [bytes.fromhex("181c5a98d6145391"), bytes.fromhex("d6145391cf01")]:
        hits=[];i=0
        while True:
            p=d.find(pat,i)
            if p<0: break
            hits.append(p);i=p+1
            if len(hits)>=5: break
        print("  pat %s: %d hits %s"%(pat.hex(),len(hits),["0x%X"%h for h in hits]))
except Exception as e:
    print("  E读失败:",e)
