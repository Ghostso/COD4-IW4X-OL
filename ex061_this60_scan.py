# EX-061 TASK 1: whole-image scan of every memory access with
# displacement 0x60 relative to any base register, plus disambiguation
# of which base register it is.
#
# Read-only. No patching, no dynamic execution.
import json
import re
import struct
from collections import OrderedDict, defaultdict

import capstone as cs
from capstone.x86 import (
    X86_OP_IMM, X86_OP_MEM, X86_OP_REG, X86_REG_EBP, X86_REG_ESP,
)

from ex060_iips_cfg import Image, DLL, build_imports

DISP = 0x60


def main():
    img = Image(DLL)
    base = img.base
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True

    # Linear sweep over .text only, but record every instruction so we can
    # later verify alignment. We sweep from 0x1000 upward and rely on
    # capstone's own length to stay aligned.
    hits = []
    rva = 0x1000
    end = 0x33000
    # find code section bounds
    codesecs = [s for s in img.sections if s["chars"] & 0x20000000]
    lo = min(s["va"] for s in codesecs)
    hi = max(s["va"] + s["vsize"] for s in codesecs)
    print("code sections: %s" % [(s["name"], hex(s["va"]), hex(s["vsize"]))
                                 for s in codesecs])
    rva = lo
    while rva < hi:
        code = img.read(rva, 16)
        if len(code) < 1:
            break
        insn = next(md.disasm(code, base + rva), None)
        if insn is None:
            rva += 1
            continue
        for i, op in enumerate(insn.operands):
            if op.type != X86_OP_MEM:
                continue
            if op.mem.disp != DISP:
                continue
            hits.append((rva, insn, i, op))
        rva += insn.size

    print("total instructions with disp==0x60: %d" % len(hits))

    # classify by base register and index register
    def regname(r):
        return md.reg_name(r) if r else None

    by_base = defaultdict(list)
    for rva, insn, oi, op in hits:
        by_base[(regname(op.mem.base), regname(op.mem.index),
                 op.mem.scale)].append((rva, insn, oi, op))

    print()
    print("=== breakdown by (base, index, scale) ===")
    for k in sorted(by_base, key=lambda x: (str(x[0]), str(x[1]), x[2])):
        b, i, s = k
        print("  base=%-6s index=%-6s scale=%d : %d hits" % (
            b, i, s, len(by_base[k])))

    # focus on ebp-based (thiscall frame) and other simple bases
    print()
    print("=== ebp+0x60 accesses (thiscall/stack-frame candidates) ===")
    for rva, insn, oi, op in by_base.get(("ebp", None, 1), []):
        print("  +0x%05X  %-24s %s %s" % (
            rva, insn.bytes.hex(), insn.mnemonic, insn.op_str))

    print()
    print("=== other-base +0x60 accesses ===")
    for k in sorted(by_base, key=lambda x: (str(x[0]), str(x[1]), x[2])):
        if k == ("ebp", None, 1):
            continue
        print("  -- base=%s index=%s scale=%d" % k)
        for rva, insn, oi, op in by_base[k]:
            print("     +0x%05X  %-24s %s %s" % (
                rva, insn.bytes.hex(), insn.mnemonic, insn.op_str))


if __name__ == "__main__":
    main()
