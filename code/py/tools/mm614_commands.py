#!/usr/bin/env python3
"""6/14 明文子命令全枚举: 除 mmstart/mmbook/mmban 外还有哪些命令?
   - 每个 blob 内层(剥u32 len)的前若干 ASCII 词
   - mmbook/mmban 的完整内容样本
"""
import json, struct, collections, re
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
# 收 6/14 blob 内层
cmds=collections.Counter()
examples=collections.defaultdict(list)
for r in recs:
    if r.get("svc")==6 and r.get("task")==14:
        for d in blobs(bytes.fromhex(r["payload"])):
            if len(d)>=4 and struct.unpack_from("<I",d,0)[0]==len(d)-4:
                inner=d[4:]
                # 取第一个 ASCII 词 (到空格/分号/NUL)
                m=re.match(rb"([A-Za-z_][A-Za-z0-9_]*)",inner)
                tok=m.group(1).decode() if m else "(%02x...)"%inner[0] if inner else "(empty)"
                cmds[tok]+=1
                if len(examples[tok])<3 and tok in ("mmbook","mmban"):
                    examples[tok].append(inner)
print("=== 6/14 blob 内层子命令 token 分布 ===")
for tok,c in cmds.most_common():
    print("  %-20s x%d"%(tok,c))

print("\n=== mmbook 样本 ===")
for x in examples["mmbook"]:
    print("  %r"%x)
print("\n=== mmban 样本 ===")
for x in examples["mmban"]:
    print("  %r"%x)

# mmstart 里所有 "名字 值;" 键名全集
keys=collections.Counter()
for r in recs:
    if r.get("svc")==6 and r.get("task")==14:
        for d in blobs(bytes.fromhex(r["payload"])):
            if len(d)>=4 and struct.unpack_from("<I",d,0)[0]==len(d)-4:
                inner=d[4:]
                if inner.startswith(b"mmstart"):
                    for m in re.finditer(rb"([A-Za-z_][A-Za-z0-9_]*|[0-9]+)\s+([^\s;]+);",inner):
                        keys[m.group(1).decode()]+=1
print("\n=== mmstart 键名全集 (名字,次数) ===")
for k,c in keys.most_common():
    print("  %-28s x%d"%(k,c))
