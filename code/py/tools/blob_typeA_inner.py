#!/usr/bin/env python3
"""解 0x13 类型A(6/14,11/4) 内层剥掉u32长度头后的 '02 0X 00 00' 结构.
目标: 判断 02 是否是类型码, 0X 是否是元素数*2, 还是 u16 小端长度.
"""
import json, collections, struct, sys
CORPUS=r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs=json.load(open(CORPUS,"r",encoding="utf-8"))
if isinstance(recs,dict): recs=recs.get("records") or recs.get("data") or list(recs.values())

# 语法v5解析器 (简化: 只找 0x13)
TAGS={0x01:('bool',1),0x03:('u8',1),0x06:('u16',2),0x07:('i32',4),
      0x08:('u32',4),0x09:('i64',8),0x0a:('u64',8)}

def parse_blobs(payload):
    """返回该payload里所有0x13 blob的data (剥外层 [u32 len][data])."""
    out=[]; i=0; n=len(payload)
    while i<n:
        t=payload[i]; i+=1
        if t==0x00: continue
        if t==0x10:
            j=payload.find(b"\x00",i)
            if j<0: break
            i=j+1; continue
        if t in TAGS:
            i+=TAGS[t][1]; continue
        if t in (0x13,0x6b,0x6c):
            if i>=n or payload[i]!=0x08: break
            i+=1
            if i+4>n: break
            ln=struct.unpack_from("<I",payload,i)[0]; i+=4
            data=payload[i:i+ln]; i+=ln
            if t==0x6b or t==0x6c:
                i+=4  # trailing count u32
            if t==0x13: out.append(data)
            continue
        break
    return out

# 统计 11/4 与 6/14 内层(剥4字节len头)前几字节
for svc,task,label in [(11,4,"11/4"),(6,14,"6/14")]:
    starts=collections.Counter()
    total=0; head2=collections.Counter(); lenprefix_ok=0
    for r in recs:
        if r.get("svc")==svc and r.get("task")==task:
            p=bytes.fromhex(r["payload"])
            for data in parse_blobs(p):
                total+=1
                if len(data)<4: continue
                decl=struct.unpack_from("<I",data,0)[0]
                if decl==len(data)-4:
                    lenprefix_ok+=1
                    inner=data[4:]
                    if len(inner)>=4:
                        starts[inner[:4].hex()]+=1
                        # 前2字节
                        head2[inner[:2].hex()]+=1
    print("=== %s: blobs=%d, 首u32==len-4 的=%d"%(label,total,lenprefix_ok))
    print("  剥头后前4字节 Top15:", starts.most_common(15))
    print("  前2字节 Top15:", head2.most_common(15))
    print()
