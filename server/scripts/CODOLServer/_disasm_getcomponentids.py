import os

import capstone
import pefile

IIPS = r"run_codol_001\sandbox_ifs1_20260923\IIPS"
TARGETS = [
    os.path.join(IIPS, "Tenio", "TenTPF.dll"),
    os.path.join(IIPS, "Tenio", "June.dll"),
    os.path.join(IIPS, "Tenio", "TenFact.dll"),
    os.path.join(IIPS, "Tenio", "MemoryAlloctor.dll"),
    os.path.join(IIPS, "Tenio", "ScriptManager.dll"),
]

EXPORT = "GetComponentIDs"


def main():
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = True
    for path in TARGETS:
        print("=" * 90)
        print(path)
        try:
            data = open(path, "rb").read()
            pe = pefile.PE(path, fast_load=True)
            pe.parse_data_directories(
                directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]]
            )
        except Exception as e:
            print("  error:", e)
            continue

        rva = None
        for exp in getattr(pe, "DIRECTORY_ENTRY_EXPORT", []).symbols:
            if exp.name and exp.name.decode("ascii", "replace") == EXPORT:
                rva = exp.address
                break
        if rva is None:
            print("  no export")
            continue

        off = pe.get_offset_from_rva(rva)
        print("  RVA=0x%X off=0x%X imagebase=0x%X" % (rva, off, pe.OPTIONAL_HEADER.ImageBase))
        chunk = data[off:off + 0x500]

        count = 0
        for insn in md.disasm(chunk, rva):
            print("    %08x  %-14s %s" % (insn.address, insn.mnemonic, insn.op_str))
            count += 1
            if count >= 140 or insn.mnemonic == "ret":
                break


if __name__ == "__main__":
    main()
