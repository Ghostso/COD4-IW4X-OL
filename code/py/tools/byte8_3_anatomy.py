#!/usr/bin/env python3
"""8/3 解剖：完整结构 + i32 周期 + u32#4 与 blob 的一一映射。"""
import collections
import hashlib
import json
import struct
import sys
import zlib

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402


def main():
    corpus = json.load(open(sys.argv[1], encoding="utf-8"))
    rs = [r for r in corpus if r["svc"] == 8 and r["task"] == 3]
    print("=== 8/3 样本 %d 条 ===" % len(rs))
    print("长度分布: %s" % dict(sorted(
        collections.Counter(r["len"] for r in rs).items())))

    tagcnt = collections.Counter()
    seqs = collections.Counter()
    u32s = collections.Counter()
    u4_blob = collections.defaultdict(set)
    u4_crc = {}
    lengths = collections.Counter()
    for r in rs:
        b = bytes.fromhex(r["payload"])
        good, els, why = G.parse(b)
        if not good:
            continue
        lengths[binary_len(els)] += 1
        for t, v in els:
            tagcnt[t] += 1
        i32 = [struct.unpack("<i", v)[0] for t, v in els if t == 0x07]
        seqs[tuple(i32)] += 1
        us = [struct.unpack("<I", v)[0] for t, v in els if t == 0x08]
        for i, x in enumerate(us):
            u32s[(i, x)] += 1
        blob = [v for t, v in els if t == 0x13][0]
        u4_blob[us[3]].add(hashlib.md5(blob).hexdigest())
        u4_crc[us[3]] = (zlib.crc32(blob) & 0xffffffff,
                         hashlib.md5(blob).digest()[:4].hex())

    print("\n元素标签分布: %s" % {hex(k): v for k, v in sorted(tagcnt.items())})
    print("\n=== 4 个 u32 各位置取值 ===")
    for i in range(4):
        c = collections.Counter({x: n for (j, x), n in u32s.items() if j == i})
        print("  #%d: %s" % (i, c.most_common(8)))
    print("\n=== u32#4 -> blob（一一映射检验）===")
    for k in sorted(u4_blob):
        print("  %08x -> %d 种 blob   crc32=%08x md5[:4]=%s" % (
            k, len(u4_blob[k]), u4_crc[k][0], u4_crc[k][1]))
    print("\n=== i32 序列变体 ===")
    for s, c in seqs.most_common():
        print("  ×%-3d len=%d 前12: %s" % (c, len(s), list(s[:12])))
    print("\n=== i32 周期检验（取最长序列）===")
    s = max(seqs, key=lambda x: len(x))
    body = list(s[5:])
    for p in range(2, 16):
        if all(body[i] == body[i % p] for i in range(len(body))):
            print("  周期 = %d  (%d 项 / %d = %d 轮)" % (
                p, len(body), p, len(body) // p))
            break
    print("\n=== i32 取值频次 top12 ===")
    allv = collections.Counter()
    for s, c in seqs.items():
        for x in s:
            allv[x] += c
    for k, v in allv.most_common(12):
        print("  %5d (0x%04x) ×%d" % (k, k & 0xffff, v))


def binary_len(els):
    n = 1  # 终止符
    for t, v in els:
        if t in G.FIXED:
            n += 1 + G.FIXED[t]
        elif t == 0x10:
            n += 1 + len(v) + 1
        elif t == 0x13:
            n += 1 + 1 + 4 + len(v)
        elif t in (0x6B, 0x6C):
            n += 1 + 1 + 4 + len(v) + 4
    return n


if __name__ == "__main__":
    main()
