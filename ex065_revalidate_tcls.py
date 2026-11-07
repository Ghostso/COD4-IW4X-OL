# EX-065: recursive-descent function recovery for tcls_core.exe.
from collections import OrderedDict, deque

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex065_tcls_img import Img
from ex060_cfg_engine import COND_JMP


def find_entries(img):
    lo, hi = img.codesec()
    d = img.by_rva
    e = set()
    for rva in range(lo, hi - 16):
        b = d[rva:rva + 16]
        if (b[0] == 0x6A and b[1] == 0xFF and b[2] == 0x68 and
                len(b) > 9 and b[7] == 0x64 and b[8] == 0xA1):
            e.add(rva)
        elif b[0] == 0x55 and b[1] == 0x8B and b[2] == 0xEC:
            e.add(rva)
        elif b[0] == 0x64 and b[1] == 0xA1 and b[2:6] == b"\x00\x00\x00\x00":
            e.add(rva)
        else:
            prev = d[rva - 1]
            if prev in (0xC3, 0xCC, 0xC2) and b[0] != 0xCC:
                e.add(rva)
    return e


def grow(img, entry, md, limit=8000):
    lo, hi = img.codesec()
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
