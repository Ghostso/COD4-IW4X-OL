# EX-061: distinguish genuine CNIFS+0x60 from numerically-coincident +0x60
# fields on OTHER object types, by comparing each function's full field
# access profile against the CNIFS profile recovered in EX-060.
import json
from collections import OrderedDict, defaultdict

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex060_iips_cfg import Image, DLL, build_imports
from ex060_cfg_engine import Function
from ex061_revalidate import grow


def field_profile(img, md, entry, base_reg_names=("ebp", "esi", "edi", "ebx",
                                                  "ecx")):
    """Collect all [reg+disp] field accesses for the given base registers."""
    body = grow(img, entry, md)
    prof = defaultdict(list)
    for rva in sorted(body):
        insn = body[rva]
        for op in insn.operands:
            if op.type != X86_OP_MEM:
                continue
            if op.mem.base == 0 or op.mem.index != 0:
                continue
            br = md.reg_name(op.mem.base)
            if br not in base_reg_names:
                continue
            prof[(br, op.mem.disp)].append(
                (rva, "%s %s" % (insn.mnemonic, insn.op_str)))
    return body, prof


CNIFS_PROFILE = {
    0x50, 0x54, 0x58, 0x5C, 0x60, 0x64, 0xCC, 0xD0,
    0x104, 0x120, 0x150, 0x154, 0x155, 0x158, 0x1C0, 0x1C4, 0x1C5,
    0x1CC, 0x1CD, 0x1CE,
}


def main():
    img = Image(DLL)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True

    print("=" * 78)
    print("CNIFS profile (from EX-060) for reference:")
    print("  " + " ".join("+0x%X" % x for x in sorted(CNIFS_PROFILE)))
    print("=" * 78)

    fns = {
        "CNIFS::initIfsLib": 0x9570,
        "CNIFS::InitInGameApp": 0x9860,
        "sub_90D0": 0x90D0,
        "sub_9240": 0x9240,
        "sub_A860": 0xA860,
        "sub_135B0": 0x135B0,
        "sub_15A00": 0x15A00,
        "sub_2E310": 0x2E310,
    }

    for name, entry in fns.items():
        body, prof = field_profile(img, md, entry)
        disps = sorted(set(d for (b, d) in prof))
        overlap = sorted(set(disps) & CNIFS_PROFILE)
        nonover = sorted(set(disps) - CNIFS_PROFILE)
        print()
        print("-- %s (0x%X)  %d insns" % (name, entry, len(body)))
        print("   distinct field disps: %d" % len(disps))
        print("   overlap with CNIFS profile : %s" % (
            " ".join("+0x%X" % x for x in overlap) or "(none)"))
        print("   non-CNIFS disps            : %s" % (
            " ".join("+0x%X" % x for x in nonover[:24]) or "(none)"))
        score = len(overlap) / max(1, len(CNIFS_PROFILE))
        print("   CNIFS-profile match ratio  : %.2f" % score)
        if (0x60, None) in []:
            pass
        # show who uses +0x60
        s60 = [v for (b, d), v in prof.items() if d == 0x60]
        if s60:
            flat = [x for sub in s60 for x in sub]
            print("   +0x60 sites               : %s" % (
                " ".join("0x%X" % r for r, _ in flat)))


if __name__ == "__main__":
    main()
