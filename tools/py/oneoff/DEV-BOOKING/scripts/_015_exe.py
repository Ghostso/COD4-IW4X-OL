# -*- coding: utf-8 -*-
"""015: read raw bytes from the packed client EXE (not the runtime dump)."""
import struct
import sys

EXE = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"
BASE = 0x400000
d = open(EXE, "rb").read()

# section table from earlier dump:
# [2] .tp3 VA=0x00A16000 VS=0x0DBB1CC0 RAW=0x00702000 RS=0x00062000
SEC2_VA, SEC2_RAW, SEC2_RS = 0x00A16000, 0x00702000, 0x00062000


def rva_of(va):
    return va - BASE


def fileoff(va):
    rva = rva_of(va)
    if SEC2_VA <= rva < SEC2_VA + SEC2_RS:
        return SEC2_RAW + (rva - SEC2_VA), "sec2"
    return None, None


for a in sys.argv[1:]:
    va = int(a, 16)
    fo, sec = fileoff(va)
    if fo is None:
        print("0x%08X  not in EXE raw section2" % va)
        continue
    chunk = d[fo:fo + 16]
    dw = struct.unpack_from("<4I", chunk, 0) if len(chunk) == 16 else ()
    print("0x%08X  file 0x%06X  %s  %s" % (va, fo, sec,
                                          " ".join("%08X" % x for x in dw)))
