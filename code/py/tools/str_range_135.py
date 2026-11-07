#!/usr/bin/env python3
"""135 卷工具 C: 打印某个 VA 范围内的所有可打印字符串(带 VA)."""
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)


def dump(va_lo, va_hi, minlen=4):
    lo = va_lo - VA
    hi = va_hi - VA
    seg = d[lo:hi]
    for m in re.finditer(rb"[\x20-\x7e]{%d,}" % minlen, seg):
        print("0x%08X  %s" % (VA + lo + m.start(), m.group().decode("latin1")))


if __name__ == "__main__":
    a = int(sys.argv[1], 0)
    b = int(sys.argv[2], 0)
    dump(a, b)
