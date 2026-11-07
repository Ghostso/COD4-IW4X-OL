#!/usr/bin/env python3
"""129 卷: 验证 0x4B7C50 拼出来的 '前缀|<15项续接>' 是否能对上语料里的真实事件行.
同时列出语料里所有 '事件名' 集合, 与 54 条模板 + 3 个前缀 ('LostDevice','RecoverLostDevice','ReducePicmipLimits') 对账.
"""
import json, re, sys, collections
CORPUS = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
def out(s): sys.stdout.write(s.encode("ascii","replace").decode("ascii")+"\n")
def cstr(f):
    e = d.find(b"\x00", f); return d[f:e].decode("latin1")

PREFIXES = {0x9B7BC8: "LostDevice", 0x9B7BD8: "RecoverLostDevice", 0x9B7BEC: "ReducePicmipLimits"}
TAIL = cstr(0x9B7B88)     # '|%s|%llu|...'
SUFFIX_U = cstr(0x9B7BD4) # '|%u'
out("续接片段 0x9B7B88 = %r  (%%指令数=%d, 项数=%d)" % (TAIL, TAIL.count("%"), TAIL.count("%")+1))
out("尾片段 0x9B7BD4 = %r" % SUFFIX_U)
for p, n in PREFIXES.items():
    out("  %-20s 全串 = %r" % (n, n + TAIL))
    out("  %-20s 再加尾 = %r" % ("", n + TAIL + SUFFIX_U.replace("%u","N")))

recs = json.load(open(CORPUS, "r", encoding="utf-8"))
out("")
out("=== 语料事件名统计 (从每个事件行的第1字段抽取) ===")
cnt = collections.Counter()
for r in recs:
    try: b = bytes.fromhex(r.get("payload","") or "")
    except Exception: continue
    if b.find(b"|") < 0: continue
    # 遥测行: 文本里的 "Name|..."
    for m in re.finditer(rb"([A-Z][A-Za-z0-9_]{2,40})\|", b):
        cnt[m.group(1).decode()] += 1
out("  共 %d 个不同事件名" % len(cnt))
for k, v in cnt.most_common(120):
    out("    %-34s %d" % (k, v))
# 找三个前缀是否存在
for n in PREFIXES.values():
    hit = [k for k in cnt if k == n]
    out("  %-22s 精确命中=%s" % (n, hit or "无"))
    rel = [(k, v) for k, v in cnt.items() if k.startswith(n)]
    out("        同前缀 = %s" % (rel or "无"))
# 找出所有带 LostDevice 字样的行样本
out("")
out("=== 语料中含 'LostDevice'/'RecoverLostDevice'/'ReducePicmip' 的样本行 ===")
shown = 0
for r in recs:
    try: b = bytes.fromhex(r.get("payload","") or "")
    except Exception: continue
    for kw in (b"LostDevice", b"RecoverLostDevice", b"ReducePicmip"):
        i = b.find(kw)
        if i >= 0 and shown < 12:
            s = b[max(0,i-40): i+400]
            out("  svc=%s task=%s: %r" % (r.get("svc"), r.get("task"), s.decode("latin1")[:380]))
            shown += 1
            break
if shown == 0:
    out("  (语料里没有任何样本)")

out("")
out("=== 54 条模板中哪些是 '只有名字+续接片段' 型 (名字串不以 | 开头但紧跟的串以 | 开头) ===")
# 扫描 0x9B7xxx 区所有 NUL 串, 打印
out("--- 0x9B7B40..0x9B7C60 字符串 ---")
i = 0x9B7B40
while i < 0x9B7C60:
    e = d.find(b"\x00", i)
    if e < 0: break
    s = d[i:e]
    if s:
        ok = all(32 <= c < 127 for c in s)
        out("  0x%06X %-5s %r" % (i, ok and "txt" or "bin", s.decode("latin1" if ok else "ascii","replace")[:120]))
    i = e + 1
