#!/usr/bin/env python3
"""s137: 反汇编 (VA 起, 长度). 抗 capstone 异常, 逐条打印."""
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)


def cstr(va, maxlen=60):
    f = va - VA
    if not (0 <= f < N):
        return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > maxlen:
        return None
    s = d[f:e]
    return s.decode("latin1") if s and all(32 <= c < 127 or c in (9, 10) for c in s) else None


def run(va, length):
    off = va - VA
    code = d[off:off + length]
    print("=== VA 0x%08X (file 0x%06X) len 0x%X ===" % (va, off, length))
    if not code:
        print("  <empty>")
        return
    try:
        for ins in md.disasm(code, va):
            line = "  0x%08X  %-24s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str)
            for tok in ins.op_str.replace(",", " ").replace("[", " ").replace("]", " ").split():
                if tok.startswith("0x"):
                    try:
                        s = cstr(int(tok, 16))
                    except ValueError:
                        s = None
                    if s:
                        line += "   ; '%s'" % s
            print(line)
    except Exception as e:  # noqa
        print("  EXC:", e)


if __name__ == "__main__":
    a = int(sys.argv[1], 0)
    L = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x100
    run(a, L)
