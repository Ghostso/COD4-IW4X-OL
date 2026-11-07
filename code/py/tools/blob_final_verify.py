#!/usr/bin/env python3
"""收口 11/4 blob 内层两族的最终验证:
   ready族(0x18): 全66条验证 10字节magic恒定 + [10:13]是否+2递增 + [13:17]=0
   room族(0x02): 抽 float32 看是否坐标; 统计 header[0:8] 结构
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
pairs=[]
for r in recs:
    if r.get("svc")==11 and r.get("task")==4:
        run=str(r.get("run") or r.get("source") or "?")
        idx=r.get("idx",0)
        for d in blobs(bytes.fromhex(r["payload"])):
            if len(d)>=4 and struct.unpack_from("<I",d,0)[0]==len(d)-4:
                pairs.append((run,idx,d[4:]))

ready=[(run,idx,x) for run,idx,x in pairs if x and x[0]==0x18]
print("### ready族 %d 条"%len(ready))
# 1) magic [0:10] 恒定?
magics=collections.Counter(x[:10] for _,_,x in ready)
print("magic[0:10] distinct:",len(magics))
for m,c in magics.items(): print("  %s x%d"%(m.hex(),c))
# 2) [13:17]==0?
tail_ok=sum(1 for _,_,x in ready if x[13:17]==b"\x00"*4)
print("[13:17]==0000: %d/%d"%(tail_ok,len(ready)))
# 3) [10:13] 值
vals=[int.from_bytes(x[10:13],"little") for _,_,x in ready]
print("[10:13] u24 值集合大小:",len(set(vals))," min=%d max=%d"%(min(vals),max(vals)))
# 按run分组看Δ
byrun=collections.defaultdict(list)
for run,idx,x in ready: byrun[run].append((idx,int.from_bytes(x[10:13],"little")))
print("按run看Δ=2:")
for run,lst in byrun.items():
    lst.sort()
    v=[b for _,b in lst]
    deltas=[v[i+1]-v[i] for i in range(len(v)-1)]
    if deltas:
        print("  run=%-20s n=%d deltas=%s"%(run[:20],len(v),sorted(set(deltas))))

print("\n### room族(0x02) header 结构 + float32")
room=[x for _,_,x in pairs if x and x[0]==0x02]
# header[0:8] 分布
hdr=collections.Counter(x[:8].hex() for x in room)
print("header[0:8] distinct=%d (top10):"%len(hdr))
for h,c in hdr.most_common(10): print("  %s x%d"%(h,c))
# 抽 float32: 每4字节对齐看是否是"合理"float (1e-3..1e5, 或 0)
print("\n各样本中'合理float32'个数 (1e-2<=|f|<=1e5):")
for x in sorted(set(room),key=len)[:8]:
    fs=[]
    for i in range(0,len(x)-3):
        f=struct.unpack_from("<f",x,i)[0]
        if 1e-2<=abs(f)<=1e5: fs.append((i,round(f,3)))
    print("  len=%3d: %d 个合理float, 前8=%s"%(len(x),len(fs),fs[:8]))
