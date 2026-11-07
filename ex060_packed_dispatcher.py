# EX-060: inspect the .tp3 packed region around the IIPS error push sites
# to determine whether a real code dispatcher exists and what the error
# code operand is.
import os
import struct

import pefile

EXE = os.path.join("工具", "EX035_DIR", "codoMP_client_shipRetail.exe")
BASE = 0x400000


def main():
    pe = pefile.PE(EXE, fast_load=True)
    pe.parse_data_directories()
    data = open(EXE, "rb").read()

    # Show raw bytes around each IIPS push site as a linear dump plus the
    # candidate "real" instruction boundary: push imm32 (68) then the
    # following bytes.
    for va, nm in ((0x58F103, "PREDOWNLOAD"), (0x58F35D, "DLL_ERROR"),
                   (0x58F3CC, "INIT_FAILED"), (0x58F281, "0x%x")):
        rva = va - BASE
        sec = None
        for s in pe.sections:
            if s.VirtualAddress <= rva < s.VirtualAddress + max(
                    s.Misc_VirtualSize, s.SizeOfRawData):
                sec = s
                break
        off = sec.PointerToRawData + (rva - sec.VirtualAddress)
        print("=" * 74)
        print("push site %s VA 0x%X raw 0x%X" % (nm, va, off))
        print("  bytes[0:48] : %s" % data[off:off + 48].hex())
        print("  ascii       : %r" % data[off:off + 48])
        # preceding 32 bytes
        print("  before[32]  : %s" % data[off - 32:off].hex())

    print()
    print("=" * 74)
    print("Search the whole EXE for '%s' (the generic error formatter)" % "0x%x")
    i = data.find(b"0x%x\x00")
    while i >= 0:
        r = None
        for s in pe.sections:
            if s.PointerToRawData <= i < s.PointerToRawData + s.SizeOfRawData:
                r = s.VirtualAddress + (i - s.PointerToRawData)
                break
        print("  raw 0x%X VA 0x%X" % (i, BASE + r if r else 0))
        i = data.find(b"0x%x\x00", i + 1)

    print()
    print("=" * 74)
    print("Distribution of push imm32 string refs near the IIPS cluster")
    # list all pushes into 0xDC9300-0xDC9500 sorted by VA (done above), now
    # show 0x40 bytes before/after the 0x58F0xx cluster to see if there is a
    # table format.
    rva = 0x58F000 - BASE
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress + max(
                s.Misc_VirtualSize, s.SizeOfRawData):
            off = s.PointerToRawData + (rva - s.VirtualAddress)
            print(data[off:off + 0x500].hex())
            break


if __name__ == "__main__":
    main()
