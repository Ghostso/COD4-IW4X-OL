#!/usr/bin/env python3
"""验证 .ifs 头部 8 个 u64 与文件长度的关系（全量）。"""
import os
import struct
import sys


def main():
    root = sys.argv[1]
    files = sorted(f for f in os.listdir(root) if f.endswith(".ifs"))
    ok4 = ok_other = 0
    rows = []
    for fn in files:
        p = os.path.join(root, fn)
        size = os.path.getsize(p)
        with open(p, "rb") as f:
            h = f.read(0xAC)
        if h[:4] != b"nifs":
            continue
        tbl = [struct.unpack_from("<Q", h, 0x0C + i * 8)[0] for i in range(8)]
        tail = struct.unpack_from("<Q", h, 0x4C)[0]
        # 找出哪个 tbl 满足 tbl[i]+tail==size
        match = [i for i, v in enumerate(tbl) if v + tail == size]
        if 4 in match:
            ok4 += 1
        else:
            ok_other += 1
            rows.append((fn, size, tbl, tail, match))

    print("total=%d  tbl[4]+tail==size: %d  else: %d" % (
        len(files), ok4, ok_other))
    for fn, size, tbl, tail, match in rows[:15]:
        print("  %-60s size=%d tail=%d match=%s" % (fn[:60], size, tail, match))


if __name__ == "__main__":
    main()
