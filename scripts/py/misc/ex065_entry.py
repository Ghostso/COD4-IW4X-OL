# EX-065 PHASE 1: recover tcls_core.exe process entry, TLS callbacks, CRT
# startup, and the path from main/WinMain to sub_8D2A2.
#
# Read-only offline static analysis. No patching, no dynamic execution.
import json
import os

import pefile

TCLS = r"WeGame\tcls\tcls_core.exe"


def main():
    pe = pefile.PE(TCLS, fast_load=True)
    pe.parse_data_directories()
    base = pe.OPTIONAL_HEADER.ImageBase
    data = open(TCLS, "rb").read()
    print("=" * 78)
    print("tcls_core.exe  base 0x%X  size 0x%X" % (
        base, pe.OPTIONAL_HEADER.SizeOfImage))
    print("=" * 78)
    print("entry point RVA 0x%X  (VA 0x%X)" % (
        pe.OPTIONAL_HEADER.AddressOfEntryPoint,
        base + pe.OPTIONAL_HEADER.AddressOfEntryPoint))
    print("subsystem %d" % pe.OPTIONAL_HEADER.Subsystem)
    print("DLL characteristics 0x%X" % pe.OPTIONAL_HEADER.DllCharacteristics)
    print()
    print("sections:")
    for s in pe.sections:
        print("  %-10s VA 0x%08X vsize 0x%08X raw 0x%08X rawsize 0x%08X ch %08X"
              % (s.Name.decode(errors="replace").rstrip("\x00"),
                 s.VirtualAddress, s.Misc_VirtualSize,
                 s.PointerToRawData, s.SizeOfRawData, s.Characteristics))

    print()
    print("data directories:")
    for d in pe.OPTIONAL_HEADER.DATA_DIRECTORY:
        if d.VirtualAddress or d.Size:
            print("  %-24s RVA 0x%08X size 0x%X" % (
                d.name if hasattr(d, "name") else "?", d.VirtualAddress, d.Size))

    # TLS
    print()
    print("=" * 78)
    print("TLS callbacks")
    print("=" * 78)
    if hasattr(pe, "DIRECTORY_ENTRY_TLS"):
        tls = pe.DIRECTORY_ENTRY_TLS.struct
        for f in tls.__field_names__ if hasattr(tls, "__field_names__") else []:
            print("  %-26s 0x%X" % (f, getattr(tls, f)))
        cb = getattr(tls, "AddressOfCallBacks", 0)
        print("  AddressOfCallBacks        VA 0x%X" % cb)
        if cb:
            rva = cb - base
            for i in range(8):
                o = _r2r(pe, rva + i * 4)
                v = int.from_bytes(data[o:o + 4], "little")
                if v == 0:
                    break
                print("  callback[%d] VA 0x%X  RVA 0x%X" % (i, v, v - base))
    else:
        print("  (no TLS directory)")

    # load config
    print()
    print("=" * 78)
    print("imports")
    print("=" * 78)
    if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
        for d in pe.DIRECTORY_ENTRY_IMPORT:
            print("  %s (%d)" % (d.dll.decode(errors="replace"),
                                 len(d.imports)))


def _r2r(pe, rva):
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress + max(
                s.Misc_VirtualSize, s.SizeOfRawData):
            return s.PointerToRawData + (rva - s.VirtualAddress)
    return 0


if __name__ == "__main__":
    main()
