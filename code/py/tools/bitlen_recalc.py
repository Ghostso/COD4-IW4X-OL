#!/usr/bin/env python3
"""用 5 位 writeBits 模型，重算 28 个 serialize 的位长。

从 serialize_ledger.txt 的脚本推算：
  writeBits(x)       -> 5 位
  writeData(p, N)    -> N 位
  writeData(p, r)    -> 变长（标 ?）
"""
import re
import sys
from collections import OrderedDict


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "_byte_papers/serialize_ledger.txt"
    cur = None
    rows = []
    total = 0
    unknown = False

    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.rstrip()
        m = re.match(r"^===== (0x[0-9a-f]+)\s+(.*)$", line)
        if m:
            if cur:
                rows.append((cur[0], cur[1], total, unknown))
            cur = (m.group(1), m.group(2))
            total = 0
            unknown = False
            continue
        m = re.match(r"\s+0x[0-9a-f]+\s+writeBits\((.*?)\)\s*$", line)
        if m:
            total += 5          # ★ 5 位模型
            continue
        m = re.match(r"\s+0x[0-9a-f]+\s+writeData\((.*?),\s*(.*?)\)\s*$", line)
        if m:
            nbits = m.group(2).strip()
            if nbits.startswith("imm:"):
                total += int(nbits[4:], 0)
            else:
                unknown = True
            continue
    if cur:
        rows.append((cur[0], cur[1], total, unknown))

    print("%-10s %-6s %-7s %s" % ("serialize", "位长", "字节", "类"))
    for va, name, bits, unk in rows:
        print("%-10s %-6d %-7s %s" % (
            va, bits, ("%.2f" % (bits / 8)) if not unk else "?", name[:56]))
    print("\n共 %d 个" % len(rows))


if __name__ == "__main__":
    main()
