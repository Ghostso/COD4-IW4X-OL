#!/usr/bin/env python3
"""两魔数按原始字节搜索（避免有符号/无符号混淆）。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

print("0xD692ADAB = %d (unsigned) / %d (signed)" % (0xD692ADAB, 0xD692ADAB - 2**32))
print("0x8D51E398 = %d (unsigned) / %d (signed)" % (0x8D51E398, 0x8D51E398 - 2**32))
print("memory 记的 -695030357 = 0x%08X" % (695030357 and (-695030357 + 2**32)))
print("memory 记的 -1924013160 = 0x%08X" % (-1924013160 + 2**32))

targets = {
    "A_0xD692ADAB": bytes.fromhex("d692adab"),
    "B_0x8D51E398": bytes.fromhex("8d51e398"),
    "mem_A_0x%08X" % (-695030357 + 2**32): (-695030357 + 2**32).to_bytes(4, "little"),
    "mem_B_0x%08X" % (-1924013160 + 2**32): (-1924013160 + 2**32).to_bytes(4, "little"),
}

for name, raw in targets.items():
    print("\n########## %s  raw=%s ##########" % (name, raw.hex()))
    bytask = collections.Counter()
    pos = collections.Counter()
    total = 0
    for r in corpus:
        b = bytes.fromhex(r["payload"])
        i = b.find(raw)
        if i < 0:
            continue
        total += 1
        good, els, why = G.parse(b)
        # 找出这是哪个元素的值
        idx = None
        if good:
            for j, (t, v) in enumerate(els):
                if isinstance(v, bytes) and v == raw:
                    idx = (j, len(els), hex(t))
                    break
        bytask[(r["svc"], r["task"])] += 1
        pos[idx] += 1
    print("  报文数=%d" % total)
    print("  task:", dict(bytask))
    print("  元素位置:", dict(pos.most_common(10)))
