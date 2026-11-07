# EX-061: robust function-boundary recovery for iips.dll .text.
#
# Strategy: find all function entries via strict prologue patterns, then
# grow each function by recursive descent (following call targets and
# branch targets), stopping at ret / jmp-past-body. This gives a real
# owner for every +0x60 access site.
import json
import struct
from collections import OrderedDict, defaultdict, deque

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex060_iips_cfg import Image, DLL, build_imports
from ex060_cfg_engine import COND_JMP


def code_bounds(img):
    codesecs = [s for s in img.sections if s["chars"] & 0x20000000]
    lo = min(s["va"] for s in codesecs)
    hi = max(s["va"] + s["vsize"] for s in codesecs)
    return lo, hi


def find_prologues(img):
    """Strict MSVC x86 prologue patterns."""
    lo, hi = code_bounds(img)
    d = img.by_rva
    starts = set()
    for rva in range(lo, hi - 16):
        b = d[rva:rva + 16]
        # 6A FF 68 xx xx xx xx 64 A1 00 00 00 00   SEH prologue
        # NOTE: the true function entry is the byte AT rva (the 6A), so the
        # subsequent push eax / sub esp / push regs follow.  Accept both the
        # 6A-first form and the 64 A1-first form, and also the case where
        # the preceding byte is padding (ret/int3/align).
        if (b[0] == 0x6A and b[1] == 0xFF and b[2] == 0x68 and
                b[7] == 0x64 and b[8] == 0xA1 and b[9:13] == b"\x00\x00\x00\x00"):
            starts.add(rva)
            continue
        # 55 8B EC   push ebp ; mov ebp,esp
        if b[0] == 0x55 and b[1] == 0x8B and b[2] == 0xEC:
            starts.add(rva)
            continue
        # 64 A1 00 00 00 00   mov eax, fs:[0]  (no-SEH start)
        if b[0] == 0x64 and b[1] == 0xA1 and b[2:6] == b"\x00\x00\x00\x00":
            starts.add(rva)
            continue
    return starts


def grow(img, entry, md, limit=8000):
    """Recursive-descent body recovery from a function entry.

    Follows conditional branch targets and fall-throughs, and stops at
    ret / jmp out of the local region. Does NOT follow calls (they are
    separate functions), but does follow their fall-through.
    """
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

    starts = sorted(find_prologues(img))
    print("strict prologue candidates: %d" % len(starts))

    # Assign each +0x60 site to the function whose body contains it.
    sites = [0x95D0, 0x97A9, 0x9A2B, 0x9B51, 0x9B66, 0x9B7B,
             0x91CF, 0x13629, 0x1366E, 0x13698, 0x1384A, 0x1385E, 0x138D3,
             0x15CF4, 0x2F01C, 0xA327, 0xA340, 0xA4D9, 0xA613, 0xA639,
             0xA68E, 0xA93A, 0x929F, 0x92C6, 0x92C9, 0x15747,
             0xB0D0, 0xB0D6, 0xCBA0, 0xCBA6]

    # Build bodies only for the candidate owners we care about: the
    # nearest preceding prologue plus a couple more, then check containment.
    print()
    print("=== owner attribution by body containment ===")
    cache = {}
    for s in sorted(sites):
        cands = [x for x in starts if x <= s]
        owner = None
        # try up to 6 nearest preceding prologues, nearest function whose
        # body actually contains the site wins
        for c in sorted(cands, reverse=True)[:6]:
            if c not in cache:
                cache[c] = grow(img, c, md)
            if s in cache[c]:
                owner = c
                break
        if owner is None:
            print("  +0x%05X  owner UNKNOWN" % s)
        else:
            body = cache[owner]
            last = max(body.keys())
            print("  +0x%05X  owner +0x%05X  body 0x%05X..0x%05X  "
                  "insns=%d" % (s, owner, owner, last, len(body)))


if __name__ == "__main__":
    main()
