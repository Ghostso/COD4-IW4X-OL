# EX-062 TASK I/G: full recovery of sub_197F0 and its exact relationship to
# InitInGameApp (wrapper vs independent implementation).
import json

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG
from capstone.x86_const import X86_REG_ECX, X86_REG_ESI, X86_REG_EAX

from ex060_iips_cfg import Image, DLL, build_imports
from ex061_revalidate import find_entries, grow


def main():
    img = Image(DLL)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True
    imp = build_imports(img)
    entries = sorted(find_entries(img))

    print("=" * 78)
    print("sub_197F0 full disassembly")
    print("=" * 78)
    body = grow(img, 0x197F0, md)
    for rva in sorted(body):
        i = body[rva]
        mark = ""
        if i.mnemonic == "call" and i.operands:
            op = i.operands[0]
            if op.type == X86_OP_IMM:
                mark = "   ; -> sub_%X" % (op.imm - img.base)
            elif op.type == X86_OP_MEM and op.mem.base == 0:
                mark = "   ; %s" % (imp.get(op.mem.disp - img.base),)
            elif op.type == X86_OP_MEM:
                mark = "   ; INDIRECT [%s+0x%X]" % (
                    md.reg_name(op.mem.base), op.mem.disp)
        print("   0x%05X  %-22s %s %s%s" % (
            rva, i.bytes.hex(), i.mnemonic, i.op_str, mark))

    print()
    print("=" * 78)
    print("Does sub_197F0 reference InitInGameApp (0x9860)?")
    print("=" * 78)
    print("   immediate call to 0x9860 : %s" % (
        any(i.mnemonic == "call" and i.operands
            and i.operands[0].type == X86_OP_IMM
            and i.operands[0].imm - img.base == 0x9860
            for i in body.values())))
    print("   the only target it calls  : 0x%X (sub_%X)" % (
        0x10012760, 0x12760))

    print()
    print("=" * 78)
    print("Is sub_197F0 inside any vtable?")
    print("=" * 78)
    raw = open(DLL, "rb").read()
    needle = (img.base + 0x197F0).to_bytes(4, "little")
    offs = []
    st = 0
    while True:
        i = raw.find(needle, st)
        if i < 0:
            break
        offs.append(i)
        st = i + 1
    print("   le32 occurrences of 0x100197F0 : %d" % len(offs))
    for o in offs:
        for s in img.sections:
            if s["raw"] <= o < s["raw"] + s["rawsize"]:
                rva = s["va"] + (o - s["raw"])
                print("      raw 0x%X  RVA 0x%X  section %s" % (
                    o, rva, s["name"]))
                break

    print()
    print("=" * 78)
    print("Is sub_197F0 exported?")
    print("=" * 78)
    exp = {e.address: e.name.decode()
           for e in img.pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name}
    print("   0x197F0 in export table: %s" % (0x197F0 in exp))
    for a, n in sorted(exp.items()):
        print("      %-28s RVA 0x%X" % (n, a))

    print()
    print("=" * 78)
    print("Callers of sub_197F0 (all call forms)")
    print("=" * 78)
    hits = []
    for c in entries:
        b = grow(img, c, md)
        for rva, i in b.items():
            if i.mnemonic == "call" and i.operands \
                    and i.operands[0].type == X86_OP_IMM \
                    and i.operands[0].imm - img.base == 0x197F0:
                hits.append((c, rva))
    print("   immediate callers: %d" % len(set(hits)))
    for c, r in sorted(set(hits))[:20]:
        print("      sub_%X at 0x%X" % (c, r))

    print()
    print("=" * 78)
    print("Vtable slots pointing at sub_197F0 (indirect dispatch)")
    print("=" * 78)
    found = []
    rva = 0x33000
    while rva < 0x42000:
        raw4 = img.read(rva, 4)
        if len(raw4) == 4:
            v = int.from_bytes(raw4, "little")
            if v == img.base + 0x197F0:
                found.append(rva)
        rva += 4
    print("   occurrences in .rdata pointer table region: %d" % len(found))
    for r in found:
        print("      RVA 0x%X" % r)


if __name__ == "__main__":
    main()
