#!/usr/bin/env python3
"""单个字节值的全语料分角色普查。用法:
    python -I tools/byte_role_probe.py corpus.json <hexbyte> [<hexbyte> ...]
"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402
import zero_role_census2 as Z  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))
targets = [int(x, 16) for x in sys.argv[2:]]

roles = {t: collections.Counter() for t in targets}
tasks = {t: collections.Counter() for t in targets}
ctxs = {t: collections.Counter() for t in targets}
field_vals = {t: collections.Counter() for t in targets}
tagpos = {t: 0 for t in targets}
fail = 0

for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        fail += 1
        continue
    rm = {}
    Z.walk(G.Buf(b), b, rm)
    for i, x in enumerate(b):
        if x not in roles:
            continue
        ro = rm.get(i, "?")
        roles[x][ro] += 1
        tasks[x][(r["svc"], r["task"], ro)] += 1
        ctxs[x][(b[i - 1] if i else -1, b[i + 1] if i + 1 < len(b) else -1)] += 1
    # 整型字段的精确值
    for t, v in els:
        if t in G.FIXED and isinstance(v, bytes) and len(v) == G.FIXED[t]:
            iv = int.from_bytes(v, "little", signed=(t == 0x07))
            for x in targets:
                if iv == x:
                    field_vals[x][(hex(t), iv)] += 1
                elif x in v:
                    field_vals[x][("<contains>", hex(t), v.hex(), iv)] += 1

print("解析失败 %d 条" % fail)
for x in targets:
    tot = sum(roles[x].values())
    print("\n=== 0x%02x  总 %d 次 ===" % (x, tot))
    print("  角色: %s" % dict(roles[x]))
    print("  上下文 top10:")
    for (a, c), n in ctxs[x].most_common(10):
        pa = "%02x" % a if a >= 0 else "ST"
        pc = "%02x" % c if c >= 0 else "EN"
        print("    %s < %02x > %s  x%d" % (pa, x, pc, n))
    print("  task/role top10:")
    for (s, tk, ro), n in tasks[x].most_common(10):
        print("    %d/%d role=%s x%d" % (s, tk, ro, n))
    print("  整型字段相关 top8:")
    for k, n in field_vals[x].most_common(8):
        print("    %s x%d" % (k, n))
