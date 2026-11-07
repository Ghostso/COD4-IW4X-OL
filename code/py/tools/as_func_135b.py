#!/usr/bin/env python3
"""135 卷工具 B: 从函数中部反推入口(向上找最近 `cc cc` 边界)并整段反汇编。"""
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)


def cstr(va, maxlen=120):
    f = va - VA
    if not (0 <= f < N):
        return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > maxlen:
        return None
    s = d[f:e]
    if not s or not all(32 <= c < 127 or c in (9, 10) for c in s):
        return None
    return s.decode("latin1")


def entry_of(va):
    f = va - VA
    i = f
    while i > 0:
        if d[i - 1] == 0xCC and d[i - 2] == 0xCC:
            return VA + i
        i -= 1
    return None


def run(va, length):
    code = d[va - VA:va - VA + length]
    for ins in md.disasm(code, va):
        line = "  0x%08X  %-22s %s %s" % (
            ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str)
        for tok in ins.op_str.replace(",", " ").split():
            if tok.startswith("0x"):
                try:
                    v = int(tok, 16)
                except ValueError:
                    continue
                s = cstr(v)
                if s:
                    line += "   ; '%s'" % s
        print(line)


if __name__ == "__main__":
    start = int(sys.argv[1], 0)
    L = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x200
    ent = entry_of(start)
    print("entry of 0x%08X -> 0x%08X (span 0x%X)" % (start, ent, start - ent))
    run(ent, L + (start - ent))
