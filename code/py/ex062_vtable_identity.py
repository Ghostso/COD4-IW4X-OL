# EX-062: determine which vtable is the FINAL primary vtable of the object
# (the constructor writes [this+0] TWICE), and enumerate the full CNIFS
# vtable with slot names.
import json
from collections import OrderedDict

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG
from capstone.x86_const import X86_REG_EBP, X86_REG_ESI

from ex060_iips_cfg import Image, DLL, build_imports
from ex061_revalidate import grow


V2 = {   # RVA -> known semantic name (from EX-060/EX-061)
    0x9570: "CNIFS::initIfsLib",
    0x9860: "CNIFS::InitInGameApp",
    0x90D0: "CNIFS::ctor",
    0x9240: "CNIFS::~CNIFS",
    0x9220: "sub_9220 (dtor thunk region)",
    0xA860: "sub_A860",
    0xB0D0: "sub_B0D0",
    0xCBA0: "sub_CBA0",
    0xAED0: "sub_AED0",
    0x6690: "sub_6690",
}


def main():
    img = Image(DLL)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True

    body = grow(img, 0x90D0, md)
    print("=" * 78)
    print("ORDER of writes to [this+0x0] in the constructor")
    print("=" * 78)
    for rva in sorted(body):
        i = body[rva]
        for op in i.operands:
            if op.type == X86_OP_MEM and op.mem.disp == 0 \
                    and md.reg_name(op.mem.base) == "ebp":
                if i.operands and i.operands[0].type == X86_OP_MEM:
                    src = i.operands[1] if len(i.operands) > 1 else None
                    val = ("0x%X" % src.imm) if src is not None \
                        and src.type == X86_OP_IMM else "?"
                    print("   0x%05X  %-26s [this+0x0] = %s" % (
                        rva, "%s %s" % (i.mnemonic, i.op_str), val))

    print()
    print("=" * 78)
    print("FINAL primary vtable = the LAST write to [this+0x0]")
    print("=" * 78)
    last = None
    for rva in sorted(body):
        i = body[rva]
        if i.operands and i.operands[0].type == X86_OP_MEM \
                and i.operands[0].mem.disp == 0 \
                and md.reg_name(i.operands[0].mem.base) == "ebp":
            src = i.operands[1]
            if src.type == X86_OP_IMM:
                last = (rva, src.imm)
    print("   last write: 0x%05X  [this+0] = 0x%X  (RVA 0x%X)" % (
        last[0], last[1], last[1] - img.base))

    # walk that vtable fully
    va = last[1]
    rva = va - img.base
    print()
    print("=" * 78)
    print("CNIFS PRIMARY VTABLE 0x%X (RVA 0x%X)" % (va, rva))
    print("=" * 78)
    print("  slot  off   slot value   target RVA  name")
    print("  ----  ----  -----------  ----------  ----")
    vt = []
    for i in range(0, 0x100):
        s = rva + i * 4
        if not img.is_mapped(s):
            break
        raw = img.read(s, 4)
        if len(raw) < 4:
            break
        val = int.from_bytes(raw, "little")
        if not (img.base <= val < img.base + img.size):
            break
        t = val - img.base
        if not img.is_code(t):
            break
        nm = V2.get(t, "")
        vt.append((i, s, val, t, nm))
        print("  %-4d  +0x%02X  0x%08X  0x%06X  %s" % (
            i, i * 4, val, t, nm))

    print()
    print("total slots: %d  (vtable size 0x%X)" % (len(vt), len(vt) * 4))

    # Where does this vtable end?  What follows?
    end_rva = rva + len(vt) * 4
    print("next dword after the vtable at RVA 0x%X: %s" % (
        end_rva, img.read(end_rva, 16).hex()))

    with open("ex062_vtable.csv", "w", newline="", encoding="utf-8") as f:
        import csv
        w = csv.writer(f)
        w.writerow(["vtable_va", "vtable_rva", "slot", "slot_offset",
                    "slot_rva", "slot_value", "target_rva",
                    "target_va", "name"])
        for i, s, val, t, nm in vt:
            w.writerow(["0x%X" % va, "0x%X" % rva, i, "0x%X" % (i * 4),
                        "0x%X" % s, "0x%X" % val, "0x%X" % t,
                        "0x%X" % (img.base + t), nm])
    print()
    print("wrote ex062_vtable.csv")

    # Other vtables summary
    print()
    print("=" * 78)
    print("secondary / interface vtables (also installed by the ctor)")
    print("=" * 78)
    others = [0x100351F8, 0x10035204, 0x100352EC, 0x100353E8,
              0x10035408, 0x10035418]
    for ova in others:
        orv = ova - img.base
        n = 0
        for i in range(0, 0x100):
            s = orv + i * 4
            if not img.is_mapped(s):
                break
            raw = img.read(s, 4)
            if len(raw) < 4:
                break
            val = int.from_bytes(raw, "little")
            if not (img.base <= val < img.base + img.size):
                break
            if not img.is_code(val - img.base):
                break
            n += 1
        print("   0x%X  slots=%d  size=0x%X" % (ova, n, n * 4))


if __name__ == "__main__":
    main()
