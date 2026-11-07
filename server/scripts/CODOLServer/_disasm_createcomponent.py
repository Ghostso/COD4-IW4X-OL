import os

import capstone
import pefile

TARGETS = [
    (r"run_codol_001\sandbox_ifs1_20260923\IIPS\Tenio\TenTPF.dll", "CreateComponent"),
    (r"run_codol_001\sandbox_ifs1_20260923\IIPS\Tenio\June.dll", "CreateComponent"),
    (r"run_codol_001\sandbox_ifs1_20260923\IIPS\Tenio\TenFact.dll", "CreateComponent"),
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

    for path, export in TARGETS:
        print("=" * 100)
        print(path)
        pe = pefile.PE(path, fast_load=True)
        pe.parse_data_directories(
            directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]]
        )
        rva = export_rva(pe, export)
        if rva is None:
            print("  export not found")
            continue
        off = pe.get_offset_from_rva(rva)
        data = open(path, "rb").read()
        print(f"  {export} RVA=0x{rva:X} off=0x{off:X}")
        chunk = data[off:off + 0x500]
        count = 0
        for insn in md.disasm(chunk, rva):
            mark = ""
            for op in insn.operands:
                if op.type == capstone.x86.X86_OP_IMM and (op.imm & 0xFFFFFFFF) == 985:
                    mark = "   <=== 985"
            print("    %08x  %-12s %s%s" % (insn.address, insn.mnemonic, insn.op_str, mark))
            count += 1
            if count >= 120 or insn.mnemonic == "ret":
                break


if __name__ == "__main__":
    main()
