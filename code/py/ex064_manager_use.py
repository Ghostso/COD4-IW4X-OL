# EX-064 TASK E/F/G: what does IIPSLaunchRestore.dll actually do with the
# manager pointer returned by GetResourceManagerII?
#
# Facts already known:
#   0x3CA1  mov [esi+0xA8], eax     ; store manager*
#   0x3CB0  mov edx, [eax]
#   0x3CB2  mov edx, [edx+0x68]     ; vtable slot at offset 0x68
#   0x3CB8  call edx
import json

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex064_restore_gpa import Img

RESTORE = r"工具\EX035_DIR\IIPS\IIPSLaunchRestore.dll"


def main():
    img = Img(RESTORE)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True

    print("=" * 78)
    print("EVERY dispatch through [X+0xA8] (the stored manager*)")
    print("=" * 78)
    lo, hi = img.codesec()
    hits = {}
    rva = lo
    while rva < hi:
        insn = next(md.disasm(img.read(rva, 16), img.base + rva), None)
        if insn is None:
            rva += 1
            continue
        for o in insn.operands:
            if o.type == X86_OP_MEM and o.mem.disp == 0xA8 \
                    and o.mem.base != 0 and o.mem.index == 0:
                hits[rva] = "%s %s" % (insn.mnemonic, insn.op_str)
        rva += insn.size
    for r in sorted(hits):
        print("   0x%05X  %s" % (r, hits[r]))

    print()
    print("=" * 78)
    print("the two manager-vtable dispatches that follow (offset +0x68 / +4)")
    print("=" * 78)
    for site in (0x3CB0, 0x3CB2, 0x3CB8, 0x3CD4, 0x3CDC, 0x3CE4):
        insn = next(md.disasm(img.read(site, 16), img.base + site), None)
        if insn:
            print("   0x%05X  %-24s %s %s" % (
                site, insn.bytes.hex(), insn.mnemonic, insn.op_str))

    print()
    print("=" * 78)
    print("struct IIPSRestoreManager-ish field usage around +0xA8")
    print("=" * 78)
    for off in (0xA0, 0xA4, 0xA8, 0xAC, 0xB0):
        st = []
        rva = lo
        while rva < hi:
            insn = next(md.disasm(img.read(rva, 16), img.base + rva), None)
            if insn is None:
                rva += 1
                continue
            for o in insn.operands:
                if o.type == X86_OP_MEM and o.mem.disp == off \
                        and o.mem.base != 0 and o.mem.index == 0:
                    b = md.reg_name(o.mem.base)
                    if b in ("esi", "edi", "eax", "ecx", "edx", "ebx"):
                        st.append(rva)
            rva += insn.size
        uniq = sorted(set(st))
        print("   +0x%02X : %3d sites  %s" % (
            off, len(uniq), ["0x%X" % x for x in uniq[:12]]))

    print()
    print("=" * 78)
    print("do the manager slot-1 and slot-5 offsets (+0x04 / +0x14) appear")
    print("as vtable fetches in IIPSLaunchRestore.dll?")
    print("=" * 78)
    for off in (0x04, 0x14, 0x68, 0x6C, 0x00):
        st = []
        rva = lo
        while rva < hi:
            insn = next(md.disasm(img.read(rva, 16), img.base + rva), None)
            if insn is None:
                rva += 1
                continue
            # mov reg,[reg2+off]  then call reg  within 0x20
            if insn.mnemonic == "mov" and len(insn.operands) == 2 \
                    and insn.operands[0].type == X86_OP_REG \
                    and insn.operands[1].type == X86_OP_MEM \
                    and insn.operands[1].mem.disp == off \
                    and insn.operands[1].mem.base != 0:
                dreg = md.reg_name(insn.operands[0].reg)
                r2 = rva + insn.size
                for _ in range(6):
                    j = next(md.disasm(img.read(r2, 16),
                                       img.base + r2), None)
                    if j is None:
                        break
                    if j.mnemonic == "call" and j.operands \
                            and j.operands[0].type == X86_OP_REG \
                            and md.reg_name(j.operands[0].reg) == dreg:
                        st.append((rva, r2, dreg))
                        break
                    if j.mnemonic.startswith("ret"):
                        break
                    r2 += j.size
            rva += insn.size
        print("   sloto 0x%02X : %d dispatch sites %s" % (
            off, len(st), [("0x%X->0x%X" % (a, b)) for a, b, _ in st[:8]]))


if __name__ == "__main__":
    main()
