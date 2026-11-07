#!/usr/bin/env python3
"""u64 三个核心 ID 的语义定位：账号ID / 频道ID / 1800154382 的分布与共现。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

ACC = 16701785630074219790      # 0xE7C8A98A6B4C2D0E
CHAN = 1234605616436508552      # 0x1122334455667788
MYST = 1800154382               # 0x6B4E6E0E
U = {ACC: "ACC(账号ID)", CHAN: "CHAN(roomChatChannelID)", MYST: "MYST(1800154382)"}

# 1) 每个 task 里这三个 ID 的角色
print("=== 三个核心 u64 在各 task 的出现次数 ===")
tab = collections.defaultdict(collections.Counter)
for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x0A and isinstance(v, bytes) and len(v) == 8:
            u = int.from_bytes(v, "little")
            if u in U:
                tab[(r["svc"], r["task"])][U[u]] += 1
for k in sorted(tab):
    print("  %3d/%-4d : %s" % (k[0], k[1], dict(tab[k])))

# 2) MYST 1800154382 的完整上下文（在哪个元素位置）
print("\n=== MYST 1800154382 出现时的元素上下文 ===")
ctx = collections.Counter()
for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for j, (t, v) in enumerate(els):
        if t == 0x0A and isinstance(v, bytes) and len(v) == 8:
            if int.from_bytes(v, "little") == MYST:
                prev = els[j - 1] if j else None
                nxt = els[j + 1] if j + 1 < len(els) else None
                def fmt(e):
                    if e is None:
                        return "-"
                    tt, vv = e
                    if isinstance(vv, bytes) and len(vv) <= 8:
                        return "%02x=%d" % (tt, int.from_bytes(vv, "little"))
                    return "%02x" % tt
                ctx[((r["svc"], r["task"]), fmt(prev), fmt(nxt), j, len(els))] += 1
for k, v in ctx.most_common(12):
    print("  %d/%d prev=%s next=%s #%d/%d : %d" % (k[0][0], k[0][1], k[1], k[2], k[3], k[4], v))

# 3) 11/4 的完整元素序列（含 1800154382）
print("\n=== 11/4 元素序列样本（前 2 条，仅显示 u64/关键）===")
n = 0
for r in corpus:
    if (r["svc"], r["task"]) != (11, 4):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    parts = []
    for t, v in els:
        if t == 0x13:
            parts.append("13[%d]" % len(v))
        elif t == 0x0A and isinstance(v, bytes):
            u = int.from_bytes(v, "little")
            parts.append("0a=%d" % u)
        elif isinstance(v, bytes) and len(v) <= 4:
            parts.append("%02x=%d" % (t, int.from_bytes(v, "little")))
        else:
            parts.append("%02x" % t)
    print("  len=%d: %s" % (len(b), " ".join(parts)))
    n += 1
    if n >= 2:
        break

# 4) 6/14 的 76561201696194782 = 0x01001000DEC0ADDE ?
print("\n=== 6/14 的异常 u64 76561201696194782 ===")
print("  hex = 0x%016x" % 76561201696194782)
bb = (76561201696194782).to_bytes(8, "little")
print("  bytes = %s" % bb.hex(" "))
