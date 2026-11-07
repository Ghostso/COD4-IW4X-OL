# EX-061: build a function map of iips.dll .text so every +0x60 access site
# can be attributed to a containing function, and so `this` provenance can
# be resolved per function.
import json
import struct
from collections import OrderedDict, defaultdict

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex060_iips_cfg import Image, DLL, build_imports


def find_prologues(img):
    """Find MSVC-style function prologues in .text.

    Patterns accepted:
      push ebp ; mov ebp, esp
      6A xx 68 xx xx xx xx 64 A1 00 00 00 00  (SEH, push -1 + handler)
      64 A1 00 00 00 00                        (no SEH start)
    We use conservative signals and a small length sweep.
    """
    starts = set()
    lo, hi = 0x1000, 0x33000
    rva = lo
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True

    known = set()
    for rva in range(lo, hi - 8):
        b = img.by_rva[rva:rva + 8]
        # 55 8B EC           push ebp ; mov ebp,esp
        if b[0] == 0x55 and b[1] == 0x8B and b[2] == 0xEC:
            starts.add(rva)
        # 6A FF 68 xx xx xx xx   push -1 ; push handler   (SEH)
        if b[0] == 0x6A and b[1] == 0xFF and b[2] == 0x68:
            starts.add(rva)
        # 64 A1 00 00 00 00      mov eax, fs:[0]
        if b[0] == 0x64 and b[1] == 0xA1 and b[2:6] == b"\x00\x00\x00\x00":
            starts.add(rva)
        # 83 EC xx   sub esp, imm8   (common after push ebp or as first insn)
        if b[0] == 0x83 and b[1] == 0xEC:
            # only accept if preceded by a ret/int3/pad byte
            prev = img.by_rva[rva - 1]
            if prev in (0xC3, 0xCC, 0xCC, 0x90, 0xC2) or prev == 0x00:
                starts.add(rva)
    return starts


def main():
    img = Image(DLL)
    starts = find_prologues(img)
    print("prologue candidates:", len(starts))

    # For each access site of interest, attribute to nearest preceding
    # candidate that is reachable by linear decode from there.
    sites = [0x95D0, 0x97A9, 0x9A2B, 0x9B51, 0x9B66, 0x9B7B,
             0x91CF, 0x13629, 0x1366E, 0x13698, 0x1384A, 0x1385E, 0x138D3,
             0x15CF4, 0x2F01C, 0xA327, 0xA340, 0xA4D9, 0xA613, 0xA639,
             0xA68E, 0xA93A, 0x929F, 0x92C6, 0x92C9, 0x15747, 0xB0D0,
             0xB0D6, 0xCBA0, 0xCBA6]

    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True

    print()
    print("=== nearest preceding prologue for each site ===")
    for s in sorted(sites):
        cands = [x for x in starts if x <= s]
        if not cands:
            print("  +0x%05X  (none)" % s)
            continue
        owner = max(cands)
        # sanity: decode from owner toward s to confirm reachability
        rva = owner
        ok = False
        while rva <= s and rva < 0x33000:
            insn = next(md.disasm(img.read(rva, 16), img.base + rva), None)
            if insn is None:
                break
            if rva == s:
                ok = True
                break
            if insn.mnemonic.startswith("ret"):
                if rva < s:
                    ok = False
                break
            rva += insn.size
        print("  +0x%05X  owner +0x%05X  linear_reach=%s  gap=0x%X" % (
            s, owner, ok, s - owner))


if __name__ == "__main__":
    main()
