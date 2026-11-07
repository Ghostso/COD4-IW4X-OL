#!/usr/bin/env python3
"""67B blob 的数值解释穷举：周期模式 + 尾段 float/u32 假设检验。"""
import collections
import json
import struct
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))
vals = []
for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x13 and isinstance(v, bytes) and len(v) == 67:
            vals.append(v)

print("样本 %d 个" % len(vals))
base = collections.Counter(vals).most_common(1)[0][0]

# 1) 周期检测
print("\n=== 周期检测（前 60 字节）===")
for period in range(1, 21):
    ok = all(base[i] == base[i % period] for i in range(60))
    if ok:
        print("  period=%d 成立: %s" % (period, base[:period].hex(" ")))

# 2) [6..59] 段按 period-8 展开
print("\n=== [6..61] 按 8 字节分组 ===")
for g in range(6, 62, 8):
    print("  [%02d] %s" % (g, base[g:g + 8].hex(" ")))

# 3) 尾段 [60..66] 数值解释
print("\n=== 尾段 [60..66] = %s ===" % base[60:67].hex(" "))
for off, name in [(60, "60"), (62, "62"), (64, "64")]:
    for width in (2, 4):
        if off + width <= 67:
            le = int.from_bytes(base[off:off + width], "little")
            be = int.from_bytes(base[off:off + width], "big")
            print("  [%d..%d] u%d LE=%d BE=%d" % (off, off + width - 1, width * 8, le, be))

print("\n=== 尾段 float 假设（各偏移）===")
for off in range(56, 64):
    if off + 4 <= 67:
        fle = struct.unpack("<f", base[off:off + 4])[0]
        fbe = struct.unpack(">f", base[off:off + 4])[0]
        print("  [%d..%d] LE float=%.6g   BE float=%.6g" % (off, off + 3, fle, fbe))

# 4) 变化字节 [62..65] 的联合分布，看是否单调（时间戳/计数器）
print("\n=== [62..65] 全部取值（按出现顺序）===")
seen = []
for v in vals:
    q = v[62:66].hex(" ")
    if q not in seen:
        seen.append(q)
for q in seen:
    print("  ", q, " LE u32 =", int.from_bytes(bytes.fromhex(q.replace(" ", "")), "little"))
