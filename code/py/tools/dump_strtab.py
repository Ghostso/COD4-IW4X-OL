#!/usr/bin/env python3
"""导出一段连续的 C 字符串表（以 00 分隔）。"""
import sys


def main():
    path = sys.argv[1]
    va = int(sys.argv[2], 0)
    n = int(sys.argv[3], 0) if len(sys.argv) > 3 else 2048
    ib = int(sys.argv[4], 0) if len(sys.argv) > 4 else 0x400000
    b = open(path, "rb").read()
    # 找 VA 对应的文件偏移（用节表）
    import struct
    e = struct.unpack_from("<I", b, 0x3C)[0]
    nsec = struct.unpack_from("<H", b, e + 6)[0]
    osz = struct.unpack_from("<H", b, e + 20)[0]
    so = e + 24 + osz
    rva = va - ib
    off = None
    for i in range(nsec):
        o = so + i * 40
        vs, sva, rs, rp = struct.unpack_from("<IIII", b, o + 8)
        if sva <= rva < sva + max(vs, rs):
            off = rp + (rva - sva)
            break
    if off is None:
        print("not found")
        return
    raw = b[off:off + n]
    parts = raw.split(b"\x00")
    for p in parts:
        if not p:
            continue
        printable = all(32 <= c < 127 for c in p)
        print("%-60r %s" % (p[:60].decode("latin1"), "" if printable else "<<非文本>>"))


if __name__ == "__main__":
    main()
