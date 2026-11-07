# -*- coding: utf-8 -*-
"""解析 r_6F0D0000_00C19000.bin —— pcb_ 出现 1205 次, 与资源清单完全一致。

假设这就是 mp/callsignBackground.csv 解析后的内存结构。
目标: 找 ref 旁边的 item ID。
"""
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(ROOT, "mem_linear", "r_6F0D0000_00C19000.bin")
REF_RE = re.compile(rb"\bpcb_[A-Za-z0-9_]{2,60}")


def main():
    b = open(P, "rb").read()
    print("文件 %d 字节 (0x%X)" % (len(b), len(b)))
    ms = list(REF_RE.finditer(b))
    print("pcb_ 命中 %d 处, 唯一 %d" % (len(ms), len(set(m.group(0) for m in ms))))
    print()
    print("前 20 处及其后 32 字节:")
    for m in ms[:20]:
        end = m.end()
        tail = b[end:end + 32]
        print("  @0x%06X %-30s | %s | u32: %s"
              % (m.start(), m.group(0).decode("latin1"),
                 tail[:16].hex(" "),
                 [struct.unpack_from("<I", tail, k)[0]
                  for k in range(0, 16, 4)]))
    print()
    # 检查 ref 之间的间距
    gaps = [ms[i + 1].start() - ms[i].start() for i in range(len(ms) - 1)]
    from collections import Counter
    print("相邻 ref 间距 top 12:", Counter(gaps).most_common(12))
    print()
    # 看有没有连续的数字区
    print("文件里的大整数(u32 在 1000..999999)样本:")
    n = 0
    for o in range(0, min(len(b), 0x40000) - 4, 4):
        v = struct.unpack_from("<I", b, o)[0]
        if 1000 <= v <= 999999:
            print("  @0x%06X = %d" % (o, v))
            n += 1
            if n > 40:
                break
    return 0


if __name__ == "__main__":
    sys.exit(main())
