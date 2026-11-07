# EX-060: verify whether the EXE text is packed/obfuscated and whether the
# "pointer" occurrences are real data refs or coincidental operand bytes.
import os
import struct
from collections import OrderedDict

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = os.path.join("工具", "EX035_DIR", "codoMP_client_shipRetail.exe")


def main():
    pe = pefile.PE(EXE, fast_load=True)
    pe.parse_data_directories()
    data = open(EXE, "rb").read()
    base = pe.OPTIONAL_HEADER.ImageBase
    print("EXE base 0x%X  size 0x%X  sha256 %s" % (
        base, pe.OPTIONAL_HEADER.SizeOfImage,
        __import__("hashlib").sha256(data).hexdigest()))
    print("entry point RVA 0x%X VA 0x%X" % (
        pe.OPTIONAL_HEADER.AddressOfEntryPoint,
        base + pe.OPTIONAL_HEADER.AddressOfEntryPoint))

    print("\n--- data directories ---")
    for d in pe.OPTIONAL_HEADER.DATA_DIRECTORY:
        if d.VirtualAddress or d.Size:
            print("  %-24s RVA 0x%08X size 0x%X" % (
                d.name if hasattr(d, "name") else "?", d.VirtualAddress, d.Size))

    print("\n--- section summary ---")
    for s in pe.sections:
        nm = s.Name.decode(errors="replace").rstrip("\x00")
        print("  %-8s VA 0x%08X vsize 0x%08X raw 0x%08X rawsize 0x%08X chars %08X entropy %.3f" % (
            nm, s.VirtualAddress, s.Misc_VirtualSize, s.PointerToRawData,
            s.SizeOfRawData, s.Characteristics, s.get_entropy()))

    # Check which section contains the ref sites
    print("\n--- section containing the 3 ref sites ---")
    for va in (0x58F104, 0x58F35E, 0x58F3CD):
        rva = va - base
        for s in pe.sections:
            if s.VirtualAddress <= rva < s.VirtualAddress + max(
                    s.Misc_VirtualSize, s.SizeOfRawData):
                print("  VA 0x%X -> section %s chars %08X" % (
                    va, s.Name.decode(errors="replace").rstrip("\x00"),
                    s.Characteristics))
                break
        else:
            print("  VA 0x%X -> no section" % va)

    # Verify: are the 'pointer' bytes preceded by a push opcode (68)?
    print("\n--- are the pointer bytes real push operands? ---")
    for va in (0x58F104, 0x58F35E, 0x58F3CD):
        rva = va - base
        for s in pe.sections:
            if s.VirtualAddress <= rva < s.VirtualAddress + max(
                    s.Misc_VirtualSize, s.SizeOfRawData):
                off = s.PointerToRawData + (rva - s.VirtualAddress)
                ctx = data[off - 6: off + 6]
                print("  VA 0x%X raw 0x%X ctx %s  prev_byte=0x%02X" % (
                    va, off, ctx.hex(), data[off - 1]))
                break

    # String cluster: show the full data around the cluster
    print("\n--- .rdata/.tp3 data cluster around WIN_IIPS strings ---")
    i = data.find(b"WIN_IIPS_INIT_ERROR")
    print(repr(data[i - 260: i + 200]))

    # is 0x8189FEC within any section?
    print("\n--- is VA 0x8189FEC inside any section? ---")
    rva = 0x8189FEC - base
    print("  RVA of 0x8189FEC = 0x%X" % rva)
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress + s.Misc_VirtualSize:
            print("  YES -> %s" % s.Name.decode(errors="replace").rstrip("\x00"))
            break
    else:
        print("  NO -> the address is NOT inside the EXE's mapped image")


if __name__ == "__main__":
    main()
