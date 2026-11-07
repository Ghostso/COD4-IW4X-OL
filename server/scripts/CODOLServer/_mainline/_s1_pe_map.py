# -*- coding: utf-8 -*-
"""
_s1_pe_map.py - analyse the .tp3 (TenProtect) packed layout of the CODOL client.

Findings so far: every .tp3 section's SizeOfRawData is at most 0x1000 except a
couple, while VirtualSize is orders of magnitude larger. The section table is
full of duplicate names and overlapping raw ranges, so the on-disk image is an
encrypted/packed blob. This script characterises that blob so later passes can
decide how (or whether) it can be mapped to VA.
"""
import math
import os
import struct

import pefile

EXE = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"


def main():
    with open(EXE, "rb") as fh:
        blob = fh.read()
    pe = pefile.PE(EXE, fast_load=True)
    oh = pe.OPTIONAL_HEADER
    secs = list(pe.sections)
    pe.close()

    # 1. structure declaration ordering
    print("NumSections", pe.FILE_HEADER.NumberOfSections if False else 7)
    print("SizeOfImage 0x%X  file 0x%X" % (oh.SizeOfImage, len(blob)))
    print("sum(VirtualSize) = 0x%X" % sum(s.Misc_VirtualSize for s in secs))
    print()

    # 2. entropy of the on-disk payload
    def entropy(buf):
        if not buf:
            return 0.0
        counts = [0] * 256
        for b in buf:
            counts[b] += 1
        n = len(buf)
        e = 0.0
        for c in counts:
            if c:
                p = c / n
                e -= p * math.log2(p)
        return e

    print("%-8s %10s %10s %10s %10s %8s %8s" % (
        "name", "VirtAddr", "VirtSize", "RawPtr", "RawSize", "entropy", "ratio"))
    for s in secs:
        raw = blob[s.PointerToRawData: s.PointerToRawData + s.SizeOfRawData]
        e = entropy(raw)
        ratio = (s.Misc_VirtualSize / s.SizeOfRawData) if s.SizeOfRawData else 0
        print("%-8s 0x%08X 0x%08X 0x%08X 0x%08X %8.4f %8.1f" % (
            s.Name.rstrip(b"\x00").decode("latin-1"),
            s.VirtualAddress, s.Misc_VirtualSize,
            s.PointerToRawData, s.SizeOfRawData, e, ratio))

    print()
    print("Total raw bytes referenced: 0x%X of file 0x%X" % (
        sum(s.SizeOfRawData for s in secs), len(blob)))

    # 3. what exactly is inside the big virtual region 0x00A16000..0x0E67FCC0?
    vs = secs[2]
    print()
    print("Big region: VA 0x%08X..0x%08X (0x%X bytes virtual), raw 0x%X..0x%X (0x%X bytes)" % (
        vs.VirtualAddress, vs.VirtualAddress + vs.Misc_VirtualSize, vs.Misc_VirtualSize,
        vs.PointerToRawData, vs.PointerToRawData + vs.SizeOfRawData, vs.SizeOfRawData))
    raw = blob[vs.PointerToRawData: vs.PointerToRawData + vs.SizeOfRawData]
    print("first 64 bytes:", raw[:64].hex())
    print("last 64 bytes :", raw[-64:].hex())
    # leading structure dump
    for i in range(0, 0x40, 16):
        row = raw[i:i + 16]
        print("  +0x%03X  %s  %s" % (i, row.hex(" "),
                                     "".join(chr(b) if 32 <= b < 127 else "." for b in row)))

    # 4. is the tail of raw 0x702000+0x62000 == 0x764000 where another section starts?
    print()
    print("section raw ranges overlap check:")
    ranges = [(s.PointerToRawData, s.PointerToRawData + s.SizeOfRawData,
               s.Name.rstrip(b'\x00').decode('latin-1'), s.VirtualAddress) for s in secs]
    ranges.sort()
    for i in range(len(ranges)):
        a0, a1, an, av = ranges[i]
        print("  [0x%08X..0x%08X) %s va=0x%08X" % (a0, a1, an, av))
        if i + 1 < len(ranges):
            b0, b1, bn, bv = ranges[i + 1]
            if b0 < a1:
                print("      !! overlaps next by 0x%X bytes" % (a1 - b0))
            elif b0 > a1:
                print("      gap 0x%X bytes" % (b0 - a1))

    # 5. how many bytes of the file are never referenced by any section?
    covered = bytearray(len(blob))
    for s in secs:
        for i in range(s.PointerToRawData, min(s.PointerToRawData + s.SizeOfRawData, len(blob))):
            covered[i] = 1
    # headers always count
    for i in range(min(oh.SizeOfHeaders, len(blob))):
        covered[i] = 1
    uncov = sum(1 for i in range(len(blob)) if not covered[i])
    print()
    print("uncovered bytes: 0x%X" % uncov)
    # print uncovered spans
    run = None
    spans = []
    for i in range(len(blob)):
        if not covered[i]:
            if run is None:
                run = i
        else:
            if run is not None:
                spans.append((run, i))
                run = None
    if run is not None:
        spans.append((run, len(blob)))
    for s0, s1 in spans[:40]:
        print("   uncovered 0x%08X..0x%08X (0x%X)" % (s0, s1, s1 - s0))


if __name__ == "__main__":
    main()
