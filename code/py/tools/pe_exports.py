#!/usr/bin/env python3
"""提取 PE 导出表。"""
import struct
import sys

sys.path.insert(0, "tools")


def rva2off(b, secs, rva):
    for _n, va, vs, rp, rs in secs:
        span = max(vs, rs)
        if va <= rva < va + span:
            d = rva - va
            return rp + d if d < rs else None
    return None


def secs_of(b):
    e = struct.unpack_from("<I", b, 0x3C)[0]
    n = struct.unpack_from("<H", b, e + 6)[0]
    osz = struct.unpack_from("<H", b, e + 20)[0]
    opt = e + 24
    magic = struct.unpack_from("<H", b, opt)[0]
    ib = struct.unpack_from("<Q" if magic == 0x20B else "<I", b, opt + (24 if magic == 0x20B else 28))[0]
    ddoff = opt + (112 if magic == 0x20B else 96)
    d = [struct.unpack_from("<II", b, ddoff + i * 8) for i in range(16)]
    so = opt + osz
    out = []
    for i in range(n):
        o = so + i * 40
        nm = b[o:o + 8].rstrip(b"\0").decode("latin1")
        vs, va, rs, rp = struct.unpack_from("<IIII", b, o + 8)
        out.append((nm, va, vs, rp, rs))
    return ib, out, d


def main():
    b = open(sys.argv[1], "rb").read()
    ib, secs, dd = secs_of(b)
    va, sz = dd[0]
    if not va:
        print("no exports")
        return
    o = rva2off(b, secs, va)
    flags, ts, maj, mnr, nameRva, base, nfun, nname, afun, aname, aord = \
        struct.unpack_from("<IIHHIIIIIII", b, o)
    no = rva2off(b, secs, nameRva)
    print("DLL name:", b[no:b.find(b'\0', no)].decode())
    print("base=%d functions=%d names=%d" % (base, nfun, nname))
    fo = rva2off(b, secs, afun)
    nf = rva2off(b, secs, aname)
    ao = rva2off(b, secs, aord)
    for i in range(nname):
        nr = struct.unpack_from("<I", b, nf + i * 4)[0]
        p = rva2off(b, secs, nr)
        nm = b[p:b.find(b"\0", p)].decode("latin1")
        ordn = struct.unpack_from("<H", b, ao + i * 2)[0]
        fr = struct.unpack_from("<I", b, fo + ordn * 4)[0]
        print("  ord %-4d %#010x  %s" % (ordn, ib + fr, nm))


if __name__ == "__main__":
    main()
