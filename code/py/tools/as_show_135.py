#!/usr/bin/env python3
"""135 卷工具 J: 批量反汇编给定 VA 列表(每个从入口到首 ret)。"""
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\codol_re_placeholder.bin"  # 占位, 下面重设
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
    return s.decode("latin1") if s and all(32 <= c < 127 for c in s) else None


if __name__ == "__main__":
    for a in sys.argv[1:]:
        va = int(a, 0)
        print("=" * 70)
        print("0x%08X" % va)
        code = d[va - VA:va - VA + 0x200]
        for ins in md.disasm(code, va):
            line = "  0x%08X  %-24s %s %s" % (
                ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str)
            for tok in ins.op_str.replace(",", " ").split():
                if tok.startswith("0x"):
                    try:
                        s = cstr(int(tok, 16))
                    except ValueError:
                        s = None
                    if s:
                        line += "   ; '%s'" % s
            print(line)
            if ins.mnemonic.startswith("ret"):
                break
