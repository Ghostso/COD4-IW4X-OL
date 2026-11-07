#!/usr/bin/env python3
"""6/14 mmbook 的 b64 精确解码 + mmstart 各键值域 + 2654 与 118 的 5 个数区分. 为 122 卷取证."""
import json, struct, base64, collections, re
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
inners=[]
for r in recs:
    if r.get("svc")==6 and r.get("task")==14:
        for d in blobs(bytes.fromhex(r["payload"])):
            if len(d)>=4 and struct.unpack_from("<I",d,0)[0]==len(d)-4:
                inners.append(d[4:])

# mmbook 全部形态
mmbook=collections.Counter(x for x in inners if x.startswith(b"mmbook"))
print("=== mmbook 全部 distinct 形态 (%d 种) ==="%len(mmbook))
for x,c in mmbook.most_common():
    print("  x%-3d %r"%(c,x))
    # 解 b64
    m=re.search(rb"mmbook\s+(\d+)\s+(\S+)\s+(\S+)",x)
    if m:
        ver,b64,flag=m.groups()
        try:
            raw=base64.b64decode(b64+b"="*(-len(b64)%4))
            print("       ver=%s b64=%s -> 0x%s (%dB) flag=%s"%(ver.decode(),b64.decode(),raw.hex(),len(raw),flag.decode()))
        except Exception as e:
            print("       b64 解失败:",e)

# mmstart 键值域
kv=collections.defaultdict(collections.Counter)
for x in inners:
    if x.startswith(b"mmstart"):
        for m in re.finditer(rb"([A-Za-z_][A-Za-z0-9_]*|[0-9]+)\s+([^\s;]+);",x):
            kv[m.group(1).decode()][m.group(2).decode()]+=1
print("\n=== mmstart 各键值域 ===")
for k in sorted(kv,key=lambda k:-sum(kv[k].values())):
    vals=kv[k]
    print("  %-24s n=%-3d 值域(distinct=%d): %s"%(k,sum(vals.values()),len(vals),dict(vals.most_common(6))))
