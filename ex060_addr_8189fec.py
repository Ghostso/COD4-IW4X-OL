# EX-060: determine the exact mapping of 0x8189FEC and the
# WIN_IIPS_INIT_ERROR reference structure.
import os
import struct
from collections import OrderedDict

import pefile

EXE = os.path.join("工具", "EX035_DIR", "codoMP_client_shipRetail.exe")
BASE = 0x400000


def main():
    pe = pefile.PE(EXE, fast_load=True)
    pe.parse_data_directories()
    data = open(EXE, "rb").read()

    print("=== 0x8189FEC mapping ===")
    rva = 0x8189FEC - BASE
    print("VA 0x8189FEC -> RVA 0x%X" % rva)
    for s in pe.sections:
        lo = s.VirtualAddress
        hi = s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData)
        if lo <= rva < hi:
            raw = s.PointerToRawData + (rva - s.VirtualAddress)
            print("  in section %s  VA range 0x%X..0x%X" % (
                s.Name.decode(errors="replace").rstrip("\x00"), lo, hi))
            print("  raw offset 0x%X (rawsize 0x%X) raw_backed=%s" % (
                raw, s.SizeOfRawData, raw < s.PointerToRawData + s.SizeOfRawData))
            if raw < s.PointerToRawData + s.SizeOfRawData:
                print("  bytes at that raw offset: %s" % data[raw:raw + 16].hex())
            break

    print()
    print("=== string cluster layout (VA offsets) ===")
    i = data.find(b"WIN_IIPS_INIT_ERROR")
    seg = data[i - 40: i + 140]
    p = 0
    while True:
        z = seg.find(b"\x00", p)
        if z < 0:
            break
        raw = i - 40 + p
        s = data[raw: i - 40 + z]
        if s:
            r = None
            for sec in pe.sections:
                if sec.PointerToRawData <= raw < sec.PointerToRawData + sec.SizeOfRawData:
                    r = sec.VirtualAddress + (raw - sec.PointerToRawData)
                    break
            print("  raw 0x%06X  VA 0x%08X  len %3d  %r" % (
                raw, (BASE + r) if r is not None else 0, len(s), s))
        p = z + 1
        if i - 40 + p >= i + 130:
            break

    print()
    print("=== scan for push imm32 of any 0xDC93xx string ===")
    for s in pe.sections:
        lo = s.PointerToRawData
        hi = lo + s.SizeOfRawData
        blob = data[lo:hi]
        for m in range(len(blob) - 5):
            if blob[m] == 0x68:
                v = struct.unpack_from("<I", blob, m + 1)[0]
                if 0xDC9300 <= v <= 0xDC9500:
                    va = BASE + s.VirtualAddress + m
                    nm = None
                    for sec in pe.sections:
                        if sec.VirtualAddress <= v - BASE < sec.VirtualAddress + sec.SizeOfRawData:
                            off = sec.PointerToRawData + (v - BASE - sec.VirtualAddress)
                            nm = data[off:off + 48].split(b"\x00")[0]
                            break
                    print("  push 0x%08X at VA 0x%08X (section %s) -> %r" % (
                        v, va, s.Name.decode(errors="replace").rstrip("\x00"), nm))


if __name__ == "__main__":
    main()
