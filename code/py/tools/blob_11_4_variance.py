#!/usr/bin/env python3
"""11/4 blob 内层逐字节方差分析: 按 byte[0..3] 分类, 找出每族里哪些字节恒定/哪些变, 定位字段边界。
   区分 0x18族(ready,17B) 与 0x02族(room data)。
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

inner=[]
for r in recs:
    if r.get("svc")==11 and r.get("task")==4:
        for d in blobs(bytes.fromhex(r["payload"])):
            if len(d)>=4 and struct.unpack_from("<I",d,0)[0]==len(d)-4:
                inner.append(d[4:])

# 分族
fam=collections.defaultdict(list)
for x in inner:
    fam[x[0]].append(x)

for f0 in sorted(fam):
    xs=fam[f0]
    lens=collections.Counter(len(x) for x in xs)
    print("="*70)
    print("族 byte0=0x%02X : %d 样本, 长度分布 %s"%(f0,len(xs),dict(lens.most_common(10))))
    # 找最大公约长度组做逐字节方差
    # 对每个长度组, 打印每字节 distinct 数
    bylen=collections.defaultdict(list)
    for x in xs: bylen[len(x)].append(x)
    for L in sorted(bylen)[:3]:
        grp=bylen[L]
        print("  -- 长度 %d (%d 样本) 逐字节 distinct/样本 --"%(L,len(grp)))
        cols=[]
        for i in range(L):
            vals=collections.Counter(x[i] for x in grp)
            cols.append((i,len(vals),vals.most_common(3)))
        # 只打印前48字节
        for (i,nd,top) in cols[:48]:
            mark="CONST" if nd==1 else ("v%d"%nd)
            print("    [%02d] %-6s top=%s"%(i,mark,top))
        # 变长/常量的边界: 找最后一个常量列
        print()
