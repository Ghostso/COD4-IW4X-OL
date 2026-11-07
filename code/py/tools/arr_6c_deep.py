#!/usr/bin/env python3
"""0x6c 原始字节级解剖：28/4 的 508B body 与 count=263 的真实关系；28/1 的 0/4/8B body。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))


def find_6c(b):
    """返回 (偏移, bytelen, body, count) 列表。"""
    out = []
    i = 0
    n = len(b)
    # 直接按文法扫描
    buf = G.Buf(b)
    while buf.i < n:
        if b[buf.i] == 0:
            break
        start = buf.i
        e = G.elem(buf)
        if not buf.ok or e is None:
            break
        if e[0] == 0x6C:
            cnt, body = e[1]
            out.append((start, len(body), body, cnt))
    return out


# 1) 28/4 完整 body 分析
print("=== 28/4 的 0x6c 完整 body（取 1 条）===")
for r in corpus:
    if (r["svc"], r["task"]) != (28, 4):
        continue
    b = bytes.fromhex(r["payload"])
    res = find_6c(b)
    if not res:
        continue
    off, bl, body, cnt = res[0]
    print("报文 len=%d, 0x6c@off=%d bytelen=%d count=%d" % (len(b), off, bl, cnt))
    print("body len=%d, /4=%.3f, /2=%.3f" % (len(body), len(body)/4, len(body)/2))
    # 按 u32 解释
    u32s = [int.from_bytes(body[i:i+4], "little") for i in range(0, len(body) - len(body) % 4, 4)]
    print("u32 个数=%d" % len(u32s))
    print("前 40 u32: %s" % u32s[:40])
    print("后 20 u32: %s" % u32s[-20:])
    print("是否严格递增:", all(u32s[i] < u32s[i+1] for i in range(len(u32s)-1)))
    print("min=%d max=%d distinct=%d" % (min(u32s), max(u32s), len(set(u32s))))
    print("完整 body hex:")
    print(body.hex())
    break

# 2) 28/4 所有报文的 0x6c 是否都相同 body
print("\n=== 28/4 所有 0x6c body 去重 ===")
c = collections.Counter()
cnts = collections.Counter()
for r in corpus:
    if (r["svc"], r["task"]) != (28, 4):
        continue
    b = bytes.fromhex(r["payload"])
    for off, bl, body, cnt in find_6c(b):
        c[body.hex()] += 1
        cnts[cnt] += 1
print("distinct body = %d" % len(c))
for k, n in c.most_common(3):
    print("  x%d len=%d %s..." % (n, len(k)//2, k[:80]))
print("count 值分布:", dict(cnts))

# 3) 28/1 的 0x6c body 去重
print("\n=== 28/1 所有 0x6c body 去重 ===")
c = collections.Counter()
cnts = collections.Counter()
byrun = collections.Counter()
for r in corpus:
    if (r["svc"], r["task"]) != (28, 1):
        continue
    b = bytes.fromhex(r["payload"])
    for off, bl, body, cnt in find_6c(b):
        c[(bl, body.hex(), cnt)] += 1
        cnts[cnt] += 1
print("distinct (len,body,cnt) = %d" % len(c))
for (bl, bh, cnt), n in c.most_common(12):
    print("  x%-3d len=%-3d cnt=%-4d body=%s" % (n, bl, cnt, bh[:60]))
print("count 值分布:", dict(cnts.most_common(10)))
