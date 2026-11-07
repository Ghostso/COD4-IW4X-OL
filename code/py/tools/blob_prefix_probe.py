#!/usr/bin/env python3
"""11/4 blob 的 [u32 len] 前缀验证 + 内部结构；6/14 的 DEADC0DE 完整含义。"""
import collections
import json
import struct
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

# 1) 所有 0x13 blob 的首 4 字节是否 == len-4（全语料）
print("=== 全语料 0x13 blob 首 4 字节 == len-4 的比例（按 task）===")
stat = collections.defaultdict(lambda: [0, 0])
for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x13 and isinstance(v, bytes) and len(v) >= 4:
            k = (r["svc"], r["task"])
            n = struct.unpack("<I", v[:4])[0]
            stat[k][1] += 1
            if n == len(v) - 4:
                stat[k][0] += 1
rows = sorted(stat.items(), key=lambda x: -x[1][1])
for k, (ok, tot) in rows[:20]:
    print("  %3d/%-4d : %d/%d = %.1f%%" % (k[0], k[1], ok, tot, 100.0 * ok / tot))

# 2) 11/4 的 blob 内层：首 4 字节后是什么
print("\n=== 11/4 blob 内层结构（首 4B 之后）===")
inner = collections.Counter()
for r in corpus:
    if (r["svc"], r["task"]) != (11, 4):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x13 and isinstance(v, bytes) and len(v) >= 12:
            n = struct.unpack("<I", v[:4])[0]
            body = v[4:]
            # body[0] 可能是 batch 类型
            inner[(len(v), n, body[0] if body else -1, body[1:5].hex() if len(body) >= 5 else "")] += 1
for k, v in inner.most_common(12):
    print("  bloblen=%-4d 内len=%-4d b0=%-3d b1-4=%s : %d" % (k[0], k[1], k[2], k[3], v))

# 3) 6/14 的 DEADC0DE 完整 blob
print("\n=== 6/14 含 DEADC0DE 的完整 blob ===")
for r in corpus:
    if (r["svc"], r["task"]) != (6, 14):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x13 and isinstance(v, bytes) and b"\xde\xc0\xad\xde" in v:
            print("  u64头部=%d  bloblen=%d" % (int.from_bytes(b[b.find(b'\x0a')+1:b.find(b'\x0a')+9], 'little') if b'\x0a' in b else -1, len(v)))
            print("  blob=%s" % v[:64].hex(" "))
            print("  明文=%r" % v[4:].decode("latin1").encode("unicode_escape").decode()[:200])
            break
    break
