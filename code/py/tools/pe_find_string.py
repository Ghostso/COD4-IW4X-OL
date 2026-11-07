#!/usr/bin/env python3
"""在 PE 里搜字节串并打印命中处的上下文 (VA 换算), 用于定位反序列化器字面量。

用法: pe_find_string.py <file> <needle-as-hex-or-ascii> [--ctx 32]
"""
import sys


def pe_sections(b):
    import struct
    e_lfanew = struct.unpack_from("<I", b, 0x3C)[0]
    assert b[e_lfanew:e_lfanew + 4] == b"PE\0\0"
    nsec = struct.unpack_from("<H", b, e_lfanew + 6)[0]
    optsz = struct.unpack_from("<H", b, e_lfanew + 20)[0]
    opt = e_lfanew + 24
    magic = struct.unpack_from("<H", b, opt)[0]
    imagebase = struct.unpack_from("<Q" if magic == 0x20B else "<I", b, opt + (24 if magic == 0x20B else 28))[0]
    secoff = opt + optsz
    out = []
    for i in range(nsec):
        o = secoff + i * 40
        name = b[o:o + 8].rstrip(b"\0").decode("latin1")
        vsize, va, rawsize, rawptr = struct.unpack_from("<IIII", b, o + 8)
        out.append((name, va, vsize, rawptr, rawsize))
    return imagebase, out


def rva_to_off(secs, rva):
    for _n, va, vsize, rawptr, rawsize in secs:
        span = max(vsize, rawsize)
        if va <= rva < va + span:
            d = rva - va
            if d < rawsize:
                return rawptr + d
            return None
    return None


def main():
    path = sys.argv[1]
    needle = sys.argv[2]
    ctx = 32
    if "--ctx" in sys.argv:
        ctx = int(sys.argv[sys.argv.index("--ctx") + 1])
    if needle.startswith("hex:"):
        nd = bytes.fromhex(needle[4:])
    else:
        nd = needle.encode("latin1")
    b = open(path, "rb").read()
    imagebase, secs = pe_sections(b)
    print("imagebase=%#x sections=%d" % (imagebase, len(secs)))
    off = 0
    hits = 0
    while True:
        i = b.find(nd, off)
        if i < 0:
            break
        hits += 1
        # 找所属节
        va = None
        for name, sva, vsize, rawptr, rawsize in secs:
            if rawptr <= i < rawptr + rawsize:
                va = imagebase + sva + (i - rawptr)
                sec = name
                break
        print("hit#%d file_off=%#x va=%s sec=%s" % (
            hits, i, ("%#x" % va) if va is not None else "?", va and sec))
        lo = max(0, i - ctx)
        hi = min(len(b), i + len(nd) + ctx)
        print("  ctx:", b[lo:hi])
        off = i + 1
        if hits > 200:
            print("... too many")
            break
    if hits == 0:
        print("no hits")


if __name__ == "__main__":
    main()
