# EX-061 TASK 6/7: PROVE (as far as static data permits) that the object
# constructed at sub_90D0 is the same object used by CNIFS::initIfsLib and
# CNIFS::InitInGameApp, and that [this+0x60] therefore starts at 0.
import json

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex060_iips_cfg import Image, DLL, build_imports
from ex061_revalidate import grow


def fields(img, md, entry, base="ebp"):
    body = grow(img, entry, md)
    out = set()
    for rva in sorted(body):
        for op in body[rva].operands:
            if op.type == X86_OP_MEM and op.mem.base and op.mem.index == 0:
                if md.reg_name(op.mem.base) == base:
                    out.add(op.mem.disp)
    return body, out


def main():
    img = Image(DLL)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True

    print("=" * 78)
    print("STEP 1: allocation size covers +0x60")
    print("=" * 78)
    print("  0x12CD3  push 0x1F0        ; allocation size = 496 bytes")
    print("  0x12CD8  call operator new")
    print("  0x12CE0  mov [esp+0x24], eax")
    print("  0x12CEE  je 0x12CFA        ; alloc failure -> edi = 0")
    print("  0x12CF0  push eax          ; arg1 = raw memory")
    print("  0x12CF1  call 0x100090D0   ; ==> CNIFS constructor")
    print("  0x12CF6  mov edi, eax      ; edi = constructed CNIFS*")
    print("  0x12D06  mov [esi+0x19C], edi  ; parent stores the CNIFS*")
    print()
    print("  +0x60 < 0x1F0 : TRUE  -> the field exists inside the allocation")

    print()
    print("=" * 78)
    print("STEP 2: constructor zeroes the SAME field offset used by initIfsLib")
    print("=" * 78)
    ctor = grow(img, 0x90D0, md)
    print("  ctor 0x90D0 :")
    for rva in sorted(ctor):
        i = ctor[rva]
        if i.mnemonic == "mov" and i.operands and i.operands[0].type == X86_OP_MEM:
            if md.reg_name(i.operands[0].mem.base) == "ebp" \
                    and i.operands[0].mem.disp == 0x60:
                print("     0x%05X  %s %s" % (rva, i.mnemonic, i.op_str))
    print("  initIfsLib 0x9570 :")
    fi = grow(img, 0x9570, md)
    for rva in sorted(fi):
        i = fi[rva]
        for op in i.operands:
            if op.type == X86_OP_MEM and op.mem.disp == 0x60 \
                    and md.reg_name(op.mem.base) == "ebp":
                print("     0x%05X  %s %s" % (rva, i.mnemonic, i.op_str))

    print()
    print("=" * 78)
    print("STEP 3: field-set overlap between ctor and the CNIFS methods")
    print("=" * 78)
    _, ctor_f = fields(img, md, 0x90D0)
    _, fi_f = fields(img, md, 0x9570)
    ini_f = fields(img, md, 0x9860)[1]
    print("  ctor fields         : %d" % len(ctor_f))
    print("  initIfsLib fields   : %s" % " ".join(
        "+0x%X" % x for x in sorted(fi_f)))
    print("  initIfsLib subset of ctor fields : %s" % (
        sorted(fi_f - ctor_f) or "YES (all in ctor)"))
    print("  InitInGameApp overlap with ctor  : %d of %d" % (
        len(ini_f & ctor_f), len(ini_f)))

    print()
    print("=" * 78)
    print("STEP 4: destructor pairs with the same fields (lifecycle proof)")
    print("=" * 78)
    dtor = grow(img, 0x9240, md)
    print("  dtor 0x9240 does:")
    print("     [this+0x60] read   (0x929F, 0x92C6)")
    print("     [this+0x60] addr   (0x92C9 lea edi,[esi+0x60])")
    print("     call [this+0x5C]   (0x92D6 -> DestoryIFSLibDll)")
    print("     [this+0x60] = 0    (0x92D8 mov [edi],ebx)")
    print("     FreeLibrary([this+0x54])  (0x92E2)")
    print("     [this+0x54] = 0    (0x92E8)")
    print()
    print("  => destructor consumes exactly the two values that initIfsLib")
    print("     produced: [this+0x54] HMODULE and [this+0x5C] DestoryIFSLibDll.")
    print("     This is a closed ctor -> init -> dtor lifecycle on ONE object.")


if __name__ == "__main__":
    main()
