#!/usr/bin/env python3
"""119卷证据汇总:
  (1) 11/4 room族 内层出现 7f000001 (127.0.0.1) 的次数与端口
  (2) room族 float32 合理值统计
  (3) variant0x02 长度律 u16@[5:7]==(len-10)*4 全量验证
  (4) ready族(0x18) 与 paper109 'blob[4]==0x18' 判据的一致性
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
raw=[]  # 完整blob(含4字节len头)
for r in recs:
    if r.get("svc")==11 and r.get("task")==4:
        for d in blobs(bytes.fromhex(r["payload"])):
            raw.append(d)
inner=[d[4:] for d in raw if len(d)>=4 and struct.unpack_from("<I",d,0)[0]==len(d)-4]
room=[x for x in inner if x and x[0]==0x02]

# (1) 127.0.0.1
pat=bytes.fromhex("7f000001")
cnt=0; ports=collections.Counter()
for x in room:
    i=0
    while True:
        p=x.find(pat,i)
        if p<0: break
        cnt+=1
        if p+6<=len(x): ports[x[p+4]|(x[p+5]<<8)]+=1
        i=p+1
print("(1) room族 '7f000001'(127.0.0.1) 出现 %d 次; 其后u16端口: %s"%(cnt,dict(ports.most_common(8))))

# (2) float32
print("\n(2) room族 float32 合理值(1e-2..1e5)出现次数:")
allf=collections.Counter()
for x in room:
    for i in range(0,len(x)-3):
        f=struct.unpack_from("<f",x,i)[0]
        if 1e-2<=abs(f)<=1e5:
            allf[round(f,2)]+=1
print("   合理float distinct=%d, top: %s"%(len(allf),allf.most_common(10)))

# (3) variant02 长度律
v2=[x for x in room if x[1]==0x02]
ok=sum(1 for x in v2 if len(x)>=8 and struct.unpack_from("<H",x,5)[0]==(len(x)-10)*4)
print("\n(3) variant0x02: u16@[5:7]==(len-10)*4 : %d/%d"%(ok,len(v2)))
# 反例
for x in v2:
    if len(x)>=8 and struct.unpack_from("<H",x,5)[0]!=(len(x)-10)*4:
        print("   反例 len=%d u16=%d"%(len(x),struct.unpack_from("<H",x,5)[0]))

# (4) ready判据
print("\n(4) ready族 与 paper109 'blob[4]==0x18' 一致性:")
n21=sum(1 for d in raw if len(d)==21)
n21_b4=sum(1 for d in raw if len(d)==21 and d[4]==0x18)
print("   完整blob len==21 的条数=%d; 其中 blob[4]==0x18 的=%d"%(n21,n21_b4))
# 17字节inner且首字节0x18
n17=sum(1 for x in inner if len(x)==17 and x[0]==0x18)
print("   17字节inner且首字节0x18 = %d"%n17)
