import os

import capstone
import pefile

TARGETS = [
    (r"run_codol_001\sandbox_ifs1_20260923\IIPS\Tenio\June.dll", "SetDLLRegistry"),
    (r"run_codol_001\sandbox_ifs1_20260923\IIPS\Tenio\TenFact.dll", "SetDLLRegistry"),
    (r"run_codol_001\sandbox_ifs1_20260923\IIPS\Tenio\TenTPF.dll", "SetDLLRegistry"),
    (r"run_codol_001\sandbox_ifs1_20260923\IIPS\Tenio\ScriptManager.dll", "SetDLLRegistry"),
]


def export_rva(pe, name):
    entry = getattr(pe, "DIRECTORY_ENTRY_EXPORT", None)
    if entry is None or isinstance(entry, list):
        return None
    for exp in getattr(entry, "symbols", []):
        if exp.name and exp.name.decode("ascii", "replace") == name:
            return exp.address
    return None


def main():
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = True
    for path, name in TARGETS:
        print("=" * 100)
        print(path, "->", name)
        pe = pefile.PE(path, fast_load=True)
        pe.parse_data_directories(
            directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]]
        )
        rva = export_rva(pe, name)
        if rva is None:
            print("  not found")
            continue
        off = pe.get_offset_from_rva(rva)
        data = open(path, "rb").read()
        print(f"  RVA=0x{rva:X} off=0x{off:X}")
        count = 0
        for insn in md.disasm(data[off:off + 0x400], rva):
            print("    %08x  %-12s %s" % (insn.address, insn.mnemonic, insn.op_str))
            count += 1
            if count >= 120 or insn.mnemonic == "ret":
                break


if __name__ == "__main__":
    main()
