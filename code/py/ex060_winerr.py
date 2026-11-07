# EX-060 TASK 4/6: WIN_IIPS_INIT_ERROR in the EXE + 8189FEC xref.
import hashlib
import os
import re
import struct
from collections import OrderedDict

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

EXE = os.path.join("工具", "EX035_DIR", "codoMP_client_shipRetail.exe")
BASE = 0x400000
STR_RAW = 0x6B53A8
TARGET_VA = 0x8189FEC  # 0x400000 + 0x4189FEC
TARGET_RVA = TARGET_VA - BASE


def pe_of(path):
    pe = pefile.PE(path, fast_load=True)
    pe.parse_data_directories()
    return pe


def raw_to_rva(pe, off):
    for s in pe.sections:
        if s.PointerToRawData <= off < s.PointerToRawData + s.SizeOfRawData:
            return s.VirtualAddress + (off - s.PointerToRawData), s
    return None, None


def main():
    pe = pe_of(EXE)
    data = open(EXE, "rb").read()
    print("EXE sha256", hashlib.sha256(data).hexdigest())
    print("base 0x%X size 0x%X" % (BASE, pe.OPTIONAL_HEADER.SizeOfImage))
    print("sections:")
    for s in pe.sections:
        print("  %-10s VA 0x%08X vsize 0x%08X raw 0x%08X rawsize 0x%08X chars %08X" % (
            s.Name.decode(errors="replace").rstrip("\x00"),
            s.VirtualAddress, s.Misc_VirtualSize, s.PointerToRawData,
            s.SizeOfRawData, s.Characteristics))

    # --- string location
    for pat in (b"WIN_IIPS_INIT_ERROR", b"IIPS_INIT_ERROR"):
        i = data.find(pat)
        while i >= 0:
            rva, sec = raw_to_rva(pe, i)
            print("\nstring %r raw 0x%X -> %s RVA 0x%X VA 0x%X" % (
                pat, i, sec.Name.decode(errors="replace").rstrip("\x00"),
                rva, BASE + rva))
            i = data.find(pat, i + 1)

    # --- dump the string context
    print("\ncontext around 0x%X:" % STR_RAW)
    print(repr(data[STR_RAW - 64: STR_RAW + 96]))

    # --- scan for the 8189FEC literal in various encodings
    print("\n--- 8189FEC literal scan in EXE ---")
    for width, enc in ((4, "<I"), (4, ">I")):
        needle = struct.pack(enc, TARGET_VA)
        n = 0
        st = 0
        while True:
            i = data.find(needle, st)
            if i < 0:
                break
            n += 1
            rva, sec = raw_to_rva(pe, i)
            print("  %s raw 0x%X RVA 0x%X VA 0x%X" % (
                enc, i, rva, BASE + rva if rva else 0))
            st = i + 1
        print("  enc %s count=%d" % (enc, n))

    # --- search for the byte pattern of the immediate in code (push/mov)
    # 68 EC 89 81 04 = push 0x8189FEC
    for pat in (bytes([0x68]) + struct.pack("<I", TARGET_VA),
                bytes([0xB8]) + struct.pack("<I", TARGET_VA),
                struct.pack("<I", TARGET_VA)):
        i = data.find(pat)
        c = 0
        while i >= 0:
            c += 1
            rva, sec = raw_to_rva(pe, i)
            print("  pattern %s at raw 0x%X RVA 0x%X" % (
                pat.hex(), i, rva))
            i = data.find(pat, i + 1)
        print("  pattern %s count=%d" % (pat.hex(), c))


if __name__ == "__main__":
    main()
