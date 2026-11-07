#!/usr/bin/env python3
"""两个未定魔数深挖：0xD692ADAB / 0x8D51E398 的完整报文上下文与共现。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))
MAGIC_A = 0xD692ADAB  # -695030357
MAGIC_B = 0x8D51E398  # -1924013160


def dump_msg(r):
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    out = []
    for i, (t, v) in enumerate(els):
        if isinstance(v, bytes):
            if len(v) in (1, 2, 4, 8):
                iv = int.from_bytes(v, "little", signed=(t == 0x07))
                out.append("#%d:%s=%d" % (i, hex(t), iv))
            else:
                esc = v.decode("latin1", "replace").encode("unicode_escape").decode()
                out.append("#%d:%s[%d]=%s" % (i, hex(t), len(v), esc[:30]))
        else:
            out.append("#%d:%s=%r" % (i, hex(t), v))
    return " | ".join(out)


for name, magic in [("A 0xD692ADAB", MAGIC_A), ("B 0x8D51E398", MAGIC_B)]:
    print("\n########## 魔数 %s ##########" % name)
    bytask = collections.Counter()
    samples = []
    pos = collections.Counter()
    for r in corpus:
        b = bytes.fromhex(r["payload"])
        good, els, why = G.parse(b)
        if not good:
            continue
        for i, (t, v) in enumerate(els):
            if t in (0x07,) and isinstance(v, bytes) and len(v) == 4:
                iv = int.from_bytes(v, "little", signed=True)
                if iv == magic:
                    bytask[(r["svc"], r["task"])] += 1
                    pos[(i, len(els))] += 1
                    if len(samples) < 4:
                        samples.append(r)
    print("  出现 task:", dict(bytask))
    print("  元素位置 (i/总):", dict(pos.most_common(8)))
    for r in samples:
        print("  --- %d/%d run=%s ---" % (r["svc"], r["task"], r.get("run")))
        print("     %s" % dump_msg(r))

# 两者是否同一条报文里共存
print("\n=== 两魔数共存检查 ===")
both = 0
onlyA = onlyB = 0
for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    ha = hb = False
    for t, v in els:
        if t == 0x07 and isinstance(v, bytes) and len(v) == 4:
            iv = int.from_bytes(v, "little", signed=True)
            if iv == MAGIC_A:
                ha = True
            if iv == MAGIC_B:
                hb = True
    if ha and hb:
        both += 1
    elif ha:
        onlyA += 1
    elif hb:
        onlyB += 1
print("  只 A=%d, 只 B=%d, 共存=%d" % (onlyA, onlyB, both))
