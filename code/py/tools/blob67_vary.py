#!/usr/bin/env python3
"""67 字节 blob 的逐字节变异性 + 字段假设检验。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

groups = collections.defaultdict(list)
for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x13 and isinstance(v, bytes) and len(v) == 67:
            groups[(r["svc"], r["task"])].append(v)

for k in sorted(groups):
    vals = groups[k]
    print("\n=== %d/%d : %d 个样本 ===" % (k[0], k[1], len(vals)))
    print("  字节位置 : 不同值个数 : 最常见值(次数)")
    for i in range(67):
        col = collections.Counter(v[i] for v in vals)
        n = len(col)
        mv, mc = col.most_common(1)[0]
        flag = "" if n == 1 else "  <<< 变化"
        print("  [%02d] n=%-3d %02x(x%d)%s" % (i, n, mv, mc, flag))
    # 假设：0..3 = IP
    ips = set(".".join(str(v[i]) for i in range(4)) for v in vals)
    print("  [0..3] 解读为 IPv4: %s" % ips)
    p_be = set(int.from_bytes(v[4:6], "big") for v in vals)
    p_le = set(int.from_bytes(v[4:6], "little") for v in vals)
    print("  [4..5] BE u16: %s   LE u16: %s" % (sorted(p_be), sorted(p_le)))
