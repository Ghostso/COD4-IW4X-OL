#!/usr/bin/env python3
"""138 v2: 跟踪 esp 相对入口 E0 的偏移, 把 [esp+X] 还原成 "E0 相对偏移"。

关键: call 之后按被调函数的 `ret N` 扣除它的参数 (cdecl/stdcall 自动清栈)。
用法: s138_stacktrack2.py <VA> <len>
"""
import sys
import re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_MEM, X86_OP_REG, X86_OP_IMM, X86_REG_ESP, X86_REG_EBP

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

_retcache = {}


def callee_ret_pop(va):
    """返回被调函数 `ret N` 的 N (找不到则 0)。"""
    if va in _retcache:
        return _retcache[va]
    f = va - VA
    res = 0
    if 0 <= f < N:
        for ins in md.disasm(d[f:f + 0x900], va):
            if ins.mnemonic == "ret":
                res = ins.operands[0].imm if ins.operands else 0
                break
            if ins.mnemonic in ("jmp",):   # 跳到别处, 保险起见停
                pass
    _retcache[va] = res
    return res


def cstr(va, maxlen=90):
    f = va - VA
    if not (0 <= f < N):
        return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > maxlen:
        return None
    s = d[f:e]
    return s.decode("latin1") if s and all(32 <= c < 127 for c in s) else None


def main():
    va = int(sys.argv[1], 0)
    ln = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x400
    f = va - VA
    delta = 0
    ebp_delta = None      # ebp 相对入口 E0 的偏移
    for ins in md.disasm(d[f:f + ln], va):
        note = ""
        for oi in (0, 1):
            if len(ins.operands) <= oi:
                continue
            op = ins.operands[oi]
            tag = "dst" if oi == 0 else "src"
            if op.type == X86_OP_MEM and op.mem.base == X86_REG_ESP and op.mem.index == 0:
                rel = delta + op.mem.disp
                if ins.mnemonic == "lea":
                    note += "  ; %s lea->F%+d" % (tag, rel)
                else:
                    note += "  ; %s F%+d" % (tag, rel)
            elif op.type == X86_OP_MEM and op.mem.base == X86_REG_EBP and op.mem.index == 0 \
                    and ebp_delta is not None:
                note += "  ; %s F%+d (ebp)" % (tag, ebp_delta + op.mem.disp)
        if len(ins.operands) == 1:      # push [esp+X]
            op = ins.operands[0]
            if op.type == X86_OP_MEM and op.mem.base == X86_REG_ESP and op.mem.index == 0:
                note += "  ; push [esp%+d] -> E0%+d" % (op.mem.disp, delta + op.mem.disp)
        line = "  0x%08X  %-20s %s %s%s" % (
            ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, note)
        for m in re.finditer(r"0x([0-9a-f]{5,8})", ins.op_str):
            s = cstr(int(m.group(1), 16))
            if s:
                line += "   ; '%s'" % s
        print(line)

        m = ins.mnemonic
        if m == "push":
            delta -= 4
        elif m == "pop":
            delta += 4
        elif m == "mov" and len(ins.operands) == 2 and ins.operands[0].type == X86_OP_REG \
                and ins.operands[0].reg == X86_REG_EBP and ins.operands[1].type == X86_OP_REG \
                and ins.operands[1].reg == X86_REG_ESP:
            ebp_delta = delta
        elif m in ("sub", "add") and len(ins.operands) == 2:
            a, b = ins.operands
            if a.type == X86_OP_REG and a.reg == X86_REG_ESP and b.type == X86_OP_IMM:
                delta += b.imm if m == "add" else -b.imm
        elif m == "and" and len(ins.operands) == 2:
            a = ins.operands[0]
            if a.type == X86_OP_REG and a.reg == X86_REG_ESP:
                # and esp,-8 : 向下对齐, 不要归零
                delta = delta - (delta % 8)
        elif m == "call":
            o = ins.operands[0]
            if o.type == X86_OP_IMM:
                delta += callee_ret_pop(o.imm)
            else:
                # 间接调用: 本二进制里全是 stdcall 辅助 (_AddRef/_Release/虚调用)
                delta += 4
                note += "  [indirect: assume ret4]"
        elif m == "mov" and len(ins.operands) == 2 and ins.operands[0].type == X86_OP_REG \
                and ins.operands[0].reg == X86_REG_ESP:
            delta = 0   # mov esp,ebp 收敛


if __name__ == "__main__":
    main()
