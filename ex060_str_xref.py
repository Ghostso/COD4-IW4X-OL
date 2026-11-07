# EX-060 TASK 4/6: find all references to the WIN_IIPS_INIT_ERROR string
# and to the surrounding IIPS error cluster in the EXE, and search for
# any code referencing address 0x8189FEC.
import hashlib
import os
import struct
from collections import OrderedDict, defaultdict

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

EXE = os.path.join("工具", "EX035_DIR", "codoMP_client_shipRetail.exe")


def load(path):
    pe = pefile.PE(path, fast_load=True)
    pe.parse_data_directories()
    return pe, open(path, "rb").read()


def raw_to_rva(pe, off):
    for s in pe.sections:
        if s.PointerToRawData <= off < s.PointerToRawData + s.SizeOfRawData:
            return s.VirtualAddress + (off - s.PointerToRawData)
    return None


def rva_to_raw(pe, rva):
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData):
            off = s.PointerToRawData + (rva - s.VirtualAddress)
            if 0 <= off < s.SizeOfRawData + s.PointerToRawData:
                return off
    return None


def main():
    pe, data = load(EXE)
    base = pe.OPTIONAL_HEADER.ImageBase
    print("EXE base 0x%X" % base)

    # exact string VAs of the IIPS cluster
    cluster = OrderedDict()
    for name in (b"WIN_IIPS_INIT_ERROR", b"WIN_IIPS_PREDOWNLOAD_ERROR",
                 b"WIN_IIPS_INIT_FAILED", b"WIN_IIPS_DLL_ERROR",
                 b"IIPS\\iips.dll"):
        i = data.find(name)
        if i >= 0:
            rva = raw_to_rva(pe, i)
            cluster[name.decode()] = (i, rva, base + rva)
            print("%-28s raw 0x%X RVA 0x%X VA 0x%X" % (
                name.decode(), i, rva, base + rva))
    print()

    # For every 4-byte pointer whose value equals one of the cluster VAs,
    # report its location. These are the relocation/absolute references a
    # 32-bit PE would use for push/lea.
    tgt_by_va = {v[2]: k for k, v in cluster.items()}
    for va, nm in tgt_by_va.items():
        needle = struct.pack("<I", va)
        st = 0
        refs = []
        while True:
            i = data.find(needle, st)
            if i < 0:
                break
            refs.append(i)
            st = i + 1
        print("pointer to %-28s VA 0x%X : %d refs" % (nm, va, len(refs)))
        for r in refs:
            rva = raw_to_rva(pe, r)
            print("     raw 0x%X RVA 0x%X VA 0x%X" % (r, rva, base + rva))

    # Relocations: check if the EXE has a .reloc; without reloc base is fixed
    hasreloc = any(b".reloc" in s.Name for s in pe.sections)
    print("\nhas .reloc section:", hasreloc)

    # search for the 8189FEC value in ANY encoding within EXE
    print("\n--- any encoding of 0x8189FEC in EXE ---")
    for desc, needle in (
        ("le32 0x8189FEC", struct.pack("<I", 0x8189FEC)),
        ("be32 0x8189FEC", struct.pack(">I", 0x8189FEC)),
        ("ascii '8189FEC'", b"8189FEC"),
        ("ascii '8189fec'", b"8189fec"),
        ("ascii '0x8189FEC'", b"0x8189FEC"),
    ):
        st = 0
        c = 0
        while True:
            i = data.find(needle, st)
            if i < 0:
                break
            c += 1
            rva = raw_to_rva(pe, i)
            print("  %-24s raw 0x%X RVA %s" % (
                desc, i, hex(rva) if rva is not None else "None"))
            st = i + 1
        print("  %-24s count=%d" % (desc, c))


if __name__ == "__main__":
    main()
