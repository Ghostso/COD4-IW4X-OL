#!/usr/bin/env python3
"""§七 #5: 0x6b/0x6c 的尾部 u32 与 body 首 u32 的关系。
   语法: [tag][08][u32 byteLen][body][u32 tail]
   paper113说 body首u32 == 元素总数(trailing count). 复核 + 看 body首u32 与 tail 是否恒等, 及与 byteLen 关系。
"""
import json, struct, collections
CORPUS=r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs=json.load(open(CORPUS,"r",encoding="utf-8"))
if isinstance(recs,dict): recs=recs.get("records") or recs.get("data") or list(recs.values())
FIXED={0x01:1,0x03:1,0x06:2,0x07:4,0x08:4,0x09:8,0x0a:8}
def arrays(payload):
    """返回所有 (tag, byteLen, body, tail)."""
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
            i+=ln
            continue
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

stats=collections.Counter()
bodyFirst_eq_tail=0; total=0; examples=collections.defaultdict(list)
for r in recs:
    p=bytes.fromhex(r["payload"])
    for tag,bl,body,tail in arrays(p):
        total+=1
        bf=struct.unpack_from("<I",body,0)[0] if len(body)>=4 else None
        stats[(tag,"tail==bodyFirst")] += (1 if bf==tail else 0)
        stats[(tag,"total")] += 1
        if bf==tail: bodyFirst_eq_tail+=1
        if len(examples[tag])<6:
            examples[tag].append((r.get("svc"),r.get("task"),bl,len(body),bf,tail,body[:16].hex()))

print("0x6b/0x6c 数组总数:",total)
for tag in (0x6b,0x6c):
    print("\n tag=0x%02X: total=%d, body首u32==tail 的=%d"%(tag,stats[(tag,'total')],stats[(tag,'tail==bodyFirst')]))
    print("  byteLen(声明) vs len(body) vs body首u32 vs tail:")
    for svc,task,bl,lbody,bf,tail,bh in examples[tag]:
        print("   %s/%s bl=%d bodylen=%d bodyFirst=%s tail=%s  body[:16]=%s"%(
            svc,task,bl,lbody,bf,tail,bh))

# byteLen 是否 == len(body)
print("\nbyteLen(声明 u32) 是否 == len(body)?")
eq=0;tot=0
for r in recs:
    p=bytes.fromhex(r["payload"])
    for tag,bl,body,tail in arrays(p):
        tot+=1
        if bl==len(body): eq+=1
print("  %d/%d"%(eq,tot))
