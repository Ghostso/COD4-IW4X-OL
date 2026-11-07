# -*- coding: utf-8 -*-
"""Dump PE section layout of a module (file-based, no capstone needed)."""
import struct
import sys


def dump(path):
    d = open(path, "rb").read()
    print("=" * 78)
    print(path)
    print("file size = %d (0x%X)" % (len(d), len(d)))
    # find PE header
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    if d[pe:pe + 4] != b"PE\0\0":
        # try known offset
        for cand in (0x110, 0x80):
            if d[cand:cand + 4] == b"PE\0\0":
                pe = cand
                break
    print("PE offset = 0x%X  sig=%r" % (pe, d[pe:pe + 4]))
    machine, nsects, _, _, _, optsize, chars = struct.unpack_from("<HHIIIHH", d, pe + 4)
    opt = pe + 24
    magic = struct.unpack_from("<H", d, opt)[0]
    if magic == 0x10B:
        entry, bcode, bdata, imagebase, salign, falign = struct.unpack_from("<IIIIII", d, opt + 16)
        sizeofimage, sizeofheaders = struct.unpack_from("<II", d, opt + 56)
    else:
        print("not PE32 (magic 0x%X)" % magic)
        return
    print("machine=0x%X nsects=%d optsize=%d" % (machine, nsects, optsize))
    print("imagebase = 0x%08X" % imagebase)
    print("entry     = 0x%08X" % entry)
    print("SizeOfImage = 0x%X (%d)" % (sizeofimage, sizeofimage))
    print("SizeOfHeaders = 0x%X" % sizeofheaders)
    sec = opt + optsize
    for i in range(nsects):
        off = sec + i * 40
        nm, vs, va, rs, ra, _, _, _, _, fl = struct.unpack_from("<8sIIIIIIHHI", d, off)
        print("  [%d] %-9s VA=0x%08X VS=0x%08X RAW=0x%08X RS=0x%08X flags=0x%08X"
              % (i, nm.rstrip(b"\x00").decode("latin1"), va, vs, ra, rs, fl))


for p in sys.argv[1:]:
    dump(p)
