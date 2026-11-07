# EX-061: resolve the dual role of CNIFS+0x60.
#
# initIfsLib writes it  (0x97A9: mov [ebp+0x60],eax  <- CreateIFSLibDll result)
# InitInGameApp reads it at 0x9A2B/0x9B51/0x9B66/0x9B7B as a vtable object.
#
# If the SAME field, then the vtable calls at +0x2C are on the CreateIFSLibDll
# RESULT object, not on the HOST/IIPS object.  That would be a strong finding.
# Verify: does InitInGameApp ever write [this+0x60]?  And what is the vtable
# slot +0x2C?
import json

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG
from capstone.x86_const import X86_REG_EBP, X86_REG_ECX

from ex060_iips_cfg import Image, DLL, build_imports
from ex060_cfg_engine import Function


def main():
    img = Image(DLL)
    imports = build_imports(img)
    fn = Function(img, 0x9860, "InitInGameApp").run().build_bbs()
    fi = Function(img, 0x9570, "initIfsLib").run().build_bbs()

    print("=" * 78)
    print("Does InitInGameApp WRITE [this+0x60] anywhere?")
    print("=" * 78)
    wrote = False
    for rva, insn in sorted(fn.insns.items()):
        if insn.mnemonic in ("mov", "lea") and "[ebp + 0x60]" in insn.op_str:
            dst = insn.op_str.split(",")[0].strip()
            if dst.startswith("dword ptr") or dst.startswith("byte ptr"):
                print("  0x%05X  %s %s" % (rva, insn.mnemonic, insn.op_str))
                wrote = True
    if not wrote:
        print("  NO -- InitInGameApp never writes [this+0x60]")

    print()
    print("=" * 78)
    print("initIfsLib: the ONLY write to [arg+0x60]")
    print("=" * 78)
    for rva, insn in sorted(fi.insns.items()):
        if "[ebp + 0x60]" in insn.op_str:
            print("  0x%05X  %-24s %s %s" % (
                rva, insn.bytes.hex(), insn.mnemonic, insn.op_str))

    print()
    print("=" * 78)
    print("vtable slot used at 0x9A35/0x9B5B/0x9B70/0x9B88")
    print("=" * 78)
    for site, argpush in ((0x9A2B, 0x9A33), (0x9B51, 0x9B59),
                          (0x9B66, 0x9B6E), (0x9B7B, 0x9B84)):
        print("  site 0x%05X:" % site)
        for rva in sorted(fn.insns):
            if site <= rva <= site + 0x10:
                insn = fn.insns[rva]
                print("     0x%05X  %-24s %s %s" % (
                    rva, insn.bytes.hex(), insn.mnemonic, insn.op_str))

    print()
    print("  -> pattern is:  ecx = [this+0x60] ; eax = [ecx] ; edx = [eax+0x2C]")
    print("                  push <slot-id>  ; call edx")
    print("  => [this+0x60] is an interface/COM-like pointer whose")
    print("     vtable slot +0x2C takes one integer id (1, 3, 4, 5).")

    print()
    print("=" * 78)
    print("Is the [this+0x60] interface pointer the SAME field initIfsLib writes?")
    print("=" * 78)
    print("  CNIFS::initIfsLib(+0x9570)  this = arg1 (push ebp at 0x99D1)")
    print("  CNIFS::InitInGameApp(+0x9860) this = ecx (mov ebp,ecx at 0x989B)")
    print("  Same caller -> same object -> SAME field offset 0x60.")
    print()
    print("  CONSEQUENCE: if [this+0x60] is written ONLY at 0x97A9 with the")
    print("  CreateIFSLibDll() return value, then the InitInGameApp reads at")
    print("  0x9A2B..0x9B7B consume the object returned by CreateIFSLibDll.")
    print("  The id arguments 1/3/4/5 are then CreateIFSLibDll-defined slots.")

    print()
    print("=" * 78)
    print("Other writers of a +0x60 field -- different object types?")
    print("=" * 78)
    from ex061_revalidate import grow
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True
    for name, entry in (("sub_90D0", 0x90D0), ("sub_135B0", 0x135B0),
                        ("sub_2E310", 0x2E310)):
        body = grow(img, entry, md)
        print("  -- %s (0x%X) %d insns" % (name, entry, len(body)))
        for rva in sorted(body):
            insn = body[rva]
            if "[ebp + 0x60]" in insn.op_str or "[ecx + 0x60]" in insn.op_str:
                print("       0x%05X  %-22s %s %s" % (
                    rva, insn.bytes.hex(), insn.mnemonic, insn.op_str))
        # how is ebp/this obtained?
        for rva in sorted(body):
            if rva > entry + 0x60:
                break
            insn = body[rva]
            if insn.mnemonic == "mov" and insn.operands \
                    and insn.operands[0].type == X86_OP_REG \
                    and md.reg_name(insn.operands[0].reg) == "ebp" \
                    and len(insn.operands) > 1 \
                    and insn.operands[1].type == X86_OP_MEM:
                print("       this-prologue: 0x%05X %s %s" % (
                    rva, insn.mnemonic, insn.op_str))


if __name__ == "__main__":
    main()
