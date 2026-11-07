import capstone
import pefile

TARGETS = [
    (r"COD OL\IIPS\Tenio\TenTPF.dll", "IIPS_2012_TenTPF"),
    (r"COD OL\Cross\Tenio\TenTPF.dll", "Cross_2013_TenTPF"),
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

    for path, label in TARGETS:
        print("=" * 100)
        print(label, path)
        data = open(path, "rb").read()
        pe = pefile.PE(path, fast_load=True)
        pe.parse_data_directories(
            directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]]
        )
        rva = export_rva(pe, "GetComponentIDs")
        if rva is None:
            print("  export not found")
            continue
        off = pe.get_offset_from_rva(rva)
        print(f"  export RVA=0x{rva:X}")
        # Follow one thunk.
        target = None
        for insn in md.disasm(data[off:off + 8], rva):
            print("    %08x  %-10s %s" % (insn.address, insn.mnemonic, insn.op_str))
            if insn.mnemonic == "jmp" and insn.operands[0].type == capstone.x86.X86_OP_IMM:
                target = insn.operands[0].imm & 0xFFFFFFFF
                break
        if target is None:
            continue
        print(f"  thunk target RVA=0x{target:X}")
        toff = pe.get_offset_from_rva(target)
        print("  --- real function ---")
        count = 0
        hits = []
        for insn in md.disasm(data[toff:toff + 0x600], target):
            line = "    %08x  %-12s %s" % (insn.address, insn.mnemonic, insn.op_str)
            if any(op.type == capstone.x86.X86_OP_IMM and (op.imm & 0xFFFFFFFF) == 985
                   for op in insn.operands):
                line += "   <=== 985"
                hits.append(insn.address)
            print(line)
            count += 1
            if count >= 160 or insn.mnemonic == "ret":
                break
        print(f"  immediate-985 hits in function: {[hex(h) for h in hits]}")


if __name__ == "__main__":
    main()
