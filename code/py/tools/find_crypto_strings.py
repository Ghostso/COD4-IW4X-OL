#!/usr/bin/env python3
"""在客户端 EXE 里找 "aes" / "IWff" / "sha256" 相关字符串的完整上下文。"""
import struct
import sys

sys.path.insert(0, "tools")
from pe_find_string import pe_sections  # noqa: E402


def main():
    path = sys.argv[1]
    b = open(path, "rb").read()
    ib, secs = pe_sections(b)

    def va_of(off):
        for name, sva, vsize, rawptr, rawsize in secs:
            if rawptr <= off < rawptr + rawsize:
                return ib + sva + (off - rawptr), name
        return None, None

    for needle in (b"aes\x00", b"IWff", b"sha256", b"IWffu100", b"IWffs100"):
        print("=== %r ===" % needle)
        off = 0
        n = 0
        while True:
            i = b.find(needle, off)
            if i < 0 or n >= 6:
                break
            va, sec = va_of(i)
            lo, hi = max(0, i - 48), min(len(b), i + 96)
            print("  va=%s sec=%s  %r" % (
                ("%#x" % va) if va else "?", sec, b[lo:hi]))
            off = i + 1
            n += 1
        print()


if __name__ == "__main__":
    main()
