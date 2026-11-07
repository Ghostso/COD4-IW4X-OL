#!/usr/bin/env python3
"""为每篇字节论文生成可复跑的证据文件。"""
import json
import struct
import sys
from collections import Counter, defaultdict


def load(path):
    return json.load(open(path, encoding="utf-8"))


def ev_terminator(corpus, out):
    c = Counter()
    for r in corpus:
        p = bytes.fromhex(r["payload"])
        tail = 0
        for b in reversed(p):
            if b == 0:
                tail += 1
            else:
                break
        c[tail] += 1
    lines = ["结尾连续 0x00 的个数分布:", ""]
    for k in sorted(c):
        lines.append("  %d 个 0x00 : %d 条" % (k, c[k]))
    lines.append("")
    lines.append("总计 %d 条" % sum(c.values()))
    open(out, "w", encoding="utf-8").write("\n".join(lines))


def ev_tag(corpus, out, tag, name):
    vals = Counter()
    total = 0
    per = Counter()
    for r in corpus:
        p = bytes.fromhex(r["payload"])
        i = 0
        while i < len(p):
            t = p[i]
            if t == 0:
                i += 1
                continue
            total += 1
            per[t] += 1
            if t == tag:
                vals[tuple(p[i:i + 12])] += 1
            i += 1
    lines = ["tag 0x%02x (%s)" % (tag, name), ""]
    lines.append("在 %d 个 tag 中出现次数: %d" % (total, per.get(tag, 0)))
    lines.append("")
    lines.append("该 tag 首次出现的上下文 (top 12):")
    for k, c in vals.most_common(12):
        lines.append("  %-36s %d" % (" ".join("%02x" % b for b in k), c))
    open(out, "w", encoding="utf-8").write("\n".join(lines))


def main():
    corpus = load(sys.argv[1])
    outdir = sys.argv[2]
    import os
    os.makedirs(outdir, exist_ok=True)
    ev_terminator(corpus, os.path.join(outdir, "ev_terminator.txt"))

    # 逐 tag 统计
    cnt = Counter()
    for r in corpus:
        p = bytes.fromhex(r["payload"])
        for b in p:
            cnt[b] += 1
    lines = ["全部 payload 字节值频次 (前 40):", ""]
    for v, c in cnt.most_common(40):
        lines.append("  %02x  %d" % (v, c))
    open(os.path.join(outdir, "ev_bytefreq.txt"), "w", encoding="utf-8").write(
        "\n".join(lines))

    for tag, name in ((0x01, "bool"), (0x03, "u8"), (0x06, "u16"),
                      (0x07, "i32"), (0x08, "u32"), (0x0A, "u64"),
                      (0x10, "cstr"), (0x13, "blob"), (0x6B, "array4b"),
                      (0x6C, "array")):
        ev_tag(corpus, os.path.join(outdir, "ev_tag_%02x.txt" % tag), tag, name)
    print("done ->", outdir)


if __name__ == "__main__":
    main()
