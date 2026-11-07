#!/usr/bin/env python3
"""从 serialize_ledger.txt 里提取 (tag -> 后续 writeData 位宽) 的配对统计。
用来验证：位流的 5 位标签词表是否与 ByteBuffer TLV 标签同构。"""
import collections
import re
import sys

LEDGER = "_byte_papers/serialize_ledger.txt"

fn_re = re.compile(r"^===== (0x[0-9a-f]+)\s+(\S+)")
bits_re = re.compile(r"writeBits\(imm:(0x[0-9a-f]+)")
data_re = re.compile(r"writeData\((\S+?)\s*,\s*(imm:0x[0-9a-f]+|\?|)\)")


def main():
    fn = None
    pairs = collections.Counter()      # (tag, width_or_?) -> n
    by_fn = collections.defaultdict(list)
    pending = None
    for line in open(LEDGER, encoding="utf-8", errors="replace"):
        m = fn_re.match(line)
        if m:
            fn = m.group(2)
            pending = None
            continue
        if not fn:
            continue
        mb = bits_re.search(line)
        if mb:
            if pending:
                pairs[(pending, "NO-DATA")] += 1
                by_fn[fn].append((pending, "NO-DATA"))
            pending = int(mb.group(1), 16)
            continue
        md = data_re.search(line)
        if md and pending is not None:
            v = md.group(2)
            w = v.split(":")[1] if v.startswith("imm:") else "VAR"
            pairs[(pending, w)] += 1
            by_fn[fn].append((pending, w))
            pending = None

    print("=== tag -> 后续 writeData 位宽 统计 ===")
    allt = sorted({t for t, _ in pairs})
    for t in allt:
        ws = sorted({w for (tt, w) in pairs if tt == t},
                    key=lambda x: (x == "VAR", x == "NO-DATA", x))
        tot = sum(n for (tt, w), n in pairs.items() if tt == t)
        detail = ", ".join("%s×%d" % (w, pairs[(t, w)]) for w in ws)
        print("tag 0x%02x  (共 %3d 次): %s" % (t, tot, detail))

    print("\n=== 每个函数首标签（消息头）===")
    for f, seq in by_fn.items():
        head = [("0x%02x" % t) + "->" + w for t, w in seq[:3]]
        print("%-38s %s" % (f, " | ".join(head)))


if __name__ == "__main__":
    main()
