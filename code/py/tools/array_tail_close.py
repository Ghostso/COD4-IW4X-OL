#!/usr/bin/env python3
"""§七 #5 收口: 0x6b/0x6c 尾部 u32 语义。
   - 0x6b: body首u32=1, tail=0 (恒), body只有4字节
   - 0x6c: 28/4 body首u32=127(元素数), tail=263(容量); 其余12条是什么?
   - 检验: tail 是否 = byteLen/4 (最大元素数)?
"""
import json, struct, collections
CORPUS=r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs=json.load(open(CORPUS,"r",encoding="utf-8"))
if isinstance(recs,dict): recs=recs.get("records") or recs.get("data") or list(recs.values())
FIXED={0x01:1,0x03:1,0x06:2,0x07:4,0x08:4,0x09:8,0x0a:8}
def arrays(payload):
    out=[];i=0;n=len(payload)
    while i<n:
        t=payload[i];i+=1
        if t==0x00: continue
        if t==0x10:
            j=payload.find(b"\x00",i)
            if j<0: break
            i=j+1;continue
        if t in FIXED: i+=FIXED[t];continue
        if t==0x13:
            if i>=n or payload[i]!=0x08: break
            i+=1
            if i+4>n: break
            ln=struct.unpack_from("<I",payload,i)[0];i+=4
            i+=ln;continue
        if t in (0x6b,0x6c):
            if i>=n or payload[i]!=0x08: break
            i+=1
            if i+4>n: break
            bl=struct.unpack_from("<I",payload,i)[0];i+=4
            body=payload[i:i+bl];i+=bl
            if i+4>n: break
            tail=struct.unpack_from("<I",payload,i)[0];i+=4
            out.append((t,bl,body,tail))
            continue
        break
    return out

rows=collections.Counter()
detail=collections.defaultdict(collections.Counter)
for r in recs:
    p=bytes.fromhex(r["payload"])
    for tag,bl,body,tail in arrays(p):
        bf=struct.unpack_from("<I",body,0)[0] if len(body)>=4 else -1
        key=(r.get("svc"),r.get("task"),tag,bl,bf,tail)
        rows[key]+=1
        # 检验关系
        detail[tag]["bl==bodylen"] += (bl==len(body))
        detail[tag]["tail==bl/4"] += (tail==bl//4)
        detail[tag]["tail==bl/4-1"] += (tail==bl//4-1)
        detail[tag]["bf==bl/4"] += (bf==bl//4)
        detail[tag]["total"] += 1

print("=== (svc/task, tag, byteLen, bodyFirst, tail) x 次数 ===")
for k,c in sorted(rows.items(),key=lambda kv:(kv[0][0],kv[0][1],kv[0][2],kv[0][3])):
    print("  %-8s tag=%02X bl=%-4d bf=%-5d tail=%-5d x%d"%("%s/%s"%(k[0],k[1]),k[2],k[3],k[4],k[5],c))

print("\n=== 关系命中率 ===")
for tag in (0x6b,0x6c):
    print(" tag=%02X: %s"%(tag,dict(detail[tag])))
