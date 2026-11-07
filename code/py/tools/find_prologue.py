#!/usr/bin/env python3
"""在 [lo,hi) 找函数入口 `55 8b ec` (或 55 8b ec 83 ec / 55 8b ec 81 ec) 并打印."""
import sys
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read()
lo = int(sys.argv[1], 0); hi = int(sys.argv[2], 0)
i = lo
while i < hi:
    if d[i:i+3] == b"\x55\x8b\xec":
        # 前面是否 int3/ret/填充
        prev = d[i-8:i]
        sys.stdout.write("  0x%06X  prev=%s  head=%s\n" % (i, prev.hex(), d[i:i+16].hex()))
    i += 1
