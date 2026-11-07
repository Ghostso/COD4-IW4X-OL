# EX-061: re-validate the "invalid" sites using a widened entry set
# (byte after ret/int3/padding counts as an entry), which recovers the
# alignment for functions whose strict prologue is not the classic form.
import json
from collections import OrderedDict, deque

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex060_iips_cfg import Image, DLL
from ex061_functions import code_bounds
from ex060_cfg_engine import COND_JMP


def find_entries(img):
    lo, hi = code_bounds(img)
    d = img.by_rva
    e = set()
    for rva in range(lo, hi - 16):
        b = d[rva:rva + 16]
        if (b[0] == 0x6A and b[1] == 0xFF and b[2] == 0x68 and
                b[7] == 0x64 and b[8] == 0xA1):
            e.add(rva)
        elif b[0] == 0x55 and b[1] == 0x8B and b[2] == 0xEC:
            e.add(rva)
        elif b[0] == 0x64 and b[1] == 0xA1 and b[2:6] == b"\x00\x00\x00\x00":
            e.add(rva)
        else:
            prev = d[rva - 1]
            # any byte right after a ret / int3 / 0xCC padding / 0x90 nop
            # run is a plausible entry
            if prev in (0xC3, 0xCC, 0xC2) and b[0] != 0xCC:
                e.add(rva)
    return e


def grow(img, entry, md, limit=6000):
    lo, hi = code_bounds(img)
    insns = OrderedDict()
    todo = deque([entry])
    seen = set()
    while todo:
        start = todo.popleft()
        if start in seen:
            continue
        seen.add(start)
        rva = start
        while lo <= rva < hi:
            if rva in insns:
                break
            insn = next(md.disasm(img.read(rva, 16), img.base + rva), None)
            if insn is None:
                break
            insns[rva] = insn
            if len(insns) > limit:
                return insns
            m = insn.mnemonic
            if m.startswith("ret") or m in ("int3", "hlt", "ud2"):
                break
            if m == "jmp":
                if insn.operands and insn.operands[0].type == X86_OP_IMM:
                    t = insn.operands[0].imm - img.base
                    if img.is_code(t):
                        todo.append(t)
                break
            if m in COND_JMP or m.startswith("j"):
                if insn.operands and insn.operands[0].type == X86_OP_IMM:
                    t = insn.operands[0].imm - img.base
                    if img.is_code(t):
                        todo.append(t)
                rva = rva + insn.size
                continue
            rva = rva + insn.size
    return insns


def main():
    img = Image(DLL)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True

    entries = sorted(find_entries(img))
    print("widened entries: %d" % len(entries))

    sites = [0xB0D0, 0xB0D6, 0xCBA0, 0xCBA6, 0x13629, 0x1366E, 0x13698,
             0x1384A, 0x1385E, 0x138D3, 0x15747, 0x2F01C]

    # For each site, find the nearest entry <= site and grow; accept only
    # if the grown body contains the site.
    cache = {}

    def body(c):
        if c not in cache:
            cache[c] = grow(img, c, md)
        return cache[c]

    print()
    print("=== revalidation ===")
    for s in sites:
        cands = [x for x in entries if x <= s]
        owners = [c for c in cands if s in body(c)]
        if not owners:
            # fall back: show the nearest entry and why it fails
            near = max(cands) if cands else None
            print("  +0x%05X  STILL UNATTRIBUTED (nearest entry 0x%X)"
                  % (s, near if near else 0))
            continue
        owner = min(owners)
        b = body(owner)
        insn = b[s]
        print("  +0x%05X  owner +0x%05X  insns=%d  insn: %s %s" % (
            s, owner, len(b), insn.mnemonic, insn.op_str))


if __name__ == "__main__":
    main()
