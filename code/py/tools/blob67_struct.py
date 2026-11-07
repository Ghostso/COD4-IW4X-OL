#!/usr/bin/env python3
"""67B blob 严格结构验证：最小周期、精确分解、动态尾段与上下文关联。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

recs = []  # (svc,task,idx,blob,elems)
for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for j, (t, v) in enumerate(els):
        if t == 0x13 and isinstance(v, bytes) and len(v) == 67:
            recs.append((r["svc"], r["task"], r["idx"], v, els))

print("样本 %d" % len(recs))
base = recs[0][3]

# 1) 最小周期（区间 [6..59]）
print("\n=== 最小周期验证（区间 [6..59]，54 字节）===")
seg = base[6:60]
for p in range(1, 28):
    if len(seg) % p:
        continue
    if all(seg[i] == seg[i % p] for i in range(len(seg))):
        print("  period=%d  整除  单元=%s  重复 %d 次" % (p, seg[:p].hex(" "), len(seg) // p))

# 2) 精确分解
print("\n=== 分解假设 A: 6 头 + 9x6 + 7 尾 ===")
print("  [0..5]  %s" % base[0:6].hex(" "))
print("  [6..59] %s (54B)" % base[6:60].hex(" "))
print("  [60..66]%s (7B)" % base[60:67].hex(" "))

# 3) 头 6 字节的固定性 + IP/端口
hdr = collections.Counter(v[0:6] for _, _, _, v, _ in recs)
print("\n=== 头 6 字节取值 ===")
for k, c in hdr.most_common():
    print("  %s  x%d  IPv4=%s" % (k.hex(" "), c, ".".join(str(x) for x in k[:4])))

# 4) [6..59] 是否全部一致
pat = collections.Counter(v[6:60] for _, _, _, v, _ in recs)
print("\n=== [6..59] 不同取值个数: %d ===" % len(pat))

# 5) [66] 取值
t66 = collections.Counter(v[66] for _, _, _, v, _ in recs)
print("=== [66] 取值: %s ===" % dict(t66))

# 6) 动态段 [60..65] 与 (svc,task) 的关系
print("\n=== [60..65] 取值 × task ===")
dyn = collections.Counter((s, t, v[60:66].hex(" ")) for s, t, _, v, _ in recs)
for k, c in dyn.most_common(20):
    print("  %d/%d  %s  x%d" % (k[0], k[1], k[2], c))

# 7) 21/1 与 21/12 的元素序列（去掉 blob）
print("\n=== 21/1 元素序列（首个样本，blob 简写）===")
for s, t, idx, v, els in recs:
    if (s, t) == (21, 1):
        seq = []
        for tt, vv in els:
            if tt == 0x13 and isinstance(vv, bytes) and len(vv) == 67:
                seq.append("13[67B]")
            elif isinstance(vv, bytes):
                seq.append("%02x[%dB]%s" % (tt, len(vv), vv.hex()))
            else:
                seq.append("%02x=%r" % (tt, vv))
        print("  " + " ".join(seq))
        break
