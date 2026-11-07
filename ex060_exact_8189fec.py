# EX-060 TASK 3: exact search for references to the specific address
# 0x8189FEC across the relevant modules, using properly-aligned decoding.
import hashlib
import os
import struct
from collections import OrderedDict, defaultdict

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

TARGET = 0x8189FEC

MODULES = [
    ("codoMP_client_shipRetail.exe", os.path.join("工具", "EX035_DIR",
     "codoMP_client_shipRetail.exe")),
    ("codoMP_client_shipRetailBase.dll", os.path.join("工具", "EX035_DIR",
     "codoMP_client_shipRetailBase.dll")),
    ("iips.dll", os.path.join("工具", "EX035_DIR", "IIPS", "iips.dll")),
    ("IIPSHost.dll", os.path.join("工具", "EX035_DIR", "IIPS", "IIPSHost.dll")),
    ("IIPSVFS.dll", os.path.join("工具", "EX035_DIR", "IIPS", "IIPSVFS.dll")),
    ("IIPSCheck.dll", os.path.join("工具", "EX035_DIR", "IIPS", "IIPSCheck.dll")),
    ("IIPSHostApp.exe", os.path.join("工具", "EX035_DIR", "IIPS", "IIPSHostApp.exe")),
    ("TenProxy.dll", os.path.join("工具", "EX035_DIR", "TenProxy.dll")),
    ("GbSpy.dll", os.path.join("工具", "EX035_DIR", "GbSpy.dll")),
    ("BugTrace.dll", os.path.join("工具", "EX035_DIR", "BugTrace.dll")),
    ("TerSafe.dll", os.path.join("工具", "EX035_DIR", "TerSafe.dll")),
    ("TenRpcs.dll", os.path.join("工具", "EX035_DIR", "TenRpcs.dll")),
]


def main():
    print("EXACT ADDRESS SEARCH for 0x%08X" % TARGET)
    print("=" * 78)
    for label, path in MODULES:
        if not os.path.exists(path):
            print("%-32s MISSING" % label)
            continue
        data = open(path, "rb").read()
        pe = pefile.PE(path, fast_load=True)
        pe.parse_data_directories()
        base = pe.OPTIONAL_HEADER.ImageBase
        hits = []
        st = 0
        needle = struct.pack("<I", TARGET)
        while True:
            i = data.find(needle, st)
            if i < 0:
                break
            hits.append(i)
            st = i + 1
        # also check other widths
        print("%-32s base 0x%08X  le32 hits=%d" % (label, base, len(hits)))
        for off in hits:
            sec = None
            for s in pe.sections:
                if s.PointerToRawData <= off < s.PointerToRawData + s.SizeOfRawData:
                    sec = s
                    break
            if sec is None:
                print("      raw 0x%X (no section)" % off)
                continue
            rva = sec.VirtualAddress + (off - sec.PointerToRawData)
            # context
            print("      raw 0x%06X RVA 0x%06X VA 0x%08X sec %-8s ctx %s" % (
                off, rva, base + rva,
                sec.Name.decode(errors="replace").rstrip("\x00"),
                data[off - 8:off + 8].hex()))

    print()
    print("=" * 78)
    print("Does 0x%08X map into any loaded module image?" % TARGET)
    print("=" * 78)
    for label, path in MODULES:
        if not os.path.exists(path):
            continue
        pe = pefile.PE(path, fast_load=True)
        base = pe.OPTIONAL_HEADER.ImageBase
        size = pe.OPTIONAL_HEADER.SizeOfImage
        inside = base <= TARGET < base + size
        print("  %-32s [0x%08X, 0x%08X)  contains=%s" % (
            label, base, base + size, inside))


if __name__ == "__main__":
    main()
