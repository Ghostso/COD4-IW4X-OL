#!/usr/bin/env python3
"""roomChatChannelID = 1234605616436508552 = 0x1122334455667788 的双形态全语料确认。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))
MAGIC = 0x1122334455667788
DEC = str(MAGIC).encode()

bin_cnt = collections.Counter()
blob_cnt = collections.Counter()
other_cnt = collections.Counter()

for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x0A and isinstance(v, bytes) and len(v) == 8:
            if int.from_bytes(v, "little") == MAGIC:
                bin_cnt[(r["svc"], r["task"])] += 1
        elif t == 0x10 and isinstance(v, bytes):
            if DEC in v:
                other_cnt[(r["svc"], r["task"])] += 1
        elif t == 0x13 and isinstance(v, bytes):
            if DEC in v:
                blob_cnt[(r["svc"], r["task"])] += 1
        elif t == 0x6B and isinstance(v, tuple):
            if DEC in v[1]:
                blob_cnt[(r["svc"], r["task"], "6b")] += 1

print("魔数 = %d = 0x%016x" % (MAGIC, MAGIC))
print("  二进制 u64 形态:", dict(bin_cnt), "合计", sum(bin_cnt.values()))
print("  0x10 字符串形态:", dict(other_cnt), "合计", sum(other_cnt.values()))
print("  blob 内明文形态:", dict(blob_cnt), "合计", sum(blob_cnt.values()))

# 输出 6/14 的字符串样本（安全打印）
print("\n=== 6/14 blob 内含该十进制数的样本 ===")
n = 0
for r in corpus:
    if (r["svc"], r["task"]) != (6, 14):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x13 and isinstance(v, bytes) and DEC in v:
            s = v.decode("latin1")
            print("  [%d] %s" % (len(s), s.encode("unicode_escape").decode()[:500]))
            n += 1
            break
    if n >= 2:
        break
