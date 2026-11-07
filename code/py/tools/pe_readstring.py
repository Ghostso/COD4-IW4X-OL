#!/usr/bin/env python3
"""读 PE 里给定 VA 处的 C 字符串（可读多个，用空格分隔）。"""
import struct
import sys


def secs_of(b):
    e = struct.unpack_from("<I", b, 0x3C)[0]
    n = struct.unpack_from("<H", b, e + 6)[0]
    osz = struct.unpack_from("<H", b, e + 20)[0]
    opt = e + 24
    magic = struct.unpack_from("<H", b, opt)[0]
    ib = struct.unpack_from("<Q" if magic == 0x20B else "<I", b, opt + (24 if magic == 0x20B else 28))[0]
    so = opt + osz
    out = []
    for i in range(n):
        o = so + i * 40
        nm = b[o:o + 8].rstrip(b"\0").decode("latin1")
        vs, va, rs, rp = struct.unpack_from("<IIII", b, o + 8)
        out.append((nm, va, vs, rp, rs))
    return ib, out


def main():
    b = open(sys.argv[1], "rb").read()
    ib, secs = secs_of(b)
    for a in sys.argv[2:]:
        va = int(a, 0)
        rva = va - ib
        off = None
        for nm, sva, vs, rp, rs in secs:
            if sva <= rva < sva + max(vs, rs):
                off = rp + (rva - sva)
                sec = nm
                break
        if off is None:
            print("%#x  ?" % va)
            continue
        z = b.find(b"\0", off)
        raw = b[off:z]
        print("%#x  sec=%s  %r" % (va, sec, raw[:200].decode("latin1", "replace")))


if __name__ == "__main__":
    main()
