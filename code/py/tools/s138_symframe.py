#!/usr/bin/env python3
"""138: 符号化栈/寄存器模拟 (线性扫描), 用于精确定位 [esp+X]/[ebp+X] 所指向的局部变量,
并追踪该槽位最后被谁写入 (哪条指令、什么来源)。

输出每个"被引用"的槽位的: 偏移(相对 esp0_at_entry)、写入指令、值来源。

用法: s138_symframe.py <VA> <len>
"""
import sys
import re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import (
    X86_OP_MEM, X86_OP_REG, X86_OP_IMM, X86_REG_ESP, X86_REG_EBP,
    X86_REG_EAX, X86_REG_ECX, X86_REG_EDX, X86_REG_EBX, X86_REG_ESI, X86_REG_EDI,
)

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True
RETPOP = {}

REGNAME = {X86_REG_EAX: "eax", X86_REG_ECX: "ecx", X86_REG_EDX: "edx",
           X86_REG_EBX: "ebx", X86_REG_ESI: "esi", X86_REG_EDI: "edi"}


def ret_pop(va):
    if va in RETPOP:
        return RETPOP[va]
    f = va - VA
    r = 0
    if 0 <= f < N:
        for ins in md.disasm(d[f:f + 0x900], va):
            if ins.mnemonic == "ret":
                r = ins.operands[0].imm if ins.operands else 0
                break
    RETPOP[va] = r
    return r


def cstr(va, maxlen=80):
    f = va - VA
    if not (0 <= f < N):
        return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > maxlen:
        return None
    s = d[f:e]
    return s.decode("latin1") if s and all(32 <= c < 127 for c in s) else None


def regname(op):
    return REGNAME.get(op.reg, "r%d" % op.reg)


def main():
    va = int(sys.argv[1], 0)
    ln = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x400
    f = va - VA
    delta = 0
    ebp_delta = None
    slots = {}     # frame_off -> desc

    def key_of(op):
        if op.type != X86_OP_MEM or op.mem.index != 0:
            return None, None
        if op.mem.base == X86_REG_ESP:
            return "esp", delta + op.mem.disp
        if op.mem.base == X86_REG_EBP and ebp_delta is not None:
            return "ebp", ebp_delta + op.mem.disp - 8   # struct-spill 归一 (待校准)
        return None, None

    for ins in md.disasm(d[f:f + ln], va):
        notes = []
        line = "0x%08X  %-16s %s %s" % (ins.address, ins.bytes.hex(),
                                        ins.mnemonic, ins.op_str)
        s = cstr_ = None
        for m in re.finditer(r"0x([0-9a-f]{5,8})", ins.op_str):
            cs = cstr(int(m.group(1), 16))
            if cs:
                line += "   ; '%s'" % cs

        ops = ins.operands
        # 读取侧
        for i, op in enumerate(ops):
            if op.type == X86_OP_MEM:
                reg, off = key_of(op)
                if reg == "esp":
                    notes.append("[%s%+d%s]" % ("esp", delta and 0 or 0, ""))
                    notes[-1] = "SLOT esp%+d(=%+d) <- %s" % (
                        delta + op.mem.disp, delta + op.mem.disp,
                        slots.get(delta + op.mem.disp, "?"))
                elif reg == "ebp":
                    pass
        # 写入侧
        if ins.mnemonic in ("mov", "movzx", "movsx", "movsxd", "lea") and len(ops) == 2:
            dst, src = ops
            if dst.type == X86_OP_MEM:
                reg, off = key_of(dst)
                if reg is not None:
                    if src.type == X86_OP_REG:
                        desc = "reg:" + regname(src)
                    elif src.type == X86_OP_IMM:
                        desc = "imm:0x%X" % (src.imm & 0xFFFFFFFF)
                    else:
                        desc = "mem"
                    slots[off] = desc
        # push [esp+x]
        if ins.mnemonic == "push" and len(ops) == 1 and ops[0].type == X86_OP_MEM:
            reg, off = key_of(ops[0])
            if reg is not None:
                notes.append("push SLOT%+d <- %s" % (off, slots.get(off, "?")))

        print(line + ("   || " + " | ".join(notes) if notes else ""))

        m = ins.mnemonic
        if m == "push":
            delta -= 4
        elif m == "pop":
            delta += 4
        elif m in ("sub", "add") and len(ops) == 2 and ops[0].type == X86_OP_REG \
                and ops[0].reg == X86_REG_ESP and ops[1].type == X86_OP_IMM:
            delta += ops[1].imm if m == "add" else -ops[1].imm
        elif m == "and" and len(ops) == 2 and ops[0].type == X86_OP_REG \
                and ops[0].reg == X86_REG_ESP:
            delta = delta - (delta % 8)
        elif m == "call":
            o = ops[0]
            delta += ret_pop(o.imm) if o.type == X86_OP_IMM else 4
        elif m == "mov" and len(ops) == 2 and ops[0].type == X86_OP_REG \
                and ops[0].reg == X86_REG_ESP:
            delta = 0
        elif m == "mov" and len(ops) == 2 and ops[0].type == X86_OP_REG \
                and ops[0].reg == X86_REG_EBP and ops[1].type == X86_OP_REG \
                and ops[1].reg == X86_REG_ESP:
            ebp_delta = delta


if __name__ == "__main__":
    main()
