#!/usr/bin/env python3
"""最小 x86 反汇编器：用 capstone（若可用）或内置的简易线性扫描。

优先使用 capstone。没有的话退回打印原始字节。
"""
import sys


def main():
    path = sys.argv[1]
    va_start = int(sys.argv[2], 0)
    n = int(sys.argv[3], 0) if len(sys.argv) > 3 else 256
    imagebase = int(sys.argv[4], 0) if len(sys.argv) > 4 else 0x78000

    b = open(path, "rb").read()
    import struct
    e = struct.unpack_from("<I", b, 0x3C)[0]
    nsec = struct.unpack_from("<H", b, e + 6)[0]
    osz = struct.unpack_from("<H", b, e + 20)[0]
    opt = e + 24
    magic = struct.unpack_from("<H", b, opt)[0]
    imagebase = struct.unpack_from(
        "<Q" if magic == 0x20B else "<I", b, opt + (24 if magic == 0x20B else 28))[0]
    so = opt + osz
    secs = []
    for i in range(nsec):
        o = so + i * 40
        nm = b[o:o + 8].rstrip(b"\0").decode("latin1")
        vs, va, rs, rp = struct.unpack_from("<IIII", b, o + 8)
        secs.append((nm, va, vs, rp, rs))

    rva = va_start - imagebase
    off = None
    sec = None
    for nm, va, vs, rp, rs in secs:
        if va <= rva < va + max(vs, rs):
            off = rp + (rva - va)
            sec = nm
            break
    if off is None:
        print("address not in any section")
        return
    print("va=%#x rva=%#x file_off=%#x section=%s" % (va_start, rva, off, sec))
    code = b[off:off + n]

    try:
        from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    except ImportError:
        print("capstone not installed; raw bytes:")
        for i in range(0, len(code), 16):
            print("%#010x  %s" % (va_start + i,
                  " ".join("%02x" % c for c in code[i:i + 16])))
        return

    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    for ins in md.disasm(code, va_start):
        print("%#010x  %-24s %s %s" % (ins.address,
              " ".join("%02x" % c for c in ins.bytes),
              ins.mnemonic, ins.op_str))


if __name__ == "__main__":
    main()
