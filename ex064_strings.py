# EX-064 TASK B/J/K: examine the EXE and IIPSLaunchRestore.dll string
# occurrences, and check for LoadLibrary/GetProcAddress dynamic paths.
import json
import os
import re
import struct

import pefile

EXE = r"工具\EX035_DIR\codoMP_client_shipRetail.exe"
RESTORE = r"工具\EX035_DIR\IIPS\IIPSLaunchRestore.dll"


def raw_to_rva(pe, off):
    for s in pe.sections:
        if s.PointerToRawData <= off < s.PointerToRawData + s.SizeOfRawData:
            return s.VirtualAddress + (off - s.PointerToRawData), \
                s.Name.decode(errors="replace").rstrip("\x00")
    return None, None


def main():
    for label, path in (("EXE", EXE), ("IIPSLaunchRestore.dll", RESTORE)):
        if not os.path.exists(path):
            print("MISSING %s" % path)
            continue
        data = open(path, "rb").read()
        pe = pefile.PE(path, fast_load=True)
        base = pe.OPTIONAL_HEADER.ImageBase
        print("=" * 78)
        print("%s  base 0x%X  size 0x%X" % (
            label, base, pe.OPTIONAL_HEADER.SizeOfImage))
        print("=" * 78)
        for t in (b"GetResourceManagerII", b"GetResourceManager",
                  b"ReleaseResourceManagerII", b"ReleaseResourceManager"):
            st = 0
            while True:
                i = data.find(t, st)
                if i < 0:
                    break
                rva, sec = raw_to_rva(pe, i)
                print("  %-26s raw 0x%06X  RVA 0x%06X  VA 0x%08X  sec %s" % (
                    t.decode(), i, rva, base + rva, sec))
                st = i + 1
        # context around the first GetResourceManagerII
        i = data.find(b"GetResourceManagerII")
        if i >= 0:
            print()
            print("  context around 0x%X:" % i)
            print("    %r" % data[i - 96:i + 160])
        # does it import iips.dll?
        pe2 = pefile.PE(path, fast_load=True)
        pe2.parse_data_directories()
        print()
        print("  import DLLs:")
        if hasattr(pe2, "DIRECTORY_ENTRY_IMPORT"):
            for d in pe2.DIRECTORY_ENTRY_IMPORT:
                print("     %s" % d.dll.decode(errors="replace"))
        else:
            print("     (no import directory)")
        print()
        print("  LoadLibrary / GetProcAddress strings:")
        for s in (b"LoadLibraryA", b"LoadLibraryW", b"LoadLibraryExA",
                  b"LoadLibraryExW", b"GetProcAddress"):
            n = data.count(s)
            if n:
                print("     %-18s x%d" % (s.decode(), n))
        print()


if __name__ == "__main__":
    main()
