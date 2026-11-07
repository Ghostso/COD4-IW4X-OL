#!/usr/bin/env python3
"""mmbook 的 base64 载荷解码 + 与 roomChatChannelID 魔数的关系；mmban 结构。"""
import base64
import collections
import json
import re
import struct
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

print("=== base64 解码验证 ===")
for s in ["AQAAAAAAAAA=", "iHdmVUQzIhE="]:
    d = base64.b64decode(s)
    print("  %-16s -> %s  u64le=%d  hex=%s" % (
        s, d.hex(" "), int.from_bytes(d, "little"), d.hex()))

MAGIC = 0x1122334455667788
print("  魔数 roomChatChannelID = 0x%016x" % MAGIC)
print("  iHdmVUQzIhE= 解码 = 0x%s" % base64.b64decode("iHdmVUQzIhE=").hex())

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

# mmbook 的 (token, b64) 组合
print("\n=== mmbook 全部 (数字, base64, 尾) 组合 ===")
combo = collections.Counter()
for r in corpus:
    if (r["svc"], r["task"]) != (6, 14):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x13 and isinstance(v, bytes) and b"mmbook" in v:
            s = v[4:].decode("latin1")
            m = re.match(r"mmbook\s+(\d+)\s+(\S+)\s+(\S+)", s)
            if m:
                combo[m.groups()] += 1
for k, v in combo.most_common():
    try:
        dec = base64.b64decode(k[1]).hex()
    except Exception:
        dec = "?"
    print("  x%-4d token=%s b64=%s -> %s  tail=%s" % (v, k[0], k[1], dec, k[2]))

# mmban 结构
print("\n=== mmban 命令去重 ===")
ban = collections.Counter()
for r in corpus:
    if (r["svc"], r["task"]) != (6, 14):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x13 and isinstance(v, bytes) and b"mmban" in v:
            ban[v[4:].decode("latin1")] += 1
for k, v in ban.most_common(6):
    print("  x%-4d %r" % (v, k[:200]))

# roomChatChannelID 取值分布（从 mmstart 明文里提取）
print("\n=== mmstart 里 roomChatChannelID 的取值 ===")
rc = collections.Counter()
for r in corpus:
    if (r["svc"], r["task"]) != (6, 14):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x13 and isinstance(v, bytes) and b"mmstart" in v:
            s = v[4:].decode("latin1")
            m = re.search(r"roomChatChannelID\s+(\d+)", s)
            if m:
                rc[m.group(1)] += 1
for k, v in rc.most_common():
    print("  roomChatChannelID=%-22s : %d" % (k, v))
