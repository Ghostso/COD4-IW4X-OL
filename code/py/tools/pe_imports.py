#!/usr/bin/env python3
"""提取 PE 的导入/导出表，列出 DLL 与函数名。"""
import struct
import sys


def rva2off(b, secs, rva):
    for _n, va, vs, rp, rs in secs:
        span = max(vs, rs)
        if va <= rva < va + span:
            d = rva - va
            return rp + d if d < rs else None
    return None


def sections(b):
    e = struct.unpack_from("<I", b, 0x3C)[0]
    n = struct.unpack_from("<H", b, e + 6)[0]
    osz = struct.unpack_from("<H", b, e + 20)[0]
    opt = e + 24
    magic = struct.unpack_from("<H", b, opt)[0]
    ib = struct.unpack_from("<Q" if magic == 0x20B else "<I", b, opt + (24 if magic == 0x20B else 28))[0]
    ddoff = opt + (112 if magic == 0x20B else 96)
    d = []
    for i in range(16):
        va, sz = struct.unpack_from("<II", b, ddoff + i * 8)
        d.append((va, sz))
    so = opt + osz
    out = []
    for i in range(n):
        o = so + i * 40
        nm = b[o:o + 8].rstrip(b"\0").decode("latin1")
        vs, va, rs, rp = struct.unpack_from("<IIII", b, o + 8)
        out.append((nm, va, vs, rp, rs))
    return ib, out, d


def main():
    path = sys.argv[1]
    b = open(path, "rb").read()
    ib, secs, dd = sections(b)
    print("imagebase=%#x" % ib)
    names = ["export", "import", "resource", "exception", "security", "reloc",
             "debug", "arch", "globalptr", "tls", "loadcfg", "boundimport",
             "iat", "delayimport", "clr", "reserved"]
    for i, (va, sz) in enumerate(dd):
        if va:
            print("dir[%d] %-12s rva=%#x size=%#x" % (i, names[i], va, sz))

    # imports
    va, sz = dd[1]
    if va:
        off = rva2off(b, secs, va)
        print("\n=== imports ===")
        for i in range(4096):
            if off + i * 20 + 20 > len(b):
                break
            ilt, ts, fc, nmr, ft = struct.unpack_from("<IIIII", b, off + i * 20)
            if not any((ilt, ts, fc, nmr, ft)):
                break
            no = rva2off(b, secs, nmr)
            dll = b[no:b.find(b"\0", no)].decode("latin1") if no else "?"
            funcs = []
            if ilt:
                fo = rva2off(b, secs, ilt)
                for j in range(2000):
                    if fo + j * 4 + 4 > len(b):
                        break
                    t = struct.unpack_from("<I", b, fo + j * 4)[0]
                    if not t:
                        break
                    if t & 0x80000000:
                        funcs.append("#%d" % (t & 0xFFFF))
                    else:
                        ho = rva2off(b, secs, t)
                        if ho and ho + 2 < len(b):
                            f = b[ho + 2:b.find(b"\0", ho + 2)].decode("latin1", "replace")
                            funcs.append(f)
            print("%-28s %d  %s" % (dll, len(funcs), ", ".join(funcs[:40])))


if __name__ == "__main__":
    main()
