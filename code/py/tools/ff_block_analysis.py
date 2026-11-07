#!/usr/bin/env python3
"""判定载荷是否是「分块加密」：找块边界对齐特征、块内/块间相关性。"""
import sys
from collections import Counter


def main():
    path = sys.argv[1]
    off = int(sys.argv[2], 0)
    b = open(path, "rb").read(off + (1 << 20))[off:]
    print("len", len(b))

    # 1) 16 字节分组下，每组的第 k 字节分布是否均匀（ECB 特征：块内同位置值分布偏斜）
    print("\n[1] 16B 块内每列的最高频值占比（均匀应≈1/256=0.39%）")
    for k in range(16):
        col = b[k::16]
        c = Counter(col)
        top, n = c.most_common(1)[0]
        print("  col %2d: top=%02x %d/%d = %.2f%%  distinct=%d" % (
            k, top, n, len(col), 100.0 * n / len(col), len(c)))

    # 2) 块大小检测：对候选块长 B，测 b[i] 与 b[i+B] 的相关（加密下应无关）
    print("\n[2] 偏移相关性（相同位置跨块比较）")
    for B in (256, 512, 1024, 2048, 4096, 8192, 16384):
        same = sum(1 for i in range(0, min(len(b) - B, 20000))
                   if b[i] == b[i + B])
        print("  B=%-6d 相同字节 %d / 20000 = %.2f%%（随机基线 0.39%%）" % (
            B, same, 100.0 * same / 20000))

    # 3) 找有没有块边界标记
    print("\n[3] 0x4000 边界处 4 字节")
    for i in range(0, min(len(b), 0x4000 * 3), 0x4000):
        print("  %#08x: %s" % (i, b[i:i + 8].hex(" ")))


if __name__ == "__main__":
    main()
