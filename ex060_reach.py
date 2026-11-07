# EX-060: reachability + xref analysis.
import json
import re
import struct
from collections import OrderedDict, defaultdict, deque

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

from ex060_iips_cfg import Image, DLL, build_imports, build_exports
from ex060_cfg_engine import Function, COND_JMP


def reachable_bbs(fn, entry):
    seen = set()
    q = deque([entry])
    while q:
        b = q.popleft()
        if b in seen or b not in fn.bbs:
            continue
        seen.add(b)
        for s, k in fn.bbs[b].succ:
            q.append(s)
    return seen


def bb_of(fn, rva):
    """Find the basic block containing rva."""
    for start, b in fn.bbs.items():
        if b.insns and b.insns[0] <= rva <= b.insns[-1]:
            return start
    return None


def main():
    img = Image(DLL)
    imports = build_imports(img)
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True

    # ---- TASK 1/2: initIfsLib CFG + reachability of +0x96E9
    print("=" * 78)
    print("TASK 1/2 : initIfsLib (0x9570) reachability")
    print("=" * 78)
    f = Function(img, 0x9570, "initIfsLib").run().build_bbs()
    reach = reachable_bbs(f, 0x9570)
    t96e9 = bb_of(f, 0x96E9)
    print("entry 0x9570 reachable BBs:", len(reach), "of", len(f.bbs))
    print("BB containing 0x96E9 = 0x%X" % t96e9)
    print("0x96E9 BB reachable from entry 0x9570 :", t96e9 in reach)
    for target in (0x977C, 0x97A5, 0x97CC, 0x97D3, 0x96EF):
        b = bb_of(f, target)
        print("  0x%X in BB 0x%X reachable=%s" % (
            target, b, (b in reach) if b else None))

    # ---- Which BBs are NOT reachable
    print("\nUNREACHABLE BBs in initIfsLib:")
    for b in f.bbs:
        if b not in reach:
            print("   0x%X kind=%s" % (b, f.bbs[b].kind))

    # ---- the 0x96E8 BB: predecessors
    print("\nPredecessors of BB 0x96E8 (the LoadLibraryW BB):")
    for start, b in f.bbs.items():
        for s, k in b.succ:
            if s == 0x96E8:
                print("   from 0x%X kind=%s" % (start, k))

    print("\nExit points (ret) in initIfsLib:")
    for start, b in f.bbs.items():
        if b.kind == "ret":
            insn = f.insns[b.insns[-1]]
            print("   0x%X  %s %s" % (start, insn.mnemonic, insn.op_str))


if __name__ == "__main__":
    main()
