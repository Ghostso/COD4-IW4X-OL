#!/usr/bin/env python3
"""严格对照: 语料 102/* 的真实字节 vs ol-mod AckOnlyServices.cpp 注释里的 (u32,u32,u8,u64) 形态。"""
import json
CORPUS = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs = json.load(open(CORPUS, "r", encoding="utf-8"))
if isinstance(recs, dict):
    recs = recs.get("records") or recs.get("data") or list(recs.values())

def hexd(b): return " ".join("%02x"%c for c in b)

by_task = {}
for r in recs:
    if r.get("svc") == 102:
        by_task.setdefault(r["task"], []).append(bytes.fromhex(r["payload"]))

print("=== 语料 102/* 每 task 的首条 payload (去重后形态) ===")
for t in sorted(by_task):
    ps = by_task[t]
    uniq = sorted(set(ps))
    print("\n102/%d  条数=%d  不同形态=%d" % (t, len(ps), len(uniq)))
    for u in uniq[:2]:
        print("   len=%d  %s" % (len(u), hexd(u[:120]) + ("..." if len(u)>120 else "")))

# 与 ol-mod 注释期望逐字段比对
print("\n=== 与 ol-mod AckOnlyServices.cpp 期望比对 ===")
# 解析 TLV 为 (tag,val) 列表 (本服务只用 03/08/0a/00)
def parse(p):
    out=[]; i=0
    while i < len(p):
        tag = p[i]; i+=1
        if tag == 0x00: out.append(("term",None)); continue
        if tag == 0x03: out.append(("u8", p[i])); i+=1; continue
        if tag == 0x08:
            import struct; out.append(("u32", struct.unpack_from("<I",p,i)[0])); i+=4; continue
        if tag == 0x0a:
            import struct; out.append(("u64", struct.unpack_from("<Q",p,i)[0])); i+=8; continue
        out.append(("?",tag)); break
    return out

for t in sorted(by_task):
    p = sorted(set(by_task[t]))[0]
    fields = parse(p)
    if t == 7:
        # 只显示头尾
        head = fields[:3]; tail = fields[-2:]
        print("102/7 字段: 前3=%s ... 共%d字段 ... 后2=%s" % (head, len(fields), tail))
    else:
        print("102/%d 字段: %s" % (t, fields))
