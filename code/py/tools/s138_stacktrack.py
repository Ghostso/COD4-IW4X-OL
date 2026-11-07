#!/usr/bin/env python3
"""138: 跟踪 esp 相对入口的偏移, 把 [esp+X] 还原成 "相对 E0 的帧偏移"。

用法: s138_stacktrack.py <VA> <len>
E0 = 进入函数后、第一条指令执行前的 esp。
对每条指令输出: 地址 字节 反汇编 ; [esp+X] -> E0<rel>
只做线性扫描, 遇到 ret/jmp 不停止 (只看一段连续代码)。
"""
import sys
import re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_MEM, X86_OP_REG, X86_REG_ESP

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def cstr(va, maxlen=90):
    f = va - VA
    if not (0 <= f < len(d)):
        return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > maxlen:
        return None
    s = d[f:e]
    return s.decode("latin1") if s and all(32 <= c < 127 for c in s) else None


def is_esp(mem):
    return mem.base == X86_REG_ESP and mem.index == 0


def main():
    va = int(sys.argv[1], 0)
    ln = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x400
    f = va - VA
    delta = 0
    for ins in md.disasm(d[f:f + ln], va):
        note = ""
        # --- 先记录本条指令的 [esp+X] (按执行前的 delta) ---
        if len(ins.operands) == 2:
            op = ins.operands[1]
            if op.type == X86_OP_MEM and is_esp(op.mem):
                rel = delta + op.mem.disp
                note += "  ; [esp+0x%X] => E0%+d" % (op.mem.disp & 0xFFFFFFFF
                                                    if op.mem.disp >= 0 else op.mem.disp,
                                                    rel)
            # lea reg,[esp+X]
        if ins.mnemonic == "lea" and len(ins.operands) == 2:
            op = ins.operands[1]
            if op.type == X86_OP_MEM and is_esp(op.mem):
                note += "  ; lea E0%+d" % (delta + op.mem.disp)
        line = "  0x%08X  %-20s %s %s%s" % (
            ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, note)
        for m in re.finditer(r"0x([0-9a-f]{5,8})", ins.op_str):
            s = cstr(int(m.group(1), 16))
            if s:
                line += "   ; '%s'" % s
        print(line)
        # --- 更新 delta ---
        m = ins.mnemonic
        if m == "push":
            delta -= 4
        elif m == "pop":
            delta += 4
        elif m in ("sub", "add") and len(ins.operands) == 2:
            a, b = ins.operands
            if a.type == X86_OP_REG and a.reg == X86_REG_ESP and b.type == 2:
                v = b.imm
                delta += v if m == "add" else -v
        elif m == "call":
            pass  # call/ret 平衡; 被调函数自行恢复
        elif m == "ret" or m.startswith("ret"):
            pass


if __name__ == "__main__":
    main()
