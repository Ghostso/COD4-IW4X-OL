#!/usr/bin/env python3
"""打印 PE 节表 (名称/VA/VSize/RawPtr/RawSize/特征)。"""
import struct
import sys


def main():
    b = open(sys.argv[1], "rb").read()
    e = struct.unpack_from("<I", b, 0x3C)[0]
    nsec = struct.unpack_from("<H", b, e + 6)[0]
    optsz = struct.unpack_from("<H", b, e + 20)[0]
    opt = e + 24
    magic = struct.unpack_from("<H", b, opt)[0]
    ib = struct.unpack_from("<Q" if magic == 0x20B else "<I", b, opt + (24 if magic == 0x20B else 28))[0]
    print("magic=%#x imagebase=%#x nsec=%d" % (magic, ib, nsec))
    sec = opt + optsz
    print("%-9s %-11s %-11s %-11s %-11s %-s" % ("name", "VA", "VSize", "RawPtr", "RawSize", "flags"))
    for i in range(nsec):
        o = sec + i * 40
        name = b[o:o + 8].rstrip(b"\0").decode("latin1")
        vs, va, rs, rp = struct.unpack_from("<IIII", b, o + 8)
        fl = struct.unpack_from("<I", b, o + 36)[0]
        print("%-9s %#011x %#011x %#011x %#011x %#010x" % (name, ib + va, vs, rp, rs, fl))


if __name__ == "__main__":
    main()
