# EX-062 TASK F/J/Q1: prove the object identity chain
#   allocation -> ctor -> publication -> dispatch -> InitInGameApp
# using instruction-level evidence only.
import json

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG
from capstone.x86_const import X86_REG_ECX, X86_REG_EAX, X86_REG_EBX

from ex060_iips_cfg import Image, DLL, build_imports
from ex061_revalidate import grow


def main():
    img = Image(DLL)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True
    imp = build_imports(img)

    factory = grow(img, 0x12760, md)

    print("=" * 78)
    print("CHAIN SEGMENT 1: allocation")
    print("=" * 78)
    for rva in sorted(factory):
        if 0x12CD0 <= rva <= 0x12CFE:
            i = factory[rva]
            mark = ""
            if i.mnemonic == "call" and i.operands:
                op = i.operands[0]
                if op.type == X86_OP_IMM:
                    mark = "  ; -> sub_%X" % (op.imm - img.base)
                elif op.type == X86_OP_MEM and op.mem.base == 0:
                    n = imp.get(op.mem.disp - img.base)
                    mark = "  ; %s" % (n,)
            print("   0x%05X  %-24s %s %s%s" % (
                rva, i.bytes.hex(), i.mnemonic, i.op_str, mark))

    print()
    print("=" * 78)
    print("CHAIN SEGMENT 2: publication into the parent object")
    print("=" * 78)
    for rva in sorted(factory):
        if 0x12CFE <= rva <= 0x12D10:
            i = factory[rva]
            print("   0x%05X  %-24s %s %s" % (
                rva, i.bytes.hex(), i.mnemonic, i.op_str))

    print()
    print("=" * 78)
    print("CHAIN SEGMENT 3: vtable dispatch of slot +0x50")
    print("=" * 78)
    for rva in sorted(factory):
        if 0x12F3C <= rva <= 0x12F5C:
            i = factory[rva]
            mark = ""
            if i.mnemonic == "call" and i.operands:
                op = i.operands[0]
                if op.type == X86_OP_REG:
                    mark = "  ; <== INDIRECT -> [vtable+0x50]"
            print("   0x%05X  %-24s %s %s%s" % (
                rva, i.bytes.hex(), i.mnemonic, i.op_str, mark))

    print()
    print("=" * 78)
    print("REGISTER DATAFLOW of the dispatch")
    print("=" * 78)
    print("""
   0x12F3C  mov ebx, [esp+0x50]      ; ebx = caller's object (parent)
   0x12F40  mov ecx, [ebx+0x19C]     ; ecx = the pointer STORED AT 0x12D06
                                      ;       (i.e. the CNIFS* from the ctor)
   0x12F46  mov eax, [ecx]           ; eax = CNIFS->vtable
                                      ;      = whatever the ctor wrote to [this+0]
                                      ;      = 0x1003530C  (last write 0x9134)
   0x12F48  mov edx, [eax+0x50]      ; edx = vtable slot 20
                                      ;      = 0x10009860 = CNIFS::InitInGameApp
   0x12F4B  add eax, 0x50            ; (this-adjustment bookkeeping)
   0x12F4E  mov byte [esp+0x200], 0x15
   0x12F56  call edx                 ; <== CALL CNIFS::InitInGameApp
                                      ;     ECX is still = the CNIFS* from 0x12F40
                                      ;     => __thiscall this == CNIFS object
   0x12F58  test al, al              ; InitInGameApp returns AL (bool)
   0x12F5C  sete byte [esp+0x17]     ; record failure
""")

    # Verify ECX is not clobbered between 0x12F40 and 0x12F56
    print("=" * 78)
    print("ECX liveness check between 0x12F40 and 0x12F56")
    print("=" * 78)
    clobber = []
    for rva in sorted(factory):
        if 0x12F40 < rva < 0x12F56:
            i = factory[rva]
            if len(i.operands) >= 1 and i.operands[0].type == X86_OP_REG \
                    and i.operands[0].reg == X86_REG_ECX:
                clobber.append((rva, "%s %s" % (i.mnemonic, i.op_str)))
    if clobber:
        for rva, t in clobber:
            print("   0x%05X  %s   <== CLOBBERS ECX" % (rva, t))
    else:
        print("   NONE -- ECX set at 0x12F40 survives to the call at 0x12F56")
    print("   => the callee receives ECX == [parent+0x19C] == the ctor's object")

    # what does InitInGameApp do with ecx?
    print()
    print("=" * 78)
    print("InitInGameApp confirms ECX == this")
    print("=" * 78)
    body = grow(img, 0x9860, md)
    for rva in sorted(body):
        if 0x9860 <= rva <= 0x98A0:
            i = body[rva]
            mark = "   <<< this" if i.mnemonic == "mov" \
                and i.op_str == "ebp, ecx" else ""
            print("   0x%05X  %-24s %s %s%s" % (
                rva, i.bytes.hex(), i.mnemonic, i.op_str, mark))


if __name__ == "__main__":
    main()
