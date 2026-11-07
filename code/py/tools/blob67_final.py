#!/usr/bin/env python3
"""收尾验证：28/4 尾段、67B blob 中间 9x6 确认、0xff 在 F 角色的精确来源。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402
import zero_role_census2 as Z  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

print("=== 28/4 尾段 [460..519] ===")
for r in corpus:
    if (r["svc"], r["task"]) != (28, 4):
        continue
    b = bytes.fromhex(r["payload"])
    print("len=%d" % len(b))
    print("  [460:] %s" % b[460:].hex(" "))
    print("  [470:] %s" % b[470:].hex(" "))
    break

print("\n=== 67B blob [6..59] 是否严格 9x6 ===")
vals = []
for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x13 and isinstance(v, bytes) and len(v) == 67:
            vals.append(v)
unit = vals[0][6:12]
print("  单元 %s" % unit.hex(" "))
print("  全部样本 [6..59] == 单元x9 ? %s" % all(v[6:60] == unit * 9 for v in vals))
print("  全部样本 [66]==1 ? %s" % all(v[66] == 1 for v in vals))
print("  全部样本 [0..6]==c0a85501fb55 ? %s" % all(v[0:6].hex() == "c0a85501fb55" for v in vals))
print("  全部样本 [60..61]==3c01 ? %s (%d/%d)" % (
    all(v[60:62].hex() == "3c01" for v in vals),
    sum(1 for v in vals if v[60:62].hex() == "3c01"), len(vals)))

print("\n=== 0xff 在 F 角色(整型字段)的精确来源 ===")
exact255 = collections.Counter()
as_neg1 = collections.Counter()
other = collections.Counter()
for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    rm = {}
    Z.walk(G.Buf(b), b, rm)
    for i, x in enumerate(b):
        if x != 0xFF or rm.get(i) != "F":
            continue
        # 定位所属字段
        for t, v in els:
            pass
    for t, v in els:
        if t in G.FIXED and isinstance(v, bytes) and len(v) == G.FIXED[t] and 0xFF in v:
            iv = int.from_bytes(v, "little", signed=(t == 0x07))
            key = (r["svc"], r["task"], hex(t), iv)
            if iv == 255:
                exact255[key] += 1
            elif iv == -1:
                as_neg1[key] += 1
            else:
                other[key] += 1
print("  值=255 (0x000000FF):", dict(exact255))
print("  值=-1  (0xFFFFFFFF):", dict(as_neg1))
print("  其它含 ff 的值:", dict(other))
