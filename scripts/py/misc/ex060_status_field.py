# EX-060 TASK 1/5: the CNIFS status field [ebp+0xcc] and error-state
# production chain inside initIfsLib.
from ex060_iips_cfg import Image, DLL, build_imports
from ex060_cfg_engine import Function, callsite_info


def main():
    img = Image(DLL)
    imports = build_imports(img)
    fi = Function(img, 0x9570, "initIfsLib").run().build_bbs()

    print("=== every write to [ebp+0xcc] (status field) in initIfsLib ===")
    for rva, insn in fi.insns.items():
        if "[ebp + 0xcc]" in insn.op_str and insn.mnemonic == "mov":
            print("   +0x%X  %-20s %s" % (rva, insn.bytes.hex(), insn.op_str))

    print()
    print("=== every write to [ebp+0x54..0x60] (member slots) ===")
    for rva, insn in fi.insns.items():
        if insn.mnemonic == "mov" and "dword ptr [ebp + 0x" in insn.op_str:
            print("   +0x%X  %-20s %s" % (rva, insn.bytes.hex(), insn.op_str))

    print()
    print("=== return-value productions (AL) ===")
    for rva, insn in fi.insns.items():
        if insn.mnemonic in ("xor", "mov") and insn.op_str.startswith("al"):
            print("   +0x%X  %-20s %s" % (rva, insn.bytes.hex(), insn.op_str))

    print()
    print("=== error-string call sites (sub_4310) and their state writes ===")
    calls = []
    for rva, insn in fi.insns.items():
        if insn.mnemonic == "call" and insn.op_str == "0x10004310":
            calls.append(rva)
    for c in calls:
        print("  call sub_4310 at +0x%X" % c)
        # find the following state write
        nxt = c
        for rva in sorted(fi.insns):
            if rva > c:
                insn = fi.insns[rva]
                if insn.mnemonic == "mov" or insn.mnemonic == "jmp":
                    print("      next: +0x%X  %s %s" % (
                        rva, insn.mnemonic, insn.op_str))
                break

    print()
    print("=== status field mapping by branch ===")
    branches = [
        (0x9704, "LoadLibraryW == NULL", "0x971C", 1),
        (0x9785, "GetProcAddress(CreateIFSLibDll) == NULL", "0x9795", 2),
        (0x97AE, "CreateIFSLibDll returned 0", "0x971C", 1),
        (0x97D5, "GetProcAddress(DestoryIFSLibDll) == NULL", "0x97E5", 3),
    ]
    for rva, why, setat, val in branches:
        print("  +0x%X  %-40s -> status=[ebp+0xcc]=%d at +%s" % (
            rva, why, val, setat))

    print()
    print("=== BB 0x9770 : the success branch after LoadLibraryW ===")
    for rva in fi.bbs[0x9770].insns:
        insn = fi.insns[rva]
        mark = ""
        if insn.mnemonic == "push" and insn.operands:
            op = insn.operands[0]
            if op.type == 2:
                s = img.cstr(op.imm - img.base, 64)
                if s:
                    mark = '   ; "%s"' % s.decode(errors="replace")
        print("   %08X  %-20s %s %s%s" % (
            insn.address, insn.bytes.hex(), insn.mnemonic, insn.op_str, mark))
    print("   succ:", fi.bbs[0x9770].succ)

    print()
    print("=== IAT slot 0x10033014 = GetProcAddress (checked) ===")
    print("   ", imports.get(0x33014))
    print("=== IAT slot 0x10033010 = LoadLibraryW (checked) ===")
    print("   ", imports.get(0x33010))


if __name__ == "__main__":
    main()
