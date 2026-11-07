# EX-060: determine whether WIN_IIPS_INIT_ERROR is referenced via a
# constant pool / string table rather than a push imm32.
import os
import struct

import pefile

EXE = os.path.join("工具", "EX035_DIR", "codoMP_client_shipRetail.exe")
BASE = 0x400000


def raw_of_va(pe, va):
    rva = va - BASE
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress + max(
                s.Misc_VirtualSize, s.SizeOfRawData):
            return s.PointerToRawData + (rva - s.VirtualAddress), s
    return None, None


def main():
    pe = pefile.PE(EXE, fast_load=True)
    pe.parse_data_directories()
    data = open(EXE, "rb").read()

    strings = [
        ("WIN_IIPS_INIT_ERROR", 0xDC93A8),
        ("WIN_IIPS_PREDOWNLOAD_ERROR", 0xDC93BC),
        ("WIN_IIPS_INIT_FAILED", 0xDC93D8),
        ("IIPS\\iips.dll", 0xDC93F0),
        ("0x%x", 0xDC9400),
        ("WIN_IIPS_DLL_ERROR", 0xDC9408),
    ]

    print("=== references to each string VA (4-byte little-endian) ===")
    for nm, va in strings:
        needle = struct.pack("<I", va)
        refs = []
        st = 0
        while True:
            i = data.find(needle, st)
            if i < 0:
                break
            refs.append(i)
            st = i + 1
        detail = []
        for r in refs:
            for s in pe.sections:
                if s.PointerToRawData <= r < s.PointerToRawData + s.SizeOfRawData:
                    rva = s.VirtualAddress + (r - s.PointerToRawData)
                    detail.append((r, rva,
                                   s.Name.decode(errors="replace").rstrip("\x00")))
                    break
        print("  %-28s VA 0x%08X  refs=%d" % (nm, va, len(refs)))
        for r, rva, sec in detail:
            print("      raw 0x%06X  RVA 0x%06X  VA 0x%08X  sec %s" % (
                r, rva, BASE + rva, sec))

    print()
    print("=== bytes before each string (possible length prefix) ===")
    for nm, va in strings:
        o, s = raw_of_va(pe, va)
        print("  %-28s prev8=%s" % (nm, data[o - 8:o].hex()))

    print()
    print("=== does the cluster look like a length-prefixed string table? ===")
    # scan the region 0xDC9360..0xDC9430 and try to parse as
    # repeated [u32 len][bytes] or as plain NUL-separated
    lo = 0xDC9360 - BASE
    off = None
    for s in pe.sections:
        if s.VirtualAddress <= lo < s.VirtualAddress + s.SizeOfRawData:
            off = s.PointerToRawData + (lo - s.VirtualAddress)
            break
    blob = data[off: off + 0x100]
    print("  region raw 0x%X" % off)
    print("  hex: %s" % blob[:0x80].hex())
    print("  asc: %r" % blob[:0x80])


if __name__ == "__main__":
    main()
