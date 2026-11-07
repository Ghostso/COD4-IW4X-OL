#!/usr/bin/env python3
"""138: 结构性锚定反汇编。
用法: s138_dis.py <VA> [len]
  先打印入口前 16 字节(确认 cc/ret 锚定), 再反汇编 len 字节。
"""
import sys
import re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)


def cstr(va, maxlen=90):
    f = va - VA
    if not (0 <= f < N):
        return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > maxlen:
        return None
    s = d[f:e]
    return s.decode("latin1") if s and all(32 <= c < 127 for c in s) else None


def dis(va, length):
    f = va - VA
    print("== entry 0x%08X (file 0x%06X)" % (va, f))
    print("   pre-entry bytes: " + d[f - 16:f].hex(" "))
    code = d[f:f + length]
    for ins in md.disasm(code, va):
        line = "  0x%08X  %-20s %s %s" % (
            ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str)
        for m in re.finditer(r"0x([0-9a-f]{5,8})", ins.op_str):
            v = int(m.group(1), 16)
            s = cstr(v)
            if s:
                line += "   ; '%s'" % s
        print(line)


if __name__ == "__main__":
    va = int(sys.argv[1], 0)
    ln = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x200
    dis(va, ln)
